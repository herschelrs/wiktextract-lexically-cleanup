Cleanup script for [Wiktextract](https://github.com/tatuylonen/wiktextract) data for use with [Glossa](https://github.com/herschelrs/glossa-frontend). Currently only tested for Spanish.
## Usage
Requires [Wiktextract](https://github.com/tatuylonen/wiktextract) dictionary in JSON format (actually, JSON Lines), which can be downloaded from [kaikki.org](https://kaikki.org/).

Should be invoked with:
```
python cleanup.py --input input.json --output output.jsonl
```
Output is also in JSON Lines format, each line a list with two items, the first a word and the second a list of entries with that word. The output is intended to be read in line-by-line and used to construct a dictionary with each word as a key.

Output file for full Spanish dictionary is 193MiB as of 2024-05-03.

## Context and tradeoffs
Wiktextract provides high quality but flawed computational dictionaries based on Wiktionary data. I was inspired by [Ebook dictionary creator](https://github.com/Vuizur/ebook_dictionary_creator) but needed a number of different features for my purposes. 

Generally the goal was to be compatible with the API I had already written for Glossa, and to present a reasonable and legible interpretation of the original entries. In many cases I had to collapse certain distinctions to accomodate low quality Wiktionary entries, as well as some parsing failures from Wiktextract. Some example of this are eg. using any beginning and ending parenthesized sections in a gloss as a `label` and `gloss` respectively (see below), regardless of whether it was written using a template in the original entry, and on the other hand dropping some correctly entered templates when there are multiple glosses in the Wiktextract data. This results in a handful of entries with either slightly unnatural `template` or `gloss` values, or with those fields missing altogether. Nonetheless I'm pretty happy with the choices I made. There are code comments explaining some of these choices. 

Most words have only one entry but ~50k have several. Some of these correspond to multiple entries in the Wiktextract data (usually for unrelated etymologies or different parts of speech), and some come from entries which have been split up, eg. intersecting inflected forms for separate lemmas, or lemmas which intersect with inflected forms of other lemmas, etc.

## Spec for entries
- `word` - the word form
- `pos` - part of speech
- `gender` - optional, a *list* of genders as strings `'f'` or `'m'`. 
    - uses both genders for words where both genders are valid
    - unfortunately doesn't include a gender for modern gender-neutral terms like 'amigue'
- `definitions` - list of dictionaries with `definition` and optionally `label` and `gloss` fields. 
    - `label` usually includes morphological, syntactic, or dialectological information, and `gloss` is a secondary gloss or disambiguation for the definition.
    - note that `definition` is missing or `null` in a very small number of entries for Spanish.
- `forms` - optional, list of inflected forms
- `form_of` - optional, gives the lemma of which the word is an inflected form.
	- most `form_of` entries have in their `definition`s the entry's specific inflection and lemma, eg 'second-person singular imperative of fresar'
- `from_alt_of` - optional, boolean, identifies `form_of` entries which came from sense with an `alt_of` tag in the Wiktextract data. These are usually alternative or deprecated spellings.
- `from_forms` - optional, boolean, identifies `form_of` entries which were population from the list of inflected forms on a lemma, and which were absent as entries in the Wiktextract data.
    - note that these entries have an empty list for `definitions`