Cleanup script for [Wiktextract](https://github.com/tatuylonen/wiktextract) data for use with [Lexically](https://lexically.app/). Currently only tested for Spanish.
## Usage
Requires [Wiktextract](https://github.com/tatuylonen/wiktextract) dictionary in [JSON Lines](https://jsonlines.org/) format, which can be downloaded from [kaikki.org](https://kaikki.org/). Note, the full dataset should be filtered first for only Spanish entries.

Should be invoked with:
```
python cleanup.py --input input.jsonl --output output.jsonl
```
Output is also in JSON Lines format, each line a list with two items, the first a word and the second a list of entries with that word.

For flattened output with one entry per line, use `--one-entry-per-line`:
```
python cleanup.py --input input.jsonl --output output.jsonl --one-entry-per-line
```

Output file for full Spanish dictionary in default format is 215MiB as of 2025-07-05.

#### Lemma List
The script can optionally generate a list of lemmas present in the processed wiktextract dictionary. Note this ignores any extra lemmas that might be included in the lemmatization table below. This feature can be be invoked with `--lemma-list="lemma_list_output"` 

#### Lemmatization Table
The script can also prepare a lemmatization table using data from the [Corpus Del Español](https://www.corpusdelespanol.org/) and the [Spanish Resource Grammar](https://web.archive.org/web/20100618195532/http://www.upf.edu/pdi/iula/montserrat.marimon/srg.html).

Should be invoked with:
```
python cleanup.py --input input.jsonl --output output.jsonl --lemma-list="lemmas" --lemmatization-table="table-output.jsonl" --cde-input="cde_forms.txt" --srg-input-dir="srg/freeling/es/MM/"
```

## Context and tradeoffs
Wiktextract provides high quality but flawed computational dictionaries based on Wiktionary data. I was inspired by [Ebook dictionary creator](https://github.com/Vuizur/ebook_dictionary_creator) but needed a number of different features for my purposes. 

This script retains the form_of key from Wiktextract, and tries to maintain label and gloss from the original entries, including for lower quality entries. There are code comments explaining some of the choices made.

Most words have only one entry but ~50k have several. Some of these correspond to multiple entries in the Wiktextract data (usually for unrelated etymologies or different parts of speech), and some come from entries which have been split up, eg. intersecting inflected forms for separate lemmas, or lemmas which intersect with inflected forms of other lemmas, etc.

## Spec for entries
- `word` - the word form
- `pos` - part of speech
- `f_pos` - highly simplified part of speech, only `'n'`, `'v'`, `'a'`, `'r'`, or `'o'`
- `gender` - optional, a *list* of genders as strings `'f'` or `'m'`. 
    - uses both genders for words where both genders are valid
    - unfortunately doesn't include a gender for modern gender-neutral terms like 'amigue'
- `definitions` - list of dictionaries with `definition` and optionally `label` and `gloss` fields. 
    - `label` usually includes morphological, syntactic, or dialectological information, and `gloss` is a secondary gloss or disambiguation for the definition.
    - note that `definition` is missing or `null` in a very small number of entries for Spanish.
- `forms` - optional, list of inflected forms
- `full_forms` - optional; single-token lemmas with multi-token forms have the correct form extracted, in these cases the original list of forms is in this key.
- `form_of` - optional, gives the lemma of which the word is an inflected form.
	- most `form_of` entries have in their `definition`s the entry's specific inflection and lemma, eg 'second-person singular imperative of fresar'
- `from_alt_of` - optional, boolean, identifies `form_of` entries which came from sense with an `alt_of` tag in the Wiktextract data. These are usually alternative or deprecated spellings.
- `from_forms` - optional, boolean, identifies `form_of` entries which were populated from the list of inflected forms on a lemma, and which were absent as entries in the Wiktextract data.
    - note that these entries have an empty list for `definitions`
