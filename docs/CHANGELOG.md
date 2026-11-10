# Changelog

All notable changes to this project are documented here.

---

## V18.0 — Initial public release

- First public release of the Attractiveness Annotation Tool
- Pairwise comparison with Bradley-Terry and TrueSkill ranking models,
  phase-aware adaptive pair selection
- Manual drag-and-drop stack ranking, cross-checked against BT/TrueSkill
  via Spearman rank correlation
- 1–5 bucket rating, plus converting any ranking into buckets via rank
  bands ("Bulk Apply Rating")
- Rater Analysis tooling (distribution shape, agreement with consensus,
  bias, entropy, inter-rater heatmaps, rater clustering) and Cross-Dataset
  Comparison
- CSV export, multi-dataset support, admin panel for site configuration
- Bundled `Demo_faces` sample dataset (8 AI-generated images) so the app
  runs out of the box
