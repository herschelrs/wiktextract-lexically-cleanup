import argparse

import json

items = []

def main():
    parser = argparse.ArgumentParser(description='Copy contents from an input file to an output file.')

    parser.add_argument('--input', type=str, required=True, help='The path of the input file')
    parser.add_argument('--output', type=str, required=True, help='The path of the output file')

    args = parser.parse_args()

    try:
        with open(args.input, 'r') as infile:
            for line in infile:
                print(line)
                # items.append(json.loads(line))
    except FileNotFoundError:
        print(f"The input file {args.input} was not found.")
        exit(1)

    try:
        with open(args.output, 'w') as outfile:
            outfile.write(str(len(items)))
    except IOError as e:
        print(f"An error occurred while writing to the file {args.output}: {e}")
        exit(1)

    print(f"Parsed dictionary file and output to {args.output}")

main()