import json
from collections import defaultdict

import re
from itertools import islice
import os


def process_dictionary_data(input_file, no_post_process, lemmatization_table, cde_input, srg_input_dir, generate_lemma_list):
    """Process dictionary data and return processed entries and optional lookup tables."""
    try:
      parsed_entries = []
      all_entries_matching_word = defaultdict(list)
      forms_lemmas = defaultdict(lambda: defaultdict(dict))
      pos_lookup_table = {}
      lemma_set = set()
      reflexive_verbs = {}

      with open(input_file, 'r') as infile:
          for line in infile:
              parsed_entries.extend(parse_entry(json.loads(line)))
      print("finished loading and parsing input file")

      for entry in parsed_entries:
        all_entries_matching_word[entry['word']].append(entry)

      if not no_post_process:

        for word, entries in list(all_entries_matching_word.items()):
          # we're going to iterate over the dictionary while we're modifying it, the details in this case are fine
          if word.endswith("rse"):
            non_reflexive_lemma = word[:-2]
            qualifying_defins = [defin for defin in entries if is_defin_reflexive(defin)]
            if not qualifying_defins:
              continue

            if len(qualifying_defins) == len(entries):
              del all_entries_matching_word[word]
            else:
              for defin in qualifying_defins:
                all_entries_matching_word[word].remove(defin)
            
            processed_qualifying_defins = [process_reflexive_defin(defin, non_reflexive_lemma) for defin in qualifying_defins]
            if not all_entries_matching_word.get(non_reflexive_lemma) or all(defin.get("form_of") == word for defin in all_entries_matching_word.get(non_reflexive_lemma, [])):
              all_entries_matching_word[non_reflexive_lemma] = processed_qualifying_defins
            else:
              for defin in all_entries_matching_word[non_reflexive_lemma]:
                if defin.get("form_of") == word:
                  all_entries_matching_word[non_reflexive_lemma].remove(defin)
              all_entries_matching_word[non_reflexive_lemma].extend(processed_qualifying_defins)
            
            reflexive_verbs[word] = (non_reflexive_lemma, processed_qualifying_defins)
        
        for entries in all_entries_matching_word.values():
          for defin in entries:
            form_of = defin.get("form_of")
            if form_of and form_of in reflexive_verbs:
              defin["form_of"] = reflexive_verbs[form_of][0]
        
        # extract correct form from multi-token forms
        for word, entries in all_entries_matching_word.items():
          if len(word.split()) == 1:
            for defin in entries:
              forms = defin.get("forms")
              if forms:
                defin['forms'] = list(set(last_token for last_token in (form.split()[-1] for form in forms) if last_token not in EXCLUDED_MALFORMED_MULTI_TOKEN_FORMS_LAST_TOKEN))
                # this works correctly in all but literally 18 cases, and these are all malformed entries anyway
                if any(len(form.split()) > 1 for form in forms):
                  defin["full_forms"] = list(set(forms))
              else:
                continue
          else:
            for defin in entries:
                if defin.get("forms"):
                    defin['forms'] = list(set(defin['forms']))
            # for multi-token lemmas it's in principle possible to extract the "actual" lemma and all its forms, but nto worth it

        for (word, entries) in list(all_entries_matching_word.items()):
          for defin in entries:
            insert_from_forms_entries(defin, all_entries_matching_word)
        
        print("finished extra processing on dictionary output")
        
        if generate_lemma_list:
          for entries in all_entries_matching_word.values():
            for entry in entries:
              lemma_set.update(find_lemmas_from_form_of_defin(entry, all_entries_matching_word))
          lemma_set.remove(None)
        
        # I'm lowercasing everything, this is slightly problematic but is a fine model for lemmatization at least for spanish
        with open(cde_input, "r", encoding="windows-1252") as file:
          for line in islice(file, 8, None):
            entry = line.split()
            rank, lemma_freq, lemma, pos, form_freq, form, _ = entry
            (form, lemma) = (form.lower(), lemma.lower())
            pos = davies_pos_conversion[pos]
            forms_lemmas[form][pos][lemma] = int(form_freq)

        for filename in [name for name in os.listdir(srg_input_dir) if name != "verbs-nogros"]:
          with open(srg_input_dir + filename, "r", encoding="windows-1252") as file:
            for line in file:
              form, lemma, tag = line.split()
              (form, lemma) = (form.lower(), lemma.lower())
              if "+" in lemma:
                lemma = lemma.split("+")[0]
              pos = srg_pos_conversion[tag[0]]
              if forms_lemmas[form][pos].get(lemma) is None:
                forms_lemmas[form][pos][lemma] = 0
              # srg doesn't have a line for the lemma pointing to itself
              if forms_lemmas[lemma][pos].get(lemma) is None:
                forms_lemmas[lemma][pos][lemma] = -1
                # in this case I'm prioritizing srg after wiktionary. this is kind of a toss-up

        for word, entries in all_entries_matching_word.items():
          for entry in entries:
            word = word.lower()
            lemmas = [lemma.lower() for lemma in find_lemmas_from_form_of_defin(entry, all_entries_matching_word) if lemma is not None]
            pos = wiktionary_pos_conversion[entry.get("pos")]
            for lemma in lemmas:
              if forms_lemmas[word][pos].get(lemma) is None:
                forms_lemmas[word][pos][lemma] = 0
        
        for key, value in forms_lemmas.items():
          new_value = {}
          for pos, lemmas_dict in value.items():
            new_value[pos] = sorted(lemmas_dict.items(), key=lambda item: -item[1])[0][0]
          pos_lookup_table[key] = new_value
        

      result = {
          'entries': all_entries_matching_word,
      }
      
      if lemmatization_table:
          result['pos_lookup_table'] = pos_lookup_table
          
      if generate_lemma_list:
          result['lemma_set'] = lemma_set
              
      return result
    except FileNotFoundError as e:
        print(f"FileNotFoundError: {e}")
        return None
    
EXCLUDED_MALFORMED_MULTI_TOKEN_FORMS_LAST_TOKEN = {"gender-neutral", "meaning"}

# full pos list at https://www.corpusdelespanol.org/web-dial/help/posList.asp
davies_pos_conversion = defaultdict(lambda: "o")
davies_pos_conversion.update({
    "j": "a",
    "m": "n",
    "n": "n",
    "o": "n",
    "r": "r",
    "v": "v",
})

srg_pos_conversion = defaultdict(lambda: "o")
    # "o" is "other", these almost entirly? mostly? don't intersect on forms
srg_pos_conversion.update({
    "A": "a",
    "N": "n",
    "R": "r",
    "V": "v",
    "Z": "n",
    # treat it as a noun, that's fine
    "W": "n",
})

wiktionary_pos_conversion = defaultdict(lambda: "o")
wiktionary_pos_conversion.update({
    "adj": "a", 
    'adv': 'r',
    "noun": 'n',
    'name': 'n',
    'num': 'n',
    "verb": 'v',
})

def is_defin_reflexive(defin: dict):
  return (defin.get("word", "").endswith("rse") and
   defin.get("pos") == "verb" and 
   len(defin.get("word", "").split()) == 1 and 
   not defin.get("form_of"))
  # there's two cases, as of the data from 2024-05 ('verse' and 'reverse', lol) for which the fourth criterion applies
  # as it happens, both of those are the only cases of entries with word in -rse, where there's more than one
  # entry listed here in all_entries_matching_word

def process_reflexive_defin(defin: dict, new_lemma: str):
  for definition in defin.get("definitions", []):
    if not "reflexive" in f"{definition.get('definition')}{definition.get('label')}{definition.get('gloss')}":
      if definition.get("label"):
        definition['label'] = "reflexive, " + definition['label']
      else:
        definition['label'] = 'reflexive'
  if defin.get("forms"):
    defin['forms'].append(defin['word'])
  defin['word'] = new_lemma
  return defin

# this list is likely incomplete, and in any case was only calculated against spanish
TAGS_INCLUDE_AS_GLOSS = {'uncountable': 'uncountable', 'plural-only': 'only in the plural', 'invariable': 'invariable'}

def tags_for_defin(sense):
  # at least for spanish there shouldn't ever be more than one tag, I think, but doing this as an array is good insurance
  if sense.get('tags'):
    return sorted([TAGS_INCLUDE_AS_GLOSS[tag] for tag in sense.get('tags') if tag in TAGS_INCLUDE_AS_GLOSS])
  else:
    return []

def group_senses(entry):
  groups = defaultdict(list)
  for sense in entry['senses']:
    grouping = ""

    # I may end up wanting to check if the tag is not present in the gloss. currently this doesn't matter because these tags are never in the gloss
    grouping += "".join(tags_for_defin(sense))
    grouping += "".join(get_gender_by_sense(sense))
    grouping += sense['form_of'][0]['word'] if sense.get("form_of") else ""

    groups[grouping].append(sense)
  return list(groups.values())

FAILED_FORM_OF_PROBLEMATIC_CONJUGATIONS = ['infinitive', 'gerund', 'preterite', 'imperfect', 'indicative']

def extract_form_of(gloss):
  first_pass_lemma = gloss.split(" of ")[-1]
  if len(first_pass_lemma.split(" ")) == 1:
    return first_pass_lemma
  else:
    for conj in FAILED_FORM_OF_PROBLEMATIC_CONJUGATIONS:
      if conj in first_pass_lemma:
        pattern = r"\b" + re.escape(conj) + r"\b\s+(\w+)"
        match = re.search(pattern, first_pass_lemma)
        if match:
            return match.group(1)
    return first_pass_lemma.split(",")[0]

def pre_parse_failed_form_of(entry):
  if entry['pos'] != 'verb':
    return
  else:
    if all(['glosses' in sense and len(sense['glosses']) == 1 for sense in entry['senses']]):
      if len(entry['senses']) != 1:
        # there are literally two cases of this
        return
      else:
        entry['senses'][0]['form_of'] = [{'word': extract_form_of(entry['senses'][0]['glosses'][0])}]
    else:
      for sense in entry['senses']:
        sense['form_of'] = [{'word': extract_form_of(sense['glosses'][1])}]

def pre_parse_combined_with_form_of(entry):
  """handles some edge cases that the wiktextract fails at
  in particular items with 'combined with' in their form_of"""
  for sense in entry['senses']:
    if is_combined_with_form_of(sense):
      for form in sense['form_of']:
        form['word'] = form['word'].split(" ")[0]

def is_failed_form_of(entry):
  return 'head_templates' in entry and (
    any([
        'args' in template and '2' in template['args'] and "form" in template['args']['2']
        for template in entry['head_templates']
    ]) and not
    any([
        "form_of" in sense
        for sense in entry['senses']
    ])
)

def rip_defin_label_gloss(orig_gloss, extra_labels):
  if orig_gloss == None:
    return {"definition": None}

  pattern = r'(?:\(([^)]*)\))?(.*?)\s*(?:\(([^)]*)\))?$'

  match = re.match(pattern, orig_gloss)
  if not match:
    raise Exception("invalid gloss, failed regex")

  label, definition, gloss = match.groups()

  extra_tag_label = ", ".join([tag for tag in extra_labels if tag not in orig_gloss])
  if extra_tag_label:
    if label:
      label += ", " + extra_tag_label
    else:
      label = extra_tag_label

  return {k: v for k, v in [("label", label), ("definition", definition.strip() if definition else None), ("gloss", gloss)] if v is not None}

def clean_glosses(senses):
  definitions = []
  for sense in senses:
    if len(sense.get('raw_glosses', [])) == 1:
      definitions.append((sense['raw_glosses'][0], tags_for_defin(sense)))
    elif sense.get("glosses"):
      definitions.append((", ".join([remove_ending_colon(gloss) for gloss in sense['glosses']]), tags_for_defin(sense)))
    else:
      definitions.append((None, tags_for_defin(sense)))
  return [rip_defin_label_gloss(*defin) for defin in definitions]

def remove_ending_colon(s):
  if s.endswith(":"):
    return s[:-1]
  return s

def parse_multiple_form_of(group):
  # in 99.86% of cases for spanish we're dealing with an nice nested inflected form intersection, which all have `glosses` len 2. for the rest we do this:
  if any([len(sense['glosses']) != 2 for sense in group]):
    return [{"definition": sense['glosses'][0]} for sense in group]
  else:
    lemma_string = remove_ending_colon(group[0]['glosses'][0].split("\n")[0].split(" of ")[1].strip())
    result = []
    for sense in group:
      definition = sense['glosses'][-1]

      if not definition.endswith(lemma_string):
        definition += " of " + lemma_string

      result.append({"definition": definition})
    return result

def parse_sense_group(group, entry):
  parsed = {}
  if not group[0].get('form_of'):
    parsed["definitions"] = clean_glosses(group)
  else:
    parsed["form_of"] = group[0]["form_of"][0]['word']

    if any(["alt_of" in sense for sense in group]):
      parsed['from_alt_of'] = True

    if len(group) == 1:
      parsed["definitions"] = clean_glosses(group)
    else:
      parsed["definitions"] = parse_multiple_form_of(group)


  # senses have been grouped by gender. note this is only relevant for two words in es, will be relevant for other languages
  gender = get_gender_by_sense(group[0])

  # wiktextract is failing to get gender for some less common gender values in the head. this misses <50 entries which have ~valid gender head templates and are failing for unclear reasons
  head_template_arg_values = [value for values in [template['args'].values() for template in entry['head_templates'] if template['args']] for value in values] if 'head_templates' in entry else []
  # originally included 'gneut' in this list which is ~30 -e -x -@ neologisms in spanish. I expect this will be more complicated for other languages
  if any(item in head_template_arg_values for item in ['mfequiv', ]) and not gender:
    gender = ['m', 'f']

  if gender:
    parsed['gender'] = gender
  return parsed

def is_combined_with_form_of(sense):
  return 'form_of' in sense and any([len(form['word'].split(' ')) > 1 and "combined with" in form['word']
      for form in sense['form_of']
        ])

def pre_parse_alt_of(sense):
  if sense.get('alt_of'):
    sense['form_of'] = sense['alt_of']

def pre_parse_entry(entry):
  # overwrite alt_of if present into form_of
  for sense in entry['senses']:
    pre_parse_alt_of(sense)

  if is_failed_form_of(entry):
    pre_parse_failed_form_of(entry)
    return
  if entry['pos'] == 'verb' and any([
      is_combined_with_form_of(sense) for sense in entry['senses']]):
    pre_parse_combined_with_form_of(entry)
    return

def extract_inflected_forms(forms):
  return [item for item in
          [form['form'] for form in forms
            if all([tag not in form['tags'] for tag in ['table-tags', 'inflection-template', 'class']]) ]
          if item != '-']

def parse_entry(entry):
  pre_parse_entry(entry)

  main_props = {"word": entry['word'], "pos": entry['pos'], "f_pos": wiktionary_pos_conversion[entry.get("pos")]}

  if entry.get('forms'):
    main_props['forms'] = extract_inflected_forms(entry['forms'])

  sense_groups = group_senses(entry)
  return [{**main_props, **parse_sense_group(group, entry)} for group in sense_groups]

def get_gender_by_sense(sense):
  result = []
  if not sense.get('tags'):
    return result
  if 'masculine' in sense.get('tags'):
    result.append("m")
  if 'feminine' in sense.get('tags'):
    result.append("f")
  return result

def find_lemmas_from_form_of_defin(defin, entries, forms_set=None, pos=None, first_call=True):
  pos = pos if pos else defin['pos']
  forms_set = forms_set if forms_set else set()
  form = defin.get("form_of")

  if form in forms_set:
    return {form}
  elif defin['pos'] != pos:
    return {}
  elif not form:
    return {defin['word']}
  elif form not in entries:
    return {None}
  else:

    forms_set.add(form)

    child_lemmas = {lemma
      for form_defin in entries.get(form)
        for lemma in find_lemmas_from_form_of_defin(form_defin, entries, forms_set, pos, False)}

    if first_call:
      child_lemmas = {lemma for lemma in child_lemmas if lemma != defin['word']}
      return child_lemmas if child_lemmas else {None}
    else:
      return child_lemmas if child_lemmas else {None}

def insert_from_forms_entries(defin, entries):
  if defin.get("forms"):
    for form in defin.get("forms"):
      if form == defin['word']:
        pass
      elif defin.get("form_of") and any(
          any(
            lemma_defin.get("pos") == defin.get("pos") and
            form in lemma_defin.get("forms", [])
            for lemma_defin in entries.get(lemma, [])
          )
          for lemma in find_lemmas_from_form_of_defin(defin, entries)
        ):
        pass
      else:
        if not any(
            form_defin.get("pos") == defin.get("pos") and 
            # this is somewhat naive, there can be more edges in the form_of graph that will lead to duplicate from_forms entries here. eg 'disfamada'
            (defin['word'] in find_lemmas_from_form_of_defin(form_defin, entries) or 
            defin['word'] == form_defin.get('form_of') or
            defin['word'] in form_defin.get("forms", [])
            )
          for form_defin in entries.get(form, [])):
          new_form_of = {"word": form, "pos": defin['pos'], "f_pos": wiktionary_pos_conversion[defin.get("pos")], "from_forms": True, "form_of": defin['word'], "definitions": []}
          entries[form].append(new_form_of)

