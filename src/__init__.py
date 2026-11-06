from typing import Any, Self, Union, Optional, List, Tuple, Callable, TypeVar, Generic  # noqa: F401
from .lib import L  # noqa: F401
from icecream import ic  # noqa: F401
from wordfreq import word_frequency, get_frequency_dict
from phonemizer import phonemize
from phonemizer.backend import EspeakBackend
from translatepy import Language
from translatepy.utils.request import Request
from typing import Protocol
from collections import defaultdict
import ask_llm_py
import numpy as np
import simplemma
import re
import asyncio
import translatepy
import unicodedata
import sys
import logging
import json
import os
import functools

__all__ = ["translate_infrequent", "TRANSLATORS", "Cache"]

# Configure logging to write to stderr
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class Cache:
	"""append-only JSONL of raw translations (+ipa), shared by concurrent processes; later lines override earlier ones"""

	def __init__(self, path: str):
		self.path = path
		self.entries: dict[str, dict[str, str]] = {}
		if not os.path.exists(path):
			return
		with open(path, "r", encoding="utf-8") as f:
			for n, line in enumerate(f, 1):
				try:
					entry = json.loads(line)
					self.entries[entry["word"]] = {"translation": entry["translation"]} | ({"ipa": entry["ipa"]} if "ipa" in entry else {})
				except (json.JSONDecodeError, KeyError, TypeError) as e:
					raise ValueError(f"corrupt cache line {n} in {path}: {line!r}") from e

	def append(self, entries: dict[str, dict[str, str]]) -> None:
		if not entries:
			return
		blob = "".join(json.dumps({"word": w} | e, ensure_ascii=False) + "\n" for w, e in entries.items()).encode("utf-8")
		os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
		with open(self.path, "ab", buffering=0) as f:
			assert f.write(blob) == len(blob)  # one write() so O_APPEND writers don't interleave
		self.entries |= entries


async def translate_infrequent(text: str, src_lang: Language, known_words: int, dest_lang: Language, primary: "Translator", fallback: "Translator", phonetic: bool, cache: Cache | None = None, *, history: str, retention: float, decay_base: float, decay_spacing: float, lemma_credit: float) -> str:
	assert isinstance(text, str), f"text must be str, got {type(text).__name__}"
	assert isinstance(src_lang, Language), f"src_lang must be Language, got {type(src_lang).__name__}"
	assert isinstance(known_words, int), f"known_words must be int, got {type(known_words).__name__}"
	assert isinstance(dest_lang, Language), f"dest_lang must be Language, got {type(dest_lang).__name__}"

	text_tokens = [w for w in SPLIT.split(text) if w]
	history_tokens = [w for w in SPLIT.split(history) if w]
	gloss = glossed_occurrences(history_tokens, text_tokens, src_lang, known_words, retention, decay_base, decay_spacing, lemma_credit)
	rare_words = {w.lower() for w, g in zip(text_tokens, gloss) if g}

	known = cache.entries if cache else {}
	missing = rare_words - known.keys()
	fresh: dict[str, str] = await batch_translate(missing, src_lang, dest_lang, primary, fallback) if missing else {}  # BOTTLENECK
	if cache:
		cache.append({w: {"translation": t} for w, t in fresh.items()})
	raw_translations = {w: known[w]["translation"] for w in rare_words - missing} | fresh
	logger.debug(f"translate_infrequent: raw_translations={raw_translations}")
	word_translations = filter_close_translations(raw_translations)
	logger.debug(f"translate_infrequent: filtered_translations={word_translations}")
	if phonetic:
		espeak_voices = EspeakBackend.supported_languages()
		if src_lang.alpha2 not in espeak_voices:
			raise ValueError(f"no espeak voice for '{src_lang.name}' ({src_lang.alpha2})")
		glossed = list(word_translations)
		ipa_of = {w: known[w]["ipa"] for w in glossed if "ipa" in known.get(w, {})}
		unknown = [w for w in glossed if w not in ipa_of]
		if unknown:
			ipas = phonemize(unknown, language=src_lang.alpha2, backend="espeak", strip=True)
			assert len(ipas) == len(unknown) and all(ipas), f"phonemize returned {ipas} for {unknown}"
			ipa_of |= dict(zip(unknown, ipas))
			if cache:
				cache.append({w: {"translation": raw_translations[w], "ipa": ipa_of[w]} for w in unknown})
		word_translations = {w: f"{word_translations[w]} [{ipa_of[w]}]" for w in glossed}

	compose = []
	i = 0
	for word, g in zip(text_tokens, gloss):
		word_start_i = text.index(word, i)
		compose += [text[i:word_start_i], word]
		if g and word.lower() in word_translations:
			compose.append(" {" + word_translations[word.lower()] + "}")
		i = word_start_i + len(word)

	return "".join(compose) + text[i:]


SPLIT = re.compile(r"[\s,.!?\(\)\"–:\[\]{}<>|/\\;]+")


def lang_zipf_s(lang: Language) -> float:
	alpha2 = lang.alpha2
	if alpha2 == "en":
		return 1.07
	elif alpha2 == "de":
		return 1.1
	else:
		L.warning(f"Don't know true `s` value of quasi-Zipfian distribution for '{lang.id}', defaulting to that of English (1.07)")
		return 1.07  # default to English


def glossed_occurrences(history: list[str], text: list[str], src_lang: Language, known_words: int, retention: float, decay_base: float, decay_spacing: float, lemma_credit: float) -> list[bool]:
	"""gloss decision per `text` token; `history` only builds memory. Model: docs/ARCHITECTURE.md"""
	lang = src_lang.alpha2
	f_k = 1 / known_words ** lang_zipf_s(src_lang) if known_words else float("inf")
	amplitude = retention**decay_base
	rarity: dict[str, tuple[str, float] | None] = {}  # lowercase surface -> (lemma, ρ) if rare
	traces: dict[str, dict[str, tuple[list[int], list[float]]]] = defaultdict(dict)  # lemma -> form -> (sighting times, decay exponents)
	gloss: list[bool] = []
	for t, tok in enumerate(history + text):
		low = tok.lower()
		if low not in rarity:
			lemma = simplemma.lemmatize(low, lang=lang).lower()
			f_form, f_lemma = word_frequency(low, lang), word_frequency(lemma, lang)
			if f_lemma > f_form:
				credit = lemma_credit * end_similarity(low, lemma)
				f = (f_form or wordfreq_floor(lang)) ** (1 - credit) * f_lemma**credit  # a form wordfreq never saw is rarer than anything it lists
			else:
				f = f_form
			rarity[low] = (lemma, f / f_k) if 0.0 < f < f_k else None  # f=0 is likely a name or technical term
		if rarity[low] is None:
			if t >= len(history):
				gloss.append(False)
			continue
		lemma, rho = rarity[low]
		recalled = sum((1.0 if form == low else lemma_credit * end_similarity(low, form)) * np.power(t - np.array(ts, dtype=float), -np.array(ds)).sum() for form, (ts, ds) in traces[lemma].items())
		perceived = rho + amplitude * recalled
		if t >= len(history):
			gloss.append(bool(perceived < 1))
		ts, ds = traces[lemma].setdefault(low, ([], []))
		ts.append(t)
		ds.append(decay_base + decay_spacing * perceived)
	assert len(gloss) == len(text)
	logger.debug(f"glossed_occurrences: {sum(gloss)}/{len(text)} text tokens glossed")
	return gloss


@functools.cache
def wordfreq_floor(lang: str) -> float:
	return min(get_frequency_dict(lang).values())


def strip_accents(s: str) -> str:
	return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def jaro_winkler_at(a: str, b: str, offset: int) -> float:
	"""jellyfish's Jaro-Winkler, except `a[i]` is looked for around `b[i + offset]`"""
	window = max(max(len(a), len(b)) // 2 - 1, 0)
	a_hit, b_hit, m = [False] * len(a), [False] * len(b), 0
	for i, c in enumerate(a):
		for j in range(max(0, i + offset - window), min(len(b), i + offset + window + 1)):
			if not b_hit[j] and b[j] == c:
				a_hit[i] = b_hit[j] = True
				m += 1
				break
	if not m:
		return 0.0
	k = transposed = 0
	for i in range(len(a)):
		if a_hit[i]:
			while not b_hit[k]:
				k += 1
			transposed += a[i] != b[k]
			k += 1
	jaro = (m / len(a) + m / len(b) + (m - transposed // 2) / m) / 3
	if jaro <= 0.7:
		return jaro
	prefix = 0
	while prefix < 4 and prefix < len(a) and 0 <= prefix + offset < len(b) and a[prefix] == b[prefix + offset]:
		prefix += 1
	return jaro + prefix * 0.1 * (1 - jaro)


@functools.cache
def end_similarity(a: str, b: str) -> float:
	"""Jaro-Winkler, also with the shorter word aligned to the longer one's end, so a stripped prefix (ел/поел) still matches. Only for two forms of one word: on unrelated strings, containment alone scores high (nsa/mensa)"""
	a, b = sorted((strip_accents(a), strip_accents(b)), key=len)
	assert a and b, "tokens are non-empty"
	return max(jaro_winkler_at(a, b, 0), jaro_winkler_at(a, b, len(b) - len(a)))


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
	def jaro_winkler(word1, word2):
		from jellyfish import jaro_winkler_similarity

		return jaro_winkler_similarity(strip_accents(word1), strip_accents(word2))

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
