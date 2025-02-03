import argparse
import json
from process_dictionary import process_dictionary_data


def main():
  parser = argparse.ArgumentParser(description='Copy contents from an input file to an output file.')

  parser.add_argument('--input', type=str, required=True, help='The path of the input file')
  parser.add_argument('--output', type=str, required=True, help='The path of the output file')
  parser.add_argument('--no-post-process', type=bool, required=False, help='Just parse entries')
  parser.add_argument('--lemmatization-table', type=str, required=False, help='Create lemmatization table, output file')
  parser.add_argument('--cde-input', type=str, required=False, help='Corpus del Español forms list')
  parser.add_argument('--srg-input-dir', type=str, required=False, help='Spanish Resource Grammar inflections list dir')
  parser.add_argument('--lemma-list', type=str, required=False, help='Generate list of lemmas, output file')

  args = parser.parse_args()

  if args.lemmatization_table:
    if args.no_post_process:
      raise Exception("generating lemmatization table can't be done with no-post-process.")
    if not args.cde_input:
      raise Exception("cde-input required if generating lemmatization table")
    if not args.srg_input_dir:
      raise Exception("srg-input-dir required if generating lemmatization table")
  if args.no_post_process and args.lemma_list:
    print("lemma list won't be generated if no-post-process is true")
  
  result = process_dictionary_data(
    input_file=args.input,
    no_post_process=args.no_post_process,
    lemmatization_table=bool(args.lemmatization_table),
    cde_input=args.cde_input,
    srg_input_dir=args.srg_input_dir,
    generate_lemma_list=bool(args.lemma_list)
  )

  if result is None:
    exit(1)
  
  all_entries_matching_word = result.get('entries', {})
  pos_lookup_table = result.get('pos_lookup_table', {})
  lemma_set = result.get('lemma_set', set())

  try:
    with open(args.output, 'w') as outfile:
      for entry in all_entries_matching_word:
        outfile.write(json.dumps([entry, all_entries_matching_word[entry]]) + "\n")
    print(f"wrote main dictionary to {args.output}")
    
  except IOError as e:
    print(f"An error occurred while writing to the file {args.output}: {e}")
    exit(1)
  
  try:
    if args.lemmatization_table:
      with open(args.lemmatization_table, "w") as outfile:
        for entry in pos_lookup_table:
          outfile.write(json.dumps([entry, pos_lookup_table[entry]]) + "\n")
      print(f"wrote lemmatization table to {args.lemmatization_table}")
    
    if args.lemma_list:
      with open(args.lemma_list, "w") as outfile:
        for lemma in lemma_set:
          outfile.write(lemma + "\n")
      print(f"wrote lemma list to {args.lemma_list}")
      
  except IOError as e:
    print(f"An error occurred while writing to the file {args.lemmatization_table}: {e}")
    exit(1)

if __name__ == "__main__":
  main()