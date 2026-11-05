There are some cli flags (run with `--help` to see all), but target use is:
```sh
echo "muss mein Yak rasieren" | translate_infrequent -l "de" -w "5_000" 2>/dev/null
```
Returning 
```
muss mein Yak rasieren {shave}
```

`--cache` keeps translations (and IPA) between runs, so already-seen words don't hit the translation backend again. Bare `--cache` uses `$XDG_CACHE_HOME/translate_infrequent/<src>-<dest>.log` (`~/.cache` if unset); `--cache PATH` uses that file. Safe to share between concurrent runs.
