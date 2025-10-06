import src
import logging
import asyncio
import sys
import argparse
from translatepy import Language


def create_parser():
	parser = argparse.ArgumentParser(description="Translate infrequent words in a text to help language learners")
	parser.add_argument("-l", "--source-lang", type=str, help="Source language")
	parser.add_argument("-t", "--target-lang", type=str, default="en", help='Target language. DEFAULT: "en"')
	parser.add_argument("-w", "--words-n", type=int, help="Number of most used words we don't translate. DEFAULT: 5_000")
	parser.add_argument("-f", "--file", type=str, help="Input file (default: stdin)")
	return parser


def main():
	logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
	src.L = logging.getLogger(__name__)

	parser = create_parser()
	args = parser.parse_args()

	if args.words_n:
		words_n = args.words_n
	else:
		words_n = 5_000

	if args.file:
		with open(args.file, "r", encoding="utf-8") as f:
			text = f.read()
	else:
		if not sys.stdin.isatty():
			text = sys.stdin.read()
		else:
			raise ValueError("No input text provided")

	source_lang = Language(args.source_lang)
	target_lang = Language(args.target_lang)

	out = asyncio.run(src.translate_infrequent(text, source_lang, words_n, target_lang))
	print(out)


main()

