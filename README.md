# Attractiveness Annotation Tool

A local Flask app for running attractiveness-rating studies on a set of
face images. Raters can compare faces pairwise, drag faces into a manual
order, and/or rate them individually on a 1–5 scale — and each method's
results can be explored, cross-checked against the others, and exported.

**Version:** V18.0
**Author:** Andrew Hale
**License:** [MIT](LICENSE) — free to use, modify, and distribute.

## Features

The app offers three rating methods, each its own section with several
tabs:

### 1. Pairwise Face Comparison
Raters are repeatedly shown two faces and pick the more attractive one
(click or keyboard). Both **Bradley-Terry** (MM/Minorisation-Maximisation
algorithm) and **TrueSkill** rankings are fitted continuously from the
same comparisons and normalised to a 0–100 score. Pair selection is
phase-aware per rater — it guarantees every face is seen at least once,
then shifts to the most informationally useful pairs, then spends extra
effort confirming the boundary between the top/bottom of the ranking and
the rest (see `docs/BT_Ranker_Strategy_Guide.docx` for the full
methodology). Sub-tabs: **Compare Faces**, **My Progress**, **Comparison
Results** (the BT/TrueSkill rankings), **Leader Board** (per-rater
comparison counts, coverage, and conformity to the group ranking),
**Bradley-Terry vs. TrueSkill** (how much the two models agree), and a
pairwise-specific **Rater Analysis**. Faces that have never been compared
receive no score — the model requires connectivity through the comparison
graph.

### 2. Face Stack Ranking (manual)
An alternative to pairwise comparison: drag and drop faces directly into
your own best-to-worst order. **Ranking Metrics** then compares your
manual order against the BT and TrueSkill rankings via Spearman rank
correlation, so you can see how well a few hundred pairwise clicks
actually reconstruct a person's real preference order.

### 3. Face Rating (1–5 scale)
Faces can also be rated directly on a 1–5 bucket scale (Unattractive →
Very Attractive) via **Rate Faces**. You can also convert *any* existing
ranking (Bradley-Terry, TrueSkill, or your own manual order) into 1–5
buckets instead of rating from scratch: set four cut points on the ranked
list and **Bulk Apply Rating** assigns every face a bucket accordingly in
one step.

**Rating Results** shows faces grouped by bucket, with three views —
your own, the group consensus, or any other individual rater's — and
several sort options. **Rater Analysis** (bucket mode) adds a large set
of exploratory statistics per rater (mean, std, distribution shape,
agreement with consensus, bias, entropy, inter-rater heatmaps, rater
clustering, most/least controversial faces, and more — see
`docs/Rater_Analysis_1to5_Scale_Guide.md` for what each one means and how
it can mislead you). A **Cross-Dataset Comparison** view lets you compare
rating patterns between two datasets side by side — useful for spotting
systematic bias between groups of images.

### Across all three
- Raters register with just an email (used only to resume their own
  progress across sessions — nothing else is required)
- CSV export of rankings and raw comparisons at any point
- Multiple datasets can coexist; switch between them from the dropdown
- Admin panel controls which sections/tabs are visible, the default
  dataset, the active pairwise model, comparisons-per-image target, and
  the consensus threshold

## Requirements

- Python 3
- `pip install -r requirements.txt` (installs Flask, NumPy, and the
  `trueskill` package)

## Adding your data

A small `Demo_faces` dataset (8 AI-generated sample images, not real
people) is included under `datasets/` so the app has something to show
out of the box. Replace or add to it with your own data.

Drop each dataset you want to rate into its own folder under `datasets/`,
e.g.:

```
datasets/
  my_first_dataset/
    img001.jpg
    img002.jpg
    ...
  another_dataset/
    ...
```

Any subfolder of `datasets/` containing at least one image (`.jpg`,
`.jpeg`, `.png`, `.webp`, or `.bmp`) is picked up automatically — no code
changes needed. Every dataset present shows up as an option in the app's
dataset dropdowns. You need at least one dataset folder with images for
the app to have anything to show.

## Running it

```bash
python app.py
```

Then open http://localhost:5000 in your browser.

## First run — logging in

By default, anyone can open the app and start rating straight away — no
login required. If you want to gate it behind a password (e.g. before
sharing a link publicly), turn on "Require site login" in the admin
panel and set a site password there.

- **Admin panel:** `/admin`, password `admin` by default
- **Site password** (only enforced while "Require site login" is on): none
  by default — set one in the admin panel before turning login on

Both passwords live in `config.json`, created automatically on first run
if it doesn't exist. Change the admin password from the admin panel (or by
editing `config.json` directly) before sharing the app with anyone — it's
a placeholder default, not meant to stay in place, since it's what gates
the admin panel regardless of the site-login setting.

The admin panel also controls which dataset is shown by default, which
tabs/sections are visible, the pairwise selection algorithm (Bradley-Terry
vs TrueSkill), comparisons-per-image target, and the consensus threshold.

## Further reading

See `docs/BT_Ranker_Strategy_Guide.docx` for the pair-selection and ranking
methodology, `docs/Rater_Analysis_1to5_Scale_Guide.md` for an explanation
of every statistic in the Rater Analysis / Dataset Comparison tabs
(bucket-rating mode), and `docs/CHANGELOG.md` for version history.

## How many comparisons do you need?

Rough guide, scaling with dataset size — smaller datasets need
proportionally more comparisons per image to converge:

| Images | Min comparisons | Comfortable |
|--------|----------------|-------------|
| 84     | ~420 (5×)      | ~840 (10×)  |
| 200    | ~1000          | ~2000       |
| 2000   | ~10000         | ~20000      |

## Data files

- `results/<dataset>/comparisons.json` — pairwise choices, timestamped and
  tagged with the rater who made them
- `results/<dataset>/categories.json` — bucket/category ratings
- `results/manual_ranks.json`, `results/rank_bands.json` — cross-dataset,
  keyed by rater
- `raters.json` — rater profiles (email, demographics, login history)
- `config.json` — site settings, editable from the admin panel

CSV exports (`/api/export`, `/api/export/ts-rankings`,
`/api/export/comparisons`) are generated on demand from these files, not
stored on disk.

## Keyboard Shortcuts

- `←`  — choose left face
- `→`  — choose right face
- `Space` or `Esc` — skip pair
