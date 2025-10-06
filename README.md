# translate_infrequent
![Minimum Supported Rust Version](https://img.shields.io/badge/python-3.12.9+-ab6000.svg)
![Lines Of Code](https://img.shields.io/badge/LoC-248-lightblue)
<br>
[<img alt="ci errors" src="https://img.shields.io/github/actions/workflow/status/valeratrades/translate_infrequent/errors.yml?branch=master&style=for-the-badge&style=flat-square&label=errors&labelColor=420d09" height="20">](https://github.com/valeratrades/translate_infrequent/actions?query=branch%3Amaster) <!--NB: Won't find it if repo is private-->
[<img alt="ci warnings" src="https://img.shields.io/github/actions/workflow/status/valeratrades/translate_infrequent/warnings.yml?branch=master&style=for-the-badge&style=flat-square&label=warnings&labelColor=d16002" height="20">](https://github.com/valeratrades/translate_infrequent/actions?query=branch%3Amaster) <!--NB: Won't find it if repo is private-->

[![Semi-explained in here](https://img.youtube.com/vi/i3SgbN1i3pI/0.jpg)](https://www.youtube.com/watch?v=i3SgbN1i3pI&t=166)

When learning a language, reading {books/other resources} in it is of great value. But on early stages of the process I find myself numbing my hands, having to translate 30% of all words I see. I will suffer no more, as now this thing does it for me.
<!-- markdownlint-disable -->
<details>
  <summary>
    <h3>Installation: Linux No Nixos</h3>
  </summary>
<pre><code class="language-sh">alias translate_infrequent='nix run "github:valeratrades/translate_infrequent" --'</code></pre>
</details>
<!-- markdownlint-restore -->
<!-- markdownlint-disable -->
<details>
  <summary>
    <h3>Installation: Nixos</h3>
  </summary>
<div class="markdown-content">packaged as normal under `.default`

My config has `home.packages = [inputs.translate_infrequent.packages.${pkgs.system}.default]`</div>
</details>
<!-- markdownlint-restore -->

## Usage
There are some cli flags (run with `--help` to see all), but target use is:
```sh
echo "Muss mich rasieren, igitt" | translate_infrequent -l "de" -w "5_000"
```
// which with current defaults is likely to output
```
Muss mich rasieren {shave}, igitt
```



<br>

<sup>
	This repository follows <a href="https://github.com/valeratrades/.github/tree/master/best_practices">my best practices</a> and <a href="https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md">Tiger Style</a> (except "proper capitalization for acronyms": (VsrState, not VSRState) and formatting).
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
