from typing import Any, Self, Union, Optional, List, Tuple, Callable, TypeVar, Generic  # noqa: F401
from .lib import L  # noqa: F401
from icecream import ic  # noqa: F401
from wordfreq import word_frequency
from translatepy import Language
import re
import asyncio
import translatepy
import unicodedata

__all__ = ["run"]


async def translate_infrequent(text: str, src_lang: Language, known_words: int = 10_000, dest_lang: Language = Language("en")) -> str:
	assert isinstance(text, str), f"text must be str, got {type(text).__name__}"
	assert isinstance(src_lang, Language), f"src_lang must be Language, got {type(src_lang).__name__}"
	assert isinstance(known_words, int), f"known_words must be int, got {type(known_words).__name__}"
	assert isinstance(dest_lang, Language), f"dest_lang must be Language, got {type(dest_lang).__name__}"

	words_initial_order = re.split(r"[\s,.!?]+", text)
	words_set = set(words_initial_order)
	try:
		# gets appended in some cases for some reason
		words_set.pop("")
	except:
		pass

	rare_words: set[str] = set()
	zipf_s = lang_zipf_s(src_lang)
	ic(zipf_s)
	dub_unknown_threshold = 1 / (known_words**zipf_s)
	for word in words_set:
		freq = word_frequency(word, src_lang.alpha2)
		# 0.0 would mean it's likely a name or technical term, so don't attempt to translate
		if freq < dub_unknown_threshold and freq != 0.0:
			rare_words.add(word)

	word_translations: dict[str, str] = await batch_translate(rare_words, src_lang, dest_lang)  # BOTTLENECK
	word_translations = filter_close_translations(word_translations)

	compose = ""
	i = 0
	for word in words_initial_order:
		word_start_i = text.index(word, i)

		add_word = None  # hate python
		if word in word_translations:
			add_word = word + " {" + word_translations[word] + "}"
		else:
			add_word = word

		compose += text[i:word_start_i]
		compose += add_word

		i = word_start_i + len(word)

	return compose


def lang_zipf_s(lang: Language) -> float:
	assert isinstance(lang, Language), f"lang must be Language, got {type(lang).__name__}"

	alpha2 = lang.alpha2
	if alpha2 == "en":
		return 1.07
	elif alpha2 == "de":
		return 1.1
	else:
		L.warning(f"Don't know true `s` value of quasi-Zipfian distribution for '{lang.id}', defaulting to that of English (1.07)")
		return 1.07  # default to English


async def batch_translate(words: set[str], src_lang: Language, dest_lang: Language) -> dict[str, str]:
	assert isinstance(words, set), f"words must be set[str], got {type(words).__name__}"
	assert all(isinstance(word, str) for word in words), "all elements in words must be str"
	assert isinstance(src_lang, Language), f"src_lang must be Language, got {type(src_lang).__name__}"
	assert isinstance(dest_lang, Language), f"dest_lang must be Language, got {type(dest_lang).__name__}"

	async def translate_word(translator, word, src_lang: Language, dest_lang: Language):
		# Run the synchronous translation in a thread pool to avoid blocking the event loop
		loop = asyncio.get_running_loop()
		try:
			translation = await loop.run_in_executor(None, lambda: translator.translate(word, source_language=src_lang.alpha2, destination_language=dest_lang.alpha2))
			return word, translation.result
		except Exception as e:
			print(f"Error translating '{word}': {str(e)}")
			return word, word  # Fallback to original word

	translator = translatepy.translators.google.GoogleTranslate()
	tasks = []

	for word in words:
		task = translate_word(translator, word, src_lang, dest_lang)
		tasks.append(task)

	results = {}
	completed_tasks = await asyncio.gather(*tasks)

	for word, translation in completed_tasks:
		results[word] = translation

	return results


def filter_close_translations(translations: dict[str, str]) -> dict[str, str]:
	def normalize_no_accents(s):
		"""Remove accents and normalize Unicode characters"""
		return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

	def jaro_winkler(word1, word2):
		from jellyfish import jaro_winkler_similarity

		n1 = normalize_no_accents(word1)
		n2 = normalize_no_accents(word2)
		return jaro_winkler_similarity(n1, n2)

	filtered: dict[str, str] = {}
	for word, translation in translations.items():
		similarity = jaro_winkler(word, translation)
		print(f"{word} -> {translation}: {similarity}")

		if similarity < 0.7:
			filtered[word] = translation

	return filtered
