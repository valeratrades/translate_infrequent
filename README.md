# translate_infrequent
![Minimum Supported Rust Version](https://img.shields.io/badge/python-3.12+-ab6000.svg)
![Lines Of Code](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/valeratrades/b48e6f02c61942200e7d1e3eeabf9bcb/raw/translate_infrequent-loc.json)
<br>
[<img alt="ci errors" src="https://img.shields.io/github/actions/workflow/status/valeratrades/translate_infrequent/errors.yml?branch=main&style=for-the-badge&style=flat-square&label=errors&labelColor=420d09" height="20">](https://github.com/valeratrades/translate_infrequent/actions?query=branch%3Amain) <!--NB: Won't find it if repo is private-->
[<img alt="ci warnings" src="https://img.shields.io/github/actions/workflow/status/valeratrades/translate_infrequent/warnings.yml?branch=main&style=for-the-badge&style=flat-square&label=warnings&labelColor=d16002" height="20">](https://github.com/valeratrades/translate_infrequent/actions?query=branch%3Amain) <!--NB: Won't find it if repo is private-->

[![Semi-explained in here](https://img.youtube.com/vi/i3SgbN1i3pI/0.jpg)](https://www.youtube.com/watch?v=i3SgbN1i3pI&t=166)

When learning a language, reading {books/other resources} in it is of great value. But on early stages of the process I find myself numbing my hands, having to translate 30% of all words I see. I will suffer no more, as now this thing does it for me.
<!-- markdownlint-disable -->
<details>
<summary>
<h2>Installation</h2>
</summary>

<!-- markdownlint-disable -->
<details>
<summary>
<h3>Linux No Nixos</h3>
</summary>

```sh
alias translate_infrequent='nix run "github:valeratrades/translate_infrequent" --'
```

</details>
<!-- markdownlint-restore -->
<!-- markdownlint-disable -->
<details>
<summary>
<h3>Nixos</h3>
</summary>

packaged as normal under `.default`

My config has `home.packages = [inputs.translate_infrequent.packages.${pkgs.system}.default]`

</details>
<!-- markdownlint-restore -->


</details>
<!-- markdownlint-restore -->

## Usage
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

An inflection inherits its dictionary form's familiarity only as far as the two are spelled alike: with `-w 5000`, `Händen` rides on `Hand`, but `warst` doesn't ride on `sein`. `--similarity-power` sets how fast that inheritance falls off with dissimilarity (`0` = every inflection is as known as its dictionary form).



<br>

<sup>
	This repository follows <a href="https://github.com/valeratrades/.github/tree/master/best_practices">my best practices</a> and <a href="https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md">Tiger Style</a> (except "proper capitalization for acronyms": (VsrState, not VSRState) and formatting). For contributing, see <a href="https://github.com/EV-Main/.github/blob/main/code/conventions/git">contribution process</a>. For project's architecture, see <a href="./docs/ARCHITECTURE.md">ARCHITECTURE.md</a>.
</sup>

#### License

<sup>
	Licensed under <a href="LICENSE">Blue Oak 1.0.0</a>
</sup>

<br>

<sub>
	Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in this crate by you, as defined in the Apache-2.0 license, shall
be licensed as above, without any additional terms or conditions.
</sub>

