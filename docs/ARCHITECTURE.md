# Architecture
```mermaid
flowchart LR
    T["history + text tokens"] --> M["memory pass: gloss decision per occurrence"]
    M --> W["words with ≥1 glossed occurrence"]
    W --> C["cache / translate backend"] --> F["filter_close_translations"] --> R["recompose: gloss marked occurrences"]
```

## Gloss model
Whether an occurrence gets glossed follows a Pavlik & Anderson (2005) trace model.

Rarity of a token, before memory. ρ is frequency relative to the `-w` cutoff (ρ = 1 at rank K):
```
ρ_x  = f_x / f_K                                   f_K = 1/K^z: K = -w, z = Zipf exponent (1.1 for de)
s    = END(form, lemma)^p                          p = --similarity-power
log ρ = log ρ_form + s · (log ρ_lemma − log ρ_form)  if ρ_lemma > ρ_form, else ρ = ρ_form
```
The form moves fraction `s` of the way from its own log-frequency to its lemma's. The interpolation is in log space because familiarity tracks log-frequency (each doubling of frequency is about the same step in recognition), and `-w` is a rank, linear in log-frequency. A linear blend would let a very common lemma swamp any similarity (hättest/haben). What's heuristic is `s`: spelling similarity standing for how much familiarity transfers, with `p` picked by eye. A form wordfreq never listed counts at its floor frequency.

END is Jaro-Winkler taken at the better of two alignments: start-aligned (plain JW) and with the shorter word aligned to the longer one's end, so a stripped prefix still matches (ел/поел: JW 0, END 0.87). It's used only between forms of one lemma: on unrelated strings, containment alone scores high (nsa/mensa).

Memory then runs in reading order over `--history` and the input:
```
ρ_perceived  = ρ + A · Σ_j w_j · (t - t_j)^(-d_j)  t in tokens; one impulse per previous sighting of any form of the lemma
w_j          = END(form, form_j)^p              1 for the same form
d_j          = a + c · ρ_perceived(t_j⁻)         set when sighting j happens
A            = Δ1^a                             a brand-new word's single sighting holds Δ1 tokens
gloss iff ρ_perceived < 1
```

Power-law traces have no short/long-term boundary to pick, and making `d_j` grow with the familiarity present at sighting time is what credits spaced repeats over massed ones.
