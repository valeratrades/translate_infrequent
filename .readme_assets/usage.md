There are some cli flags (run with `--help` to see all), but target use is:
```sh
echo "muss mein Yak rasieren" | translate_infrequent -l "de" -w "5_000" 2>/dev/null
```
Returning 
```
muss mein Yak rasieren {shave}
```
