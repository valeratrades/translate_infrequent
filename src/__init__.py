from typing import Any, Self, Union, Optional, List, Tuple, Callable, TypeVar, Generic  # noqa: F401
from .lib import L  # noqa: F401
from icecream import ic  # noqa: F401
from wordfreq import word_frequency
from translatepy import Language
from translatepy.utils.request import Request
from typing import Protocol
import ask_llm_py
import re
import asyncio
import translatepy
import unicodedata
import sys
import logging

__all__ = ["translate_infrequent", "TRANSLATORS"]

# Configure logging to write to stderr
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


async def translate_infrequent(text: str, src_lang: Language, known_words: int, dest_lang: Language, primary: "Translator", fallback: "Translator") -> str:
	assert isinstance(text, str), f"text must be str, got {type(text).__name__}"
	assert isinstance(src_lang, Language), f"src_lang must be Language, got {type(src_lang).__name__}"
	assert isinstance(known_words, int), f"known_words must be int, got {type(known_words).__name__}"
	assert isinstance(dest_lang, Language), f"dest_lang must be Language, got {type(dest_lang).__name__}"

	words_initial_order = re.split(r"[\s,.!?\(\)\"–:\[\]{}<>|/\\;]+", text)
	words_set = set(words_initial_order)
	words_set.discard("")  # split yields it at text edges

	rare_words = find_rare_words(words_set, src_lang, known_words)

	word_translations: dict[str, str] = await batch_translate(rare_words, src_lang, dest_lang, primary, fallback)  # BOTTLENECK
	logger.debug(f"translate_infrequent: raw_translations={word_translations}")
	word_translations = filter_close_translations(word_translations)
	logger.debug(f"translate_infrequent: filtered_translations={word_translations}")

	compose = ""
	i = 0
	for word in words_initial_order:
		word_start_i = text.index(word, i)

		add_word = None  # hate python
		# Check both original case and lowercase for translations
		in_translations = word in word_translations or word.lower() in word_translations
		translation_key = word if word in word_translations else word.lower()
		if in_translations:
			add_word = word + " {" + word_translations[translation_key] + "}"
		else:
			add_word = word

		compose += text[i:word_start_i]
		compose += add_word

		i = word_start_i + len(word)

	return compose


def find_rare_words(words: set[str], src_lang: Language, known_words: int = 10_000) -> set[str]:
	assert isinstance(words, set), f"words must be set[str], got {type(words).__name__}"
	assert all(isinstance(word, str) for word in words), "all elements in words must be str"
	assert isinstance(src_lang, Language), f"src_lang must be Language, got {type(src_lang).__name__}"
	assert isinstance(known_words, int), f"known_words must be int, got {type(known_words).__name__}"

	def lang_zipf_s(lang: Language) -> float:
		alpha2 = lang.alpha2
		if alpha2 == "en":
			return 1.07
		elif alpha2 == "de":
			return 1.1
		else:
			L.warning(f"Don't know true `s` value of quasi-Zipfian distribution for '{lang.id}', defaulting to that of English (1.07)")
			return 1.07  # default to English

	rare_words: set[str] = set()
	zipf_s = lang_zipf_s(src_lang)
	if known_words == 0:
		dub_unknown_threshold = float('inf')  # All words are rare when known_words=0
	else:
		dub_unknown_threshold = 1 / (known_words**zipf_s)

	logger.debug(f"find_rare_words: known_words={known_words}, zipf_s={zipf_s}, threshold={dub_unknown_threshold}")

	for word in words:
		freq = word_frequency(word.lower(), src_lang.alpha2)
		is_rare = freq < dub_unknown_threshold and freq != 0.0
		logger.debug(f"find_rare_words: word='{word}' (lower='{word.lower()}'), freq={freq}, is_rare={is_rare}")
		# 0.0 would mean it's likely a name or technical term, so don't attempt to translate
		if is_rare:
			# Store the lowercased version for consistent lookup
			rare_words.add(word.lower())

	logger.debug(f"find_rare_words: rare_words={rare_words}")
	return rare_words


class CaptchaError(Exception):
	def __init__(self, done: dict[str, str], remaining: set[str]):
		super().__init__(f"captcha after {len(done)} words, {len(remaining)} remaining")
		self.done = done
		self.remaining = remaining


class Translator(Protocol):
	async def translate(self, words: set[str], src_lang: Language, dest_lang: Language) -> dict[str, str]: ...


class GoogleWeb:
	"""translate.google.com's web RPC; rate-limits by redirecting to a captcha at google.com/sorry/"""

	def __init__(self):
		request = Request()
		request.session.hooks["response"].append(self._detect_captcha)  # translatepy swallows service errors, so the redirect itself is the only reliable signal
		self.translator = translatepy.translators.google.GoogleTranslate(request=request)
		self.captcha = False

	def _detect_captcha(self, response, *args, **kwargs):
		if response.status_code == 429 or "/sorry/" in response.url or "/sorry/" in response.headers.get("location", ""):
			self.captcha = True

	async def translate(self, words: set[str], src_lang: Language, dest_lang: Language) -> dict[str, str]:
		loop = asyncio.get_running_loop()

		async def translate_word(word: str) -> tuple[str, str | None]:
			if self.captcha:
				return word, None
			try:
				translation = await loop.run_in_executor(None, lambda: self.translator.translate(word, source_language=src_lang.alpha2, destination_language=dest_lang.alpha2))
			except Exception:
				if self.captcha:
					return word, None
				raise
			logger.debug(f"GoogleWeb: '{word}' -> '{translation.result}'")
			return word, translation.result

		done = {w: t for w, t in await asyncio.gather(*(translate_word(w) for w in words)) if t is not None}
		if self.captcha:
			raise CaptchaError(done, words - done.keys())
		return done


class AskLlm:
	BATCH = 100

	async def translate(self, words: set[str], src_lang: Language, dest_lang: Language) -> dict[str, str]:
		loop = asyncio.get_running_loop()
		ordered = sorted(words)
		batches = [ordered[i : i + self.BATCH] for i in range(0, len(ordered), self.BATCH)]
		results: dict[str, str] = {}
		for part in await asyncio.gather(*(loop.run_in_executor(None, self._translate_batch, b, src_lang, dest_lang) for b in batches)):
			results |= part
		return results

	ROUNDS = 3  # the model occasionally drops lines from a long numbered list

	@classmethod
	def _translate_batch(cls, batch: list[str], src_lang: Language, dest_lang: Language) -> dict[str, str]:
		results: dict[str, str] = {}
		missing = batch
		for _ in range(cls.ROUNDS):
			numbered = "\n".join(f"{i}. {w}" for i, w in enumerate(missing, 1))
			prompt = f"Translate each {src_lang.name} word to {dest_lang.name}. Reply with exactly {len(missing)} lines formatted `N. translation`, keeping the numbering, nothing else.\n\n{numbered}"
			lines = [l.strip() for l in ask_llm_py.ask(prompt, "Translate").splitlines() if l.strip()]
			got: dict[int, str] = {}
			if len(missing) == 1 and len(lines) == 1 and not re.match(r"^\d+\.", lines[0]):  # a lone word comes back unnumbered
				got[1] = lines[0]
			for line in lines:
				if m := re.match(r"^(\d+)\.\s*(.+?)$", line):
					got[int(m[1])] = m[2]
			results |= {w: got[i] for i, w in enumerate(missing, 1) if i in got}
			missing = [w for w in missing if w not in results]
			if not missing:
				return results
			logger.warning(f"AskLlm: {len(missing)} of {len(batch)} words missing from the answer, re-asking")
		raise RuntimeError(f"AskLlm: after {cls.ROUNDS} rounds, no translation for {missing}")


TRANSLATORS: dict[str, type] = {"google": GoogleWeb, "ask_llm": AskLlm}


async def batch_translate(words: set[str], src_lang: Language, dest_lang: Language, primary: Translator, fallback: Translator) -> dict[str, str]:
	try:
		return await primary.translate(words, src_lang, dest_lang)
	except CaptchaError as e:
		logger.warning(f"{type(primary).__name__} hit a captcha; translating {len(e.remaining)} remaining words via {type(fallback).__name__}")
		return e.done | await fallback.translate(e.remaining, src_lang, dest_lang)


def filter_close_translations(translations: dict[str, str]) -> dict[str, str]:
	def normalize_no_accents(s):
		"""Remove accents and normalize Unicode characters"""
		return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))

	def jaro_winkler(word1, word2):
		from jellyfish import jaro_winkler_similarity

		n1 = normalize_no_accents(word1)
		n2 = normalize_no_accents(word2)
		return jaro_winkler_similarity(n1, n2)

	filtered: dict[str, str] = {}
	for word, translation in translations.items():
		similarity = jaro_winkler(word, translation)
		logger.debug(f"filter_close_translations: {word} -> {translation}: similarity={similarity}")
		# Filter out translations that are too similar
		if similarity <= 0.88: # borderline word: "muss {must}", - last thing that's being assumed to be similar enough to fall into guessing range, with `<= 0.88" 
			filtered[word] = translation
			logger.debug(f"filter_close_translations: KEPT {word} -> {translation}")
		else:
			logger.debug(f"filter_close_translations: REMOVED {word} -> {translation} (too similar)")

	return filtered
