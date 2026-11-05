import asyncio

from translatepy import Language

from src import translate_infrequent


class Echo:
	async def translate(self, words, src_lang, dest_lang):
		return {w: "shave" for w in words}


def test_text_after_last_word_is_kept():
	text = "Muss mein Yak rasieren?!\n"
	out = asyncio.run(translate_infrequent(text, Language("de"), 10_000, Language("en"), Echo(), Echo(), False))
	assert out == "Muss mein Yak rasieren {shave}?!\n"
