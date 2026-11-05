There are some cli flags (run with `--help` to see all), but target use is:
```sh
echo "muss mein Yak rasieren" | translate_infrequent -l "de" -w "5_000" 2>/dev/null
```
Returning 
```
muss mein Yak rasieren {shave}
```

`--cache` keeps translations (and IPA) between runs, so already-seen words don't hit the translation backend again. Bare `--cache` uses `$XDG_CACHE_HOME/translate_infrequent/<src>-<dest>.log` (`~/.cache` if unset); `--cache PATH` uses that file. Safe to share between concurrent runs.

A word isn't glossed at every occurrence: each sighting is remembered, decaying over the following tokens, and the gloss returns only once the word is likely forgotten (model in [ARCHITECTURE.md](./docs/ARCHITECTURE.md)). `--retention TOKENS` sets how long one sighting keeps a brand-new word known (`0` glosses every occurrence); `--decay-base` and `--decay-spacing` shape the decay. `--history PATH` feeds text read earlier (e.g. previous chapters) into that memory without emitting or translating it.
