# Computational strand: the sentiment idea, and what to do instead (advisor draft, 2026-11-02)

## 1. Why "sentiment analysis of feminism" does not work as stated

The instinct is right: a computational strand would strengthen the paper. But the idea fails on four independent grounds.

- **Wrong construct.** Sentiment tools (VADER, NRC, transformer classifiers) output positive/negative polarity. Polarity is not feminism and is not agency. Laura Palmer screaming "no" is maximally negative sentiment and maximally high resistance; Dorothy Vallens' quiet compliance may score neutral while coding as near-zero autonomy. The tool would measure the wrong thing with high confidence.
- **Wrong modality.** The question is about *visual* motifs. Sentiment analysis reads text. For the AP Research rubric (method aligned to question), this is the fatal problem: a reader will ask why dialogue polarity is evidence about mirrors.
- **Lynch breaks the tools.** His dialogue is sparse, deadpan, and often ironic. Lexicon methods take sarcasm at face value by design, and even BERT-family classifiers remain unreliable on narrative irony (see SentimentArcs, arXiv 2110.09454).
- **Tiny corpus.** Four films of unusually thin dialogue is a few thousand lines. Any per-film average would have wide uncertainty and no defensible test.

Verdict: drop it. Keep the instinct.

## 2. What text could legitimately measure agency

**Sap et al. 2017 (verified).** "Connotation Frames of Power and Agency in Modern Films," EMNLP 2017, ACL Anthology D17-1247. Labels ~2,000 verbs for whether the subject has positive/negative/equal *agency* and whether agent or theme holds *power*; applied to ~770 screenplays to show female characters are described with lower-agency verbs. The lexicon now ships inside the **Riveter** package (github.com/maartensap/riveter-nlp, GPL-3) as `riveter/data/sap-lexicon/agency_power.csv`. Riveter itself needs Python 3.9 and a transformer coreference model; the CSV alone can be used with plain spaCy and ~40 lines of code.

| Measure | What it says about agency | Effort | Verdict |
|---|---|---|---|
| Dialogue share and turn-taking | Voice and presence, not agency per se | Low once speaker-labeled | Good descriptive table |
| Bechdel-style tests | Binary, widely criticized | Trivial | One sentence in lit review, not a method |
| Character interaction network | Centrality, isolation | Medium | Interesting but not agency |
| Subject-vs-object position + Sap lexicon | Closest proxy for "acts vs. is acted upon" | Medium-high | The one to pick, if any |

**If one is picked:** Sap-lexicon agency scoring on *screenplay action lines*, not dialogue. Action lines ("Dorothy grabs the knife," "Laura is dragged") are the subject-verb-object sentences the lexicon was built for, they are already attributed to characters, and they describe the *visual* track, which brings the strand back toward the research question. Score each female character's share of positive/negative-agency verbs per film. Three weeks is realistic with the advisor doing the spaCy setup.

## 3. Text sources and the speaker-labeling bottleneck

- **Blue Velvet:** a "revised third draft" circulates online. No published screenplay found.
- **Fire Walk with Me:** July 3 and August 8, 1991 drafts circulate; the August draft contains much that was cut.
- **Lost Highway:** published screenplay, Lynch and Gifford, Faber and Faber 1997. The one clean, citable text.
- **Mulholland Drive:** the circulating PDF is the January 1999 *TV pilot* script, not the feature. The second half of the film has no public script.
- **Inland Empire:** largely written scene-by-scene during shooting; no usable text.
- **Subtitles (.srt):** OpenSubtitles is a legal grey area; .srt has no speaker labels.

Honest hours: speaker-labeling four films of subtitles by hand is roughly 4–6 hours per film, so 16–24 hours before any analysis. Drafts also diverge from the finished films (Mulholland Drive badly), which must be disclosed as a validity threat.

## 4. The better fit: quantitize the qualitative coding

The scene × code matrix is already the best dataset in this project. Sandelowski, Voils & Knafl, "On Quantitizing," *Journal of Mixed Methods Research* 3(3), 2009, 208–222, DOI 10.1177/1558689809334210, gives numerical conversion of qualitative data a methodological home. Counting, cross-tabulating, and visualizing your own codes is coherent because the numbers inherit the qualitative construct validity rather than importing a foreign one. It also answers "across films" directly: a four-panel small-multiples heatmap of motif × agency co-occurrence, one per film in release order, *is* the comparison claim in one figure.

**Schema (one row per coded unit):**

```
film, year, scene_id, timecode_start, timecode_end, character,
motif (mirror|lighting|color|framing|other), motif_detail,
agency_dim (autonomy|vulnerability|resistance|control),
valence (-1|0|+1), coder, notes
```

**Pandas sketch:**

```python
import pandas as pd, seaborn as sns, matplotlib.pyplot as plt
df = pd.read_csv("coding.csv")
freq = pd.crosstab(df.film, df.agency_dim, normalize="index")      # per-film code mix
co = (df.groupby(["film","motif","agency_dim"]).size()
        .unstack(fill_value=0))
films = ["Blue Velvet","Fire Walk with Me","Lost Highway","Mulholland Drive"]
fig, axes = plt.subplots(1, len(films), figsize=(16,4), sharey=True)
for ax, f in zip(axes, films):
    sns.heatmap(co.loc[f].div(co.loc[f].values.sum()), ax=ax, cmap="mako",
                vmin=0, vmax=0.25, cbar=(f==films[-1]), annot=True, fmt=".2f")
    ax.set_title(f)
plt.tight_layout(); plt.savefig("motif_x_agency.png", dpi=200)
```

Normalize within film (scene counts differ). No-code route: Google Sheets pivot table, rows = motif, columns = agency_dim, filter = film, conditional-format as heatmap.

## 5. Optional visual-computational strand

All free, all run on a MacBook:

- **PySceneDetect** (`pip install scenedetect`, BSD-3): shot boundaries; gives per-shot start/end times and shot-length distributions. Expect false cuts on Lynch's dissolves and strobe sequences; spot-check.
- **ffmpeg + OpenCV/PIL:** sample one frame per second, compute mean luminance and a k-means dominant palette (scikit-learn, k=5) per scene; join to scene_id. Effort: ~1 day for the advisor to write.
- **Cinemetrics** (cinemetrics.uchicago.edu): the database exists; entries for these films are unconfirmed.

What it can claim: "scenes coded as low-key lighting have measurably lower mean luminance," a triangulation of the lighting codes. What it cannot claim: anything about agency. Luminance is not meaning.

## 6. Recommendation

- **Primary:** qualitative content analysis, as planned.
- **Secondary (do this):** quantitized coding matrices, per-film frequencies, small-multiple heatmaps, agreement statistics. Low cost, high rubric value.
- **Optional stretch, pick ONE:** Sap-lexicon agency scoring on screenplay action lines (Blue Velvet, FWWM, Lost Highway; disclose the Mulholland Drive pilot-script mismatch), *or* luminance/palette triangulation. Not both.
- **Drop:** generic sentiment analysis.

Limitations paragraph template: name the construct gap (verb agency or luminance is a proxy, not the thing), the source gap (drafts differ from films; subtitles lack speakers), the tool gap (lexicon built on mainstream screenplays; PySceneDetect misses dissolves), and the sample size (n = 4 films, so descriptive, not inferential). State that the computational strand triangulates, never replaces, the qualitative reading.

## 7. Tools

Python 3.11+; pandas, matplotlib, seaborn; spaCy `en_core_web_sm`; Riveter (Python 3.9 only, optional); PySceneDetect (scenedetect.com); ffmpeg (`brew install ffmpeg`); OpenCV (`pip install opencv-python`); scikit-learn; Voyant Tools (voyant-tools.org) for no-code text exploration; Orange Data Mining with the Text add-on for no-code pipelines.
