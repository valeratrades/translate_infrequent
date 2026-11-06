import asyncio

import pytest
from translatepy import Language

from src import Cache, translate_infrequent


class CountingTranslator:
	def __init__(self):
		self.calls = 0

	async def translate(self, words, src_lang, dest_lang):
		self.calls += 1
		return {w: "shave" for w in words}


def run(cache_path, translator, phonetic=False):
	return asyncio.run(translate_infrequent("Muss mein Yak rasieren", Language("de"), 10_000, Language("en"), translator, translator, phonetic, Cache(cache_path), history="", retention=300, decay_base=0.177, decay_spacing=0.217, similarity_power=2))


def test_second_run_makes_no_translator_calls(tmp_path):
	path = str(tmp_path / "de-en.log")
	translator = CountingTranslator()
	first = run(path, translator)
	assert translator.calls == 1
	assert "rasieren {shave}" in first
	assert run(path, translator) == first
	assert translator.calls == 1


def test_ipa_is_added_to_cached_entry_without_retranslating(tmp_path):
	path = str(tmp_path / "de-en.log")
	translator = CountingTranslator()
	run(path, translator)
	with_ipa = run(path, translator, phonetic=True)
	assert translator.calls == 1
	assert "rasieren {shave [" in with_ipa
	assert run(path, translator, phonetic=True) == with_ipa


def test_corrupt_line_is_an_error_with_line_number(tmp_path):
	path = tmp_path / "de-en.log"
	path.write_text('{"word": "a", "translation": "b"}\nnot json\n')
	with pytest.raises(ValueError, match="line 2"):
		Cache(str(path))
