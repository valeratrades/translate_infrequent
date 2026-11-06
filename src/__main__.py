import src
import logging
import asyncio
import sys
import os
import argparse
from translatepy import Language


def create_parser():
	parser = argparse.ArgumentParser(description="Translate infrequent words in a text to help language learners")
	parser.add_argument("-l", "--source-lang", type=str, help="Source language")
	parser.add_argument("-t", "--target-lang", type=str, default="en", help='Target language. DEFAULT: "en"')
	parser.add_argument("-w", "--words-n", type=int, help="Number of most used words we don't translate. DEFAULT: 5_000")
	parser.add_argument("-f", "--file", type=str, help="Input file (default: stdin)")
	parser.add_argument("-b", "--backend", choices=src.TRANSLATORS, default="google", help='Translation backend. DEFAULT: "google"')
	parser.add_argument("-p", "--phonetic", action="store_true", help="Append IPA to each gloss")
	parser.add_argument("--cache", nargs="?", const=True, default=None, metavar="PATH", help="Persist translations (and IPA) across runs. Bare flag: $XDG_CACHE_HOME/translate_infrequent/<src>-<dest>.log")
	parser.add_argument("--history", type=str, metavar="PATH", help="Text read before the input only to build memory of seen words; not emitted, not translated")
	decay_help = "Pavlik & Anderson (2005) fit, with time measured in seconds; here time is tokens, so no value is known to be correct."
	parser.add_argument("--retention", type=float, default=300, metavar="TOKENS", help="How long one sighting keeps a brand-new word known. 0 = gloss every occurrence (old behaviour). DEFAULT: 300")
	parser.add_argument("--decay-base", type=float, default=0.177, help=f"Decay exponent of a sighting of a fully unknown word. {decay_help} DEFAULT: 0.177")
	parser.add_argument("--decay-spacing", type=float, default=0.217, help=f"Extra decay per unit of familiarity at sighting time (massed repeats fade faster). {decay_help} DEFAULT: 0.217")
	parser.add_argument("--similarity-power", type=float, default=2, metavar="P", help="An inflection inherits END(form, dictionary form)^P of the way from its own log-frequency to its dictionary form's, END being spelling similarity in 0..1 (warst/sein 0, gib/geben 0.69, Händen/Hand 0.93). Higher P treats irregular forms as separate words sooner; 0 = every inflection is as known as its dictionary form. DEFAULT: 2")
	parser.add_argument("--fallback", choices=src.TRANSLATORS, default="ask_llm", help='Backend used once the primary one hits a captcha. DEFAULT: "ask_llm"')
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

	if args.history:
		with open(args.history, "r", encoding="utf-8") as f:
			history = f.read()
	else:
		history = ""

	source_lang = Language(args.source_lang)
	target_lang = Language(args.target_lang)

	cache_path = args.cache
	if cache_path is True:
		cache_dir = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
		cache_path = os.path.join(cache_dir, "translate_infrequent", f"{source_lang.alpha2}-{target_lang.alpha2}.log")
	cache = src.Cache(cache_path) if cache_path else None

	out = asyncio.run(src.translate_infrequent(text, source_lang, words_n, target_lang, src.TRANSLATORS[args.backend](), src.TRANSLATORS[args.fallback](), args.phonetic, cache, history=history, retention=args.retention, decay_base=args.decay_base, decay_spacing=args.decay_spacing, similarity_power=args.similarity_power))
	print(out)


main()

