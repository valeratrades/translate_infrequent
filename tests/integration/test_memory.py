import asyncio
import re

from translatepy import Language

from src import translate_infrequent


class Gloss:
	async def translate(self, words, src_lang, dest_lang):
		return {w: "gloss" for w in words}


def check(text: str, word: str, glossed: list[int], history: str = "", retention: float = 300) -> str:
	"""`glossed`: which occurrences of `word` in the output carry a gloss"""
	out = asyncio.run(translate_infrequent(text, Language("de"), 5_000, Language("en"), Gloss(), Gloss(), False, history=history, retention=retention, decay_base=0.177, decay_spacing=0.217))
	marks = [bool(m[1]) for m in re.finditer(rf"\b{word}\b( \{{gloss\}})?", out, re.I)]
	assert [i for i, m in enumerate(marks) if m] == glossed, out
	return out


def test_immediate_repeats_are_glossed_once():
	check("Husten husten husten.", "husten", [0])


def test_zero_retention_glosses_every_occurrence():
	check("Husten husten husten.", "husten", [0, 1, 2], retention=0)


def test_history_counts_as_seen_and_is_not_emitted():
	assert check("Husten.", "husten", [], history="Er hat Husten.") == "Husten."


def test_memory_decays():
	check("Erdling " + "und " * 1000 + "Erdling.", "erdling", [0, 1])
