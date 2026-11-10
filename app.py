"""
Face Attractiveness Ranker
=========================================
Drop one or more datasets into `datasets/<dataset_name>/` (each a folder of
images) and run:
    python app.py
Then open http://localhost:5000 in your browser. Every dataset folder with
at least one image is picked up automatically and offered in the dataset
dropdowns.
"""

import hashlib
import json
import math
import random
import re
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
from flask import (Flask, Response, abort, jsonify, render_template,
                   request, send_from_directory, session)

app = Flask(__name__)
app.secret_key = "1f662d63107f50a868dc1e60ad3debe88952d0c93bca96fc"

# ── Site password ──────────────────────────────────────────────────────────────
# Change this to whatever password you want.
SITE_PASSWORD = ""

# Whether the site password gate is enforced at all. When False, anyone can
# browse the app without logging in (admin panel still needs ADMIN_PASSWORD).
SITE_LOGIN_REQUIRED = False

# ── Admin password ─────────────────────────────────────────────────────────────
# Password for the /admin config panel. Separate from the site password.
ADMIN_PASSWORD = "admin"

# ── UI font size ───────────────────────────────────────────────────────────────
# Global base font size as a percentage applied to <html>. Affects all users.
UI_FONT_SIZE = 100

# ── Pairwise dataset ───────────────────────────────────────────────────────────
# Default folder for pairwise comparison.
# Set to a dataset name (e.g. "my_dataset") to start on that dataset by default.
# Set to None to automatically use the first dataset found under datasets/.
PAIRWISE_FOLDER = None

# Set to False to hide the dataset dropdown from the UI entirely.
# Users will always use PAIRWISE_FOLDER (or first found if None above).
PAIRWISE_FOLDER_SELECTOR = True

# ── Protected folders ─────────────────────────────────────────────────────────
# Category ratings written by non-official users on these folders go to a
# separate guest file, leaving the official data untouched. Reports and
# consensus views always read the official file only.
PROTECTED_FOLDERS = []

# ── Comparison targets ────────────────────────────────────────────────────────
TARGET_PER_IMAGE = 10   # comparisons-per-image goal
MIN_COMPARISONS_FOR_CONSENSUS = 400  # raters with fewer comparisons are excluded from consensus

# ── Section visibility ─────────────────────────────────────────────────────────
# Set any section to False to hide it and all its tabs from the UI.
SHOW_INTRO            = True   # Introduction tab at the top of the nav
SHOW_SECTION_PAIRWISE = True   # Compare, My Progress, Rankings, Leader Board, BT vs TS
SHOW_SECTION_STACK    = True   # Ranked Grouping
SHOW_SECTION_CATEGORY = True   # Bucket Grouping, Bucket Grouping Results, Rater Analysis, Dataset Comparison

# ── Pair-selection model ──────────────────────────────────────────────────────
#
# Which algorithm decides which two faces to show next?
#
#   "BT"        — Bradley-Terry (the original system).
#                  Uses a 4-phase strategy: coverage → adaptive filling →
#                  extreme-zone boundary refinement → optional bottom-zone
#                  deep refinement.  Well-tested, good for small datasets.
#                  Trade-off: requires hand-tuned phase transitions and zone
#                  sizes; does not know *how uncertain* each face's score is.
#
#   "TrueSkill" — TrueSkill uncertainty-guided selection.
#                  After initial coverage (Phase 1, identical to BT), pairs
#                  are chosen by targeting the faces the model is *most
#                  uncertain* about (highest σ).  No manual phases 2/3/4 —
#                  the algorithm decides where effort is needed automatically.
#                  Trade-off: requires the `trueskill` library; convergence
#                  behaviour differs from BT on very small datasets (<20 faces).
#
PAIR_SELECTION_MODEL = "TrueSkill"   # "BT" or "TrueSkill"

# ── Paths (partial — needed before config load) ────────────────────────────────
BASE_DIR     = Path(__file__).parent
DATASETS_DIR = BASE_DIR / "datasets"   # every dataset is a subfolder here, e.g. datasets/my_dataset/
CONFIG_FILE  = BASE_DIR / "config.json"


def _load_config():
    """Override in-memory config from config.json if it exists."""
    global SITE_PASSWORD, SITE_LOGIN_REQUIRED, ADMIN_PASSWORD, PAIRWISE_FOLDER, PAIRWISE_FOLDER_SELECTOR
    global SHOW_INTRO, SHOW_SECTION_PAIRWISE, SHOW_SECTION_STACK, SHOW_SECTION_CATEGORY
    global PAIR_SELECTION_MODEL, TARGET_PER_IMAGE, MIN_COMPARISONS_FOR_CONSENSUS, PROTECTED_FOLDERS
    global UI_FONT_SIZE
    if not CONFIG_FILE.exists():
        return
    try:
        cfg = json.load(open(CONFIG_FILE))
        SITE_PASSWORD               = cfg.get("site_password",              SITE_PASSWORD)
        SITE_LOGIN_REQUIRED         = cfg.get("site_login_required",        SITE_LOGIN_REQUIRED)
        ADMIN_PASSWORD              = cfg.get("admin_password",             ADMIN_PASSWORD)
        PAIRWISE_FOLDER             = cfg.get("pairwise_folder",            PAIRWISE_FOLDER) or None
        PAIRWISE_FOLDER_SELECTOR    = cfg.get("pairwise_folder_selector",   PAIRWISE_FOLDER_SELECTOR)
        SHOW_INTRO                  = cfg.get("show_intro",                 SHOW_INTRO)
        SHOW_SECTION_PAIRWISE       = cfg.get("show_pairwise",              SHOW_SECTION_PAIRWISE)
        SHOW_SECTION_STACK          = cfg.get("show_stack",                 SHOW_SECTION_STACK)
        SHOW_SECTION_CATEGORY       = cfg.get("show_category",              SHOW_SECTION_CATEGORY)
        PAIR_SELECTION_MODEL        = cfg.get("pair_selection_model",       PAIR_SELECTION_MODEL)
        TARGET_PER_IMAGE            = cfg.get("target_per_image",           TARGET_PER_IMAGE)
        MIN_COMPARISONS_FOR_CONSENSUS = cfg.get("min_comparisons_consensus", MIN_COMPARISONS_FOR_CONSENSUS)
        PROTECTED_FOLDERS           = cfg.get("protected_folders",          PROTECTED_FOLDERS)
        UI_FONT_SIZE                = cfg.get("ui_font_size",               UI_FONT_SIZE)
    except Exception as e:
        print(f"Warning: could not load config.json: {e}")

_load_config()


def _save_config():
    with open(CONFIG_FILE, "w") as fh:
        json.dump({
            "site_password":             SITE_PASSWORD,
            "site_login_required":       SITE_LOGIN_REQUIRED,
            "admin_password":            ADMIN_PASSWORD,
            "pairwise_folder":           PAIRWISE_FOLDER or "",
            "pairwise_folder_selector":  PAIRWISE_FOLDER_SELECTOR,
            "show_intro":                SHOW_INTRO,
            "show_pairwise":             SHOW_SECTION_PAIRWISE,
            "show_stack":                SHOW_SECTION_STACK,
            "show_category":             SHOW_SECTION_CATEGORY,
            "pair_selection_model":      PAIR_SELECTION_MODEL,
            "target_per_image":          TARGET_PER_IMAGE,
            "min_comparisons_consensus": MIN_COMPARISONS_FOR_CONSENSUS,
            "protected_folders":         PROTECTED_FOLDERS,
            "ui_font_size":              UI_FONT_SIZE,
        }, fh, indent=2)


def site_auth_required(fn):
    """Decorator: redirect to /login if the visitor has not entered the site password."""
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if SITE_LOGIN_REQUIRED and SITE_PASSWORD and not session.get("site_authed"):
            from flask import redirect, url_for
            return redirect("/login")
        return fn(*args, **kwargs)
    return wrapper


# ── Paths ─────────────────────────────────────────────────────────────────────
RESULTS_DIR = BASE_DIR / "results"   # all generated rating data lives here
RESULTS_DIR.mkdir(exist_ok=True)

RATERS_FILE       = BASE_DIR / "raters.json"
DATA_FILE         = RESULTS_DIR / "comparisons.json"
RANK_BANDS_FILE   = RESULTS_DIR / "rank_bands.json"
MANUAL_RANKS_FILE = RESULTS_DIR / "manual_ranks.json"

VALID_EXT  = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
EMAIL_RE   = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── Rater helpers ─────────────────────────────────────────────────────────────

def load_raters():
    if RATERS_FILE.exists():
        with open(RATERS_FILE) as fh:
            return json.load(fh)
    return {}


def save_raters(data):
    with open(RATERS_FILE, "w") as fh:
        json.dump(data, fh, indent=2)


def email_to_id(email: str) -> str:
    return "r_" + hashlib.sha256(email.lower().strip().encode()).hexdigest()[:10]


# ── Image helpers ─────────────────────────────────────────────────────────────

def list_datasets() -> list:
    """Return every dataset name — a subfolder of datasets/ containing at least one image."""
    if not DATASETS_DIR.exists():
        return []
    return sorted(
        d.name for d in DATASETS_DIR.iterdir()
        if d.is_dir() and any(f.suffix.lower() in VALID_EXT for f in d.iterdir())
    )


def get_images(folder=None):
    d = DATASETS_DIR / (folder or _first_pairwise_folder())
    if not d.exists():
        return []
    return sorted(f.name for f in d.iterdir() if f.suffix.lower() in VALID_EXT)


def _first_pairwise_folder() -> str:
    if PAIRWISE_FOLDER:
        return PAIRWISE_FOLDER
    folders = list_datasets()
    return folders[0] if folders else ""


def _first_dataset() -> str:
    folders = list_datasets()
    return folders[0] if folders else ""


def qualified_consensus_comparisons(all_comp):
    """Return only comparisons from raters who meet the MIN_COMPARISONS_FOR_CONSENSUS threshold."""
    from collections import Counter
    counts = Counter(c["rater_id"] for c in all_comp if "rater_id" in c)
    qualified = {rid for rid, n in counts.items() if n >= MIN_COMPARISONS_FOR_CONSENSUS}
    return [c for c in all_comp if c.get("rater_id") in qualified]


def _folder_slug(folder: str) -> str:
    """Sanitise a folder name for use as a results/ subdirectory name."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', folder)


def _comparisons_file(folder=None) -> Path:
    if not folder:
        return DATA_FILE
    return RESULTS_DIR / _folder_slug(folder) / "comparisons.json"


def _categories_file(folder: str) -> Path:
    """Return the categories JSON path for a given dataset folder."""
    return RESULTS_DIR / _folder_slug(folder) / "categories.json"


@lru_cache(maxsize=None)
def get_category_images(folder: str):
    d = DATASETS_DIR / folder
    if not d.exists():
        return []
    return sorted(
        f.name for f in d.iterdir()
        if f.suffix.lower() in VALID_EXT
    )


# ── Comparison helpers ────────────────────────────────────────────────────────

def load_comparisons(folder=None):
    f = _comparisons_file(folder)
    if f.exists():
        with open(f) as fh:
            return json.load(fh)
    return []


def save_comparisons(data, folder=None):
    f = _comparisons_file(folder)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "w") as fh:
        json.dump(data, fh, indent=2)
    # Keep TrueSkill fresh — fit_trueskill is a fast linear replay so refitting
    # on every comparison is fine and keeps σ-guided pair selection accurate.
    # BT is NOT invalidated here — fit_bradley_terry is an expensive iterative
    # algorithm so we let CACHE_REFIT_EVERY throttle it to every 5 comparisons.
    try:
        invalidate_ts_cache()
    except NameError:
        pass


def filter_comparisons(comparisons, rater_id=None):
    if rater_id is None:
        return comparisons
    return [c for c in comparisons if c.get("rater_id") == rater_id]


def comparison_counts(images, comparisons):
    """How many times each image appeared (as winner OR loser)."""
    counts = {img: 0 for img in images}
    for c in comparisons:
        if c["winner"] in counts:
            counts[c["winner"]] += 1
        if c["loser"] in counts:
            counts[c["loser"]] += 1
    return counts


def seen_images(comparisons):
    """Set of images that have appeared at least once."""
    seen = set()
    for c in comparisons:
        seen.add(c["winner"])
        seen.add(c["loser"])
    return seen


# ── BT Score cache ────────────────────────────────────────────────────────────
#
# WHY: Fitting Bradley-Terry on every pair request is expensive on a single-core
# VPS. This cache stores the last fitted scores and only refits when at least
# CACHE_REFIT_EVERY new comparisons have been recorded since the last fit.
# Zero resource use when the site is idle — no background threads, no timers.
# The user who triggers a refit waits ~0.5s at most; everyone else is instant.

CACHE_REFIT_EVERY = 5   # refit after this many new comparisons

_bt_cache = {
    # keyed by a frozenset of rater_ids present in the comparison list,
    # but in practice we use a simpler approach: one cache entry per
    # (comparison_subset_key) where the key is just the comparison count.
    # Structure: { cache_key: {"scores": {...}, "comp_count": int} }
}
_cache_lock = __import__('threading').Lock()


def _cache_key(comparisons):
    """A cheap key: just the number of comparisons. Enough for staleness check."""
    return len(comparisons)


def get_cached_bt_scores(images, comparisons):
    """
    Return BT scores from cache if fresh, otherwise refit and cache.
    Fresh means fewer than CACHE_REFIT_EVERY new comparisons since last fit.
    """
    key      = _cache_key(comparisons)
    cache_id = id(images)  # stable per process since images list doesn't change

    with _cache_lock:
        entry = _bt_cache.get(cache_id)
        if entry is not None:
            age = key - entry["comp_count"]
            if age < CACHE_REFIT_EVERY:
                return entry["scores"]

    # Cache miss or stale — refit
    scores = fit_bradley_terry(images, comparisons)

    with _cache_lock:
        _bt_cache[cache_id] = {"scores": scores, "comp_count": key}

    return scores


def invalidate_bt_cache():
    """Call after any write to comparisons to force refit on next request."""
    with _cache_lock:
        _bt_cache.clear()
    # Also invalidate TrueSkill cache — defined later but that is fine in Python
    try:
        invalidate_ts_cache()
    except NameError:
        pass  # TS cache not yet defined on first call during module load


# ── TrueSkill Engine (trueskill library) ─────────────────────────────────────
#
# WHY TRUESKILL IN PARALLEL:
# Bradley-Terry produces a single point estimate per face. TrueSkill maintains
# a full probability distribution — (μ, σ) per face — where μ is the estimated
# skill and σ is the uncertainty. This has two key advantages:
#
#   1. Uncertainty-aware: faces with high σ are explicitly known to be
#      uncertain. The system can target these directly without needing a
#      separate Phase 4 strategy.
#
#   2. Faster convergence: because uncertainty is tracked explicitly, the
#      model knows when it has learned enough about each face and can focus
#      effort where it is most needed.
#
# Uses the battle-tested `trueskill` library (Herbrich et al. 2007),
# the same algorithm used by Xbox Live matchmaking.
#
# DISPLAY: Scores shown as the conservative estimate μ - 3σ, normalised
# to 0-100. This is standard TrueSkill practice — it represents the score
# we are 99.7% confident the face is at least this attractive.

import trueskill as _ts

# Use default TrueSkill environment (mu=25, sigma=8.333, beta=4.167, tau=0.083)
_TS_ENV = _ts.TrueSkill(draw_probability=0.0)


def fit_trueskill(images, comparisons):
    """
    Replay all comparisons through the TrueSkill library and return per-face scores.

    Returns a dict:
      {image: {"mu": float, "sigma": float, "score": float, "rank_score": float}}

    score      = mu - 3*sigma  (conservative estimate, standard TrueSkill)
    rank_score = score normalised to 0-100 for display

    Images never seen in any comparison get score=None.
    """
    # Initialise all faces with the default TrueSkill prior
    ratings  = {img: _TS_ENV.create_rating() for img in images}
    appeared = set()

    for c in comparisons:
        w, l = c.get("winner"), c.get("loser")
        if w not in ratings or l not in ratings:
            continue
        # "large" magnitude → scale the winner's update by 2×, loser stays normal
        (new_w,), (new_l,) = _TS_ENV.rate(
            [(ratings[w],), (ratings[l],)],
            ranks=[0, 1]   # 0 = winner, 1 = loser
        )
        mag = c.get("magnitude")
        if mag == "large":
            scale = 2.0
            ratings[w] = _ts.Rating(
                ratings[w].mu + (new_w.mu - ratings[w].mu) * scale,
                max(new_w.sigma - (new_w.sigma - ratings[w].sigma) * scale, 0.01))
            ratings[l] = new_l          # loser gets normal update only
        elif mag == "both_ugly":
            # Winner: normal win but also 1.5× the loser's loss applied
            loss_delta = new_l.mu - ratings[l].mu     # negative number
            ratings[w] = _ts.Rating(
                new_w.mu + loss_delta * 0.5,           # pull winner down too
                max(new_w.sigma, 0.01))
            # Loser: 2× loss
            ratings[l] = _ts.Rating(
                ratings[l].mu + (new_l.mu - ratings[l].mu) * 2.0,
                max(new_l.sigma - (new_l.sigma - ratings[l].sigma) * 2.0, 0.01))
        else:
            ratings[w] = new_w
            ratings[l] = new_l
        appeared.update([w, l])

    # Compute conservative scores for ranked faces
    raw_scores = {img: ratings[img].mu - 3 * ratings[img].sigma
                  for img in images if img in appeared}

    if not raw_scores:
        return {img: None for img in images}

    mn  = min(raw_scores.values())
    mx  = max(raw_scores.values())
    rng = mx - mn if mx != mn else 1e-9

    result = {}
    for img in images:
        if img in appeared:
            r   = ratings[img]
            raw = r.mu - 3 * r.sigma
            result[img] = {
                "mu":         round(r.mu,    3),
                "sigma":      round(r.sigma, 3),
                "score":      round(raw,     3),
                "rank_score": round((raw - mn) / rng * 100, 2),
            }
        else:
            result[img] = None
    return result


# ── TrueSkill cache (same lazy strategy as BT cache) ─────────────────────

_ts_cache      = {}
_ts_cache_lock = __import__('threading').Lock()


def get_cached_ts_scores(images, comparisons):
    """Return TrueSkill scores from cache if fresh, else refit."""
    key      = len(comparisons)
    cache_id = "ts_" + str(id(images))

    with _ts_cache_lock:
        entry = _ts_cache.get(cache_id)
        if entry is not None and (key - entry["comp_count"]) < CACHE_REFIT_EVERY:
            return entry["scores"]

    scores = fit_trueskill(images, comparisons)

    with _ts_cache_lock:
        _ts_cache[cache_id] = {"scores": scores, "comp_count": key}

    return scores


def invalidate_ts_cache():
    with _ts_cache_lock:
        _ts_cache.clear()


def build_ts_rankings(images, comparisons, top_n=None):
    """Build a ranked list from TrueSkill scores, parallel to build_rankings."""
    if len(comparisons) < 5:
        return None, "Need at least 5 comparisons to compute TrueSkill rankings."

    scores = get_cached_ts_scores(images, comparisons)
    counts = comparison_counts(images, comparisons)

    ranked = sorted(
        [{"image":      img,
          "mu":         d["mu"],
          "sigma":      d["sigma"],
          "score":      d["score"],
          "rank_score": d["rank_score"],
          "comparisons": counts.get(img, 0)}
         for img, d in scores.items() if d is not None],
        key=lambda x: -x["rank_score"]
    )
    for i, row in enumerate(ranked):
        row["rank"] = i + 1

    if top_n:
        ranked = ranked[:top_n]

    unranked = [{"image": img} for img, d in scores.items() if d is None]
    return {"ranked": ranked, "unranked": unranked,
            "total_comparisons": len(comparisons)}, None


# ── Dynamic zone sizes (all derived from image count — never hardcoded) ──────
#
# WHY DYNAMIC ZONES?
# All zone boundaries are expressed as fractions of the total image count so
# the strategy scales correctly whether the dataset has 84 images or 2000.
# Never use magic numbers like "top 20" — always compute from len(images).

def zone_sizes(n):
    """
    Compute all dynamic zone boundaries for a dataset of n images.

    Returns a dict with integer counts for each zone, all derived from n:
      top_n        : top extreme zone  (~24% of n)
      bot_n        : bottom extreme zone (~24% of n)
      boundary_n   : boundary band outside each extreme (~12% of n)
      anchor_start : start index of mid-ranking anchor band (~40% into ranking)
      anchor_end   : end index of mid-ranking anchor band (~60% into ranking)

    For n=84:  top_n=20, bot_n=20, boundary_n=10, anchor 34-50
    For n=200: top_n=48, bot_n=48, boundary_n=24, anchor 80-120
    For n=2000:top_n=480,bot_n=480,boundary_n=240,anchor 800-1200
    """
    top_n      = max(2, round(n * 0.24))
    bot_n      = max(2, round(n * 0.24))
    boundary_n = max(2, round(n * 0.12))
    anchor_start = round(n * 0.40)
    anchor_end   = round(n * 0.60)
    return {
        "top_n":        top_n,
        "bot_n":        bot_n,
        "boundary_n":   boundary_n,
        "anchor_start": anchor_start,
        "anchor_end":   anchor_end,
    }


def coverage_phase(images, my_comps):
    """
    Returns (phase, unseen_count, unseen_list).

    Phase 1 — not all images seen yet            → prioritise unseen
    Phase 2 — all seen, filling toward target    → mixed adaptive
    Phase 3 — all images at target               → extreme-focused refinement
    Phase 4 — rater manually activated           → bottom-zone deep refinement
                                                    (stored in raters.json)
    """
    seen   = seen_images(my_comps)
    unseen = [img for img in images if img not in seen]

    if unseen:
        return 1, len(unseen), unseen

    counts = comparison_counts(images, my_comps)
    below  = [img for img, c in counts.items() if c < TARGET_PER_IMAGE]
    if below:
        return 2, 0, []

    return 3, 0, []


def adaptive_pair(images, my_comps, pool=None):
    """
    Pick a pair where both images have similar BT scores.
    Uses weighted sampling: weight = 1 / (|score_A - score_B| + 1).

    Optional pool argument restricts selection to a subset of images.
    This is used by Phase 4 to constrain adaptive pairs to the bottom zone.

    Falls back to random if BT scores are not yet available.
    """
    candidates = pool if pool is not None else images
    if len(candidates) < 2:
        candidates = images

    if len(my_comps) < 5:
        return random.sample(candidates, 2)

    scores = get_cached_bt_scores(images, my_comps)
    scored = [(img, sc) for img, sc in scores.items()
              if sc is not None and img in candidates]
    if len(scored) < 2:
        return random.sample(candidates if len(candidates) >= 2 else images, 2)

    img_a, score_a = random.choice(scored)
    others  = [(img, sc) for img, sc in scored if img != img_a]
    weights = np.array([1.0 / (abs(sc - score_a) + 1.0) for _, sc in others])
    weights /= weights.sum()
    idx_b   = np.random.choice(len(others), p=weights)
    return img_a, others[idx_b][0]


def boundary_pair(images, my_comps, bottom_only=False):
    """
    Boundary strategy: one face from an extreme zone, one from the adjacent
    boundary band just outside it.

    WHY: The most valuable comparisons for stabilising the top/bottom lists
    are not within the zone itself, but at the threshold — testing whether
    a face near the edge belongs inside or outside.

    bottom_only=True restricts to bottom zone challenges only (used in Phase 4
    where the top zone is frozen and must not appear in any pair).
    """
    if len(my_comps) < 5:
        return random.sample(images, 2)

    scores = get_cached_bt_scores(images, my_comps)
    scored = sorted(
        [(img, sc) for img, sc in scores.items() if sc is not None],
        key=lambda x: -x[1]
    )
    n = len(scored)
    z = zone_sizes(n)

    top_n      = z["top_n"]
    bot_n      = z["bot_n"]
    boundary_n = z["boundary_n"]

    top_zone     = [img for img, _ in scored[:top_n]]
    top_boundary = [img for img, _ in scored[top_n : min(top_n + boundary_n, n)]]
    bot_zone     = [img for img, _ in scored[max(0, n - bot_n):]]
    bot_boundary = [img for img, _ in scored[max(0, n - bot_n - boundary_n) : max(0, n - bot_n)]]

    if n < top_n + boundary_n:
        return random.sample(images, 2)

    if bottom_only:
        # Phase 4: only challenge the bottom zone — top zone is frozen
        if bot_boundary and bot_zone:
            return random.choice(bot_boundary), random.choice(bot_zone)
        return random.sample(images, 2)

    # Phase 3: challenge either extreme
    if random.random() < 0.5 and top_boundary:
        return random.choice(top_boundary), random.choice(top_zone)
    elif bot_boundary:
        return random.choice(bot_boundary), random.choice(bot_zone)
    return random.sample(images, 2)


def within_extreme_pair(images, my_comps, bottom_only=False):
    """
    Both faces from the same extreme zone, selected adaptively by score
    similarity within the zone (not purely random).

    WHY ADAPTIVE WITHIN THE ZONE: Random within-zone selection wastes
    comparisons on obviously-ordered pairs (rank 1 vs rank 18). Adaptive
    selection within the zone picks the *closest* faces within the zone,
    which is where ordering uncertainty is highest.

    bottom_only=True selects only from the bottom zone (Phase 4 use).
    """
    if len(my_comps) < 5:
        return random.sample(images, 2)

    scores = get_cached_bt_scores(images, my_comps)
    scored = sorted(
        [(img, sc) for img, sc in scores.items() if sc is not None],
        key=lambda x: -x[1]
    )
    n = len(scored)
    z = zone_sizes(n)

    if bottom_only:
        zone_imgs = [img for img, _ in scored[max(0, n - z["bot_n"]):]]
    else:
        # Phase 3: pick top or bottom with equal probability
        if random.random() < 0.5:
            zone_imgs = [img for img, _ in scored[:z["top_n"]]]
        else:
            zone_imgs = [img for img, _ in scored[max(0, n - z["bot_n"]):]]

    if len(zone_imgs) < 2:
        return random.sample(images, 2)

    # Use adaptive (score-similarity) selection within the zone
    return adaptive_pair(images, my_comps, pool=zone_imgs)


def anchor_pair(images, my_comps):
    """
    Phase 4 anchor strategy.

    THE PROBLEM THIS SOLVES:
    When bottom-zone faces only compare against each other, wins accumulate
    within the closed group and scores drift upward — the worst faces start
    to look average because they are winning *some* comparisons. This is a
    fundamental property of the Bradley-Terry model: scores are relative,
    not absolute.

    THE FIX — ANCHORING:
    By occasionally comparing a bottom-zone face against a mid-ranking
    anchor face (ranks ~40-60% of the full list), we keep the bottom zone
    correctly positioned on the full scale. The anchor face acts as a
    calibration reference: bottom faces still lose to it, which counteracts
    the upward drift from within-group wins. The anchor faces themselves are
    not in the top zone, so the top rankings remain completely undisturbed.

    One face drawn from the bottom zone, one from the anchor band.
    """
    if len(my_comps) < 5:
        return random.sample(images, 2)

    scores = get_cached_bt_scores(images, my_comps)
    scored = sorted(
        [(img, sc) for img, sc in scores.items() if sc is not None],
        key=lambda x: -x[1]
    )
    n = len(scored)
    z = zone_sizes(n)

    bot_zone    = [img for img, _ in scored[max(0, n - z["bot_n"]):]]
    anchor_band = [img for img, _ in scored[z["anchor_start"]:z["anchor_end"]]]

    if not bot_zone or not anchor_band:
        return random.sample(images, 2)

    return random.choice(bot_zone), random.choice(anchor_band)


def pick_pair(images, my_comps, phase4_active=False):
    """
    Phase-aware pair selection.  All zone sizes are computed dynamically
    from len(images) via zone_sizes() — nothing is hardcoded.

    Phase 1 — Coverage guarantee:
        One slot always filled from unseen images until all faces appear once.

    Phase 2 — Mixed adaptive:
        60% adaptive       : similar BT scores anywhere (most informative)
        20% least-seen     : least-compared images (coverage balance)
        20% random         : bridge-building

    Phase 3 — Extreme-focused refinement:
        50% boundary       : extreme zone vs adjacent boundary band
        25% adaptive       : similar scores anywhere
        15% within-extreme : adaptive within same zone (top or bottom)
        10% random         : bridge-building

    Phase 4 — Bottom-zone deep refinement (manually activated):

        WHY PHASE 4 EXISTS:
        After Phase 3, the top zone is well-ordered because faces there win
        comparisons and accumulate clearly differentiated scores. The bottom
        zone suffers from the opposite problem: faces that always lose have
        scores near zero, making them indistinguishable. The adaptive strategy
        avoids them because nothing else scores near zero. This phase locks
        the top zone entirely and focuses all comparison effort on the bottom.

        WHY WE NEED ANCHORS:
        Comparing only bottom-zone faces against each other causes score drift
        — wins accumulate and scores rise toward the middle, corrupting the
        global scale. Anchor comparisons against mid-ranking faces (not top-
        zone) keep the bottom zone correctly positioned without disturbing the
        top rankings.

        50% bottom-internal adaptive : both from bottom zone, score-similarity
                                        weighted — orders closely-ranked bad faces
        30% anchor                   : one bottom-zone face vs mid-rank anchor
                                        — prevents upward score drift
        15% bottom boundary          : bottom zone vs adjacent band above it
                                        — maintains the zone boundary
         5% random (bottom half only) : bridge-building within lower half only;
                                        top zone is never selected

        THE GUARANTEE: No top-zone face ever appears in a Phase 4 pair.
    """
    if len(images) < 2:
        return None, None

    phase, _, unseen = coverage_phase(images, my_comps)

    # Phase 4 overrides Phase 3 when manually activated
    if phase4_active and phase == 3:
        roll = random.random()
        if roll < 0.50:
            return within_extreme_pair(images, my_comps, bottom_only=True)
        elif roll < 0.80:
            return anchor_pair(images, my_comps)
        elif roll < 0.95:
            return boundary_pair(images, my_comps, bottom_only=True)
        else:
            # Random restricted to bottom half — top zone never touched
            scores = get_cached_bt_scores(images, my_comps)
            scored = sorted(
                [(img, sc) for img, sc in scores.items() if sc is not None],
                key=lambda x: -x[1]
            )
            n = len(scored)
            bottom_half = [img for img, _ in scored[n // 2:]] if n >= 4 else images
            return random.sample(bottom_half if len(bottom_half) >= 2 else images, 2)

    if phase == 1:
        img_a = random.choice(unseen)
        rest        = [img for img in images if img != img_a]
        unseen_rest = [img for img in unseen  if img != img_a]
        img_b = random.choice(unseen_rest if unseen_rest else rest)
        return img_a, img_b

    if phase == 2:
        roll = random.random()
        if roll < 0.60:
            return adaptive_pair(images, my_comps)
        elif roll < 0.80:
            counts    = comparison_counts(images, my_comps)
            min_count = min(counts.values())
            pool      = [img for img, c in counts.items() if c <= min_count + 2]
            if len(pool) < 2:
                pool = images
            return random.sample(pool, 2)
        else:
            return random.sample(images, 2)

    # Phase 3 — extreme-focused
    roll = random.random()
    if roll < 0.50:
        return boundary_pair(images, my_comps)
    elif roll < 0.75:
        return adaptive_pair(images, my_comps)
    elif roll < 0.90:
        return within_extreme_pair(images, my_comps)
    else:
        return random.sample(images, 2)


# ── TrueSkill zone-biased uncertainty pair selection ─────────────────────────
#
# WHY BOUNDARY COMPARISONS ARE WEIGHTED MOST (35%):
#   The faces most likely to be mis-ranked sit at zone boundaries — a face
#   just inside the top zone vs one just outside it. Getting these boundary
#   decisions right has the biggest impact on the final top/bottom ordering.
#   Both faces in a boundary pair are chosen weighted by σ, so the model
#   automatically spends more effort on the boundaries it is least sure about.
#
# WHY WITHIN-EXTREME GETS 30%:
#   Once a face is confirmed as "top" or "bottom", we still need to order
#   faces *within* each extreme zone. Comparing two top-zone faces (or two
#   bottom-zone) with σ-weighting sharpens internal ordering where it matters.
#
# WHY σ-WEIGHTING INSTEAD OF SCORE-SIMILARITY:
#   BT's adaptive strategy pairs faces with similar scores (small |Δ|).
#   TrueSkill's σ is strictly better: σ tells you *how much the model would
#   learn* from seeing a face again, regardless of its score. A face with
#   high σ and a middling score is more informative than two low-σ faces
#   with nearly identical scores — the model already knows those two well.
#
# WHY 15% RANDOM (HIGHER THAN USUAL):
#   Aggressive zone-targeting risks "bridge starvation": faces in the middle
#   get very few comparisons, making it impossible to calibrate extreme-zone
#   faces against the full population. 15% random ensures every face gets
#   occasional comparisons that anchor the global scale.

# Track recent pairs per image to avoid repetition
_recent_pairs = {}          # {image: deque(maxlen=RECENT_PAIR_MEMORY)}
RECENT_PAIR_MEMORY = 5      # remember last N partners per face


def _record_recent(a, b):
    """Record that A and B were just paired so we can avoid repeating them."""
    from collections import deque
    for x, y in [(a, b), (b, a)]:
        if x not in _recent_pairs:
            _recent_pairs[x] = deque(maxlen=RECENT_PAIR_MEMORY)
        _recent_pairs[x].append(y)


def _sigma_weighted_pick(pool):
    """Pick one (image, sigma) from pool using σ-weighted random sampling."""
    imgs, sigs = zip(*pool)
    w = np.array(sigs)
    w /= w.sum()
    idx = np.random.choice(len(imgs), p=w)
    return imgs[idx]


def _sigma_weighted_pair(pool):
    """Pick two distinct items from pool using σ-weighted sampling."""
    img_a = _sigma_weighted_pick(pool)
    rest  = [(img, sig) for img, sig in pool if img != img_a]
    if not rest:
        return random.sample([img for img, _ in pool], 2)
    img_b = _sigma_weighted_pick(rest)
    return img_a, img_b


def ts_uncertainty_pair(images, my_comps):
    """
    Zone-biased TrueSkill pair selection.

    Strategy mix (all σ-weighted within each category):
      35% boundary       — one face from an extreme zone (top or bottom),
                           one from the adjacent boundary band outside it.
      30% within-extreme — both faces from the same extreme zone.
      20% global σ       — any two faces, weighted by σ globally.
      15% random         — pure uniform random (bridge starvation prevention).

    All zone boundaries computed dynamically via zone_sizes(n).
    Falls back to global σ if a zone has fewer than 2 scored faces.
    """
    if len(my_comps) < 5:
        pair = random.sample(images, 2)
        _record_recent(*pair)
        return pair

    ts_scores = get_cached_ts_scores(images, my_comps)

    # Build scored list sorted by TrueSkill rank_score descending
    scored_raw = [(img, d) for img, d in ts_scores.items() if d is not None]
    if len(scored_raw) < 2:
        pair = random.sample(images, 2)
        _record_recent(*pair)
        return pair

    scored_sorted = sorted(scored_raw, key=lambda x: -x[1]["rank_score"])
    n = len(scored_sorted)
    z = zone_sizes(n)

    # Build zone pools as [(image, sigma), ...]
    top_zone  = [(img, d["sigma"]) for img, d in scored_sorted[:z["top_n"]]]
    bot_zone  = [(img, d["sigma"]) for img, d in scored_sorted[n - z["bot_n"]:]]
    # Boundary band: faces just outside each extreme zone
    top_boundary = [(img, d["sigma"]) for img, d in
                    scored_sorted[z["top_n"]:z["top_n"] + z["boundary_n"]]]
    bot_boundary = [(img, d["sigma"]) for img, d in
                    scored_sorted[max(0, n - z["bot_n"] - z["boundary_n"]):n - z["bot_n"]]]
    all_scored   = [(img, d["sigma"]) for img, d in scored_sorted]

    # Helper: attempt a strategy, fall back to global σ if zone too small
    def try_boundary():
        """One face from extreme zone, one from adjacent boundary band."""
        if random.random() < 0.5:
            zone, band = top_zone, top_boundary
        else:
            zone, band = bot_zone, bot_boundary
        if len(zone) < 1 or len(band) < 1:
            return _sigma_weighted_pair(all_scored)
        return _sigma_weighted_pick(zone), _sigma_weighted_pick(band)

    def try_within_extreme():
        """Both faces from the same extreme zone."""
        zone = top_zone if random.random() < 0.5 else bot_zone
        if len(zone) < 2:
            return _sigma_weighted_pair(all_scored)
        return _sigma_weighted_pair(zone)

    def global_sigma():
        """Any two faces, σ-weighted."""
        return _sigma_weighted_pair(all_scored)

    # ── Roll strategy ──
    roll = random.random()
    if roll < 0.35:
        a, b = try_boundary()
    elif roll < 0.65:
        a, b = try_within_extreme()
    elif roll < 0.85:
        a, b = global_sigma()
    else:
        a, b = random.sample(images, 2)

    _record_recent(a, b)
    return a, b


def pick_pair_trueskill(images, my_comps):
    """
    TrueSkill model pair selection.

    Phase 1 — identical to BT: always include unseen faces first.
              TrueSkill cannot rank a face it has never seen, so full
              coverage is still required before uncertainty-guided
              selection can work.

    After Phase 1 — single uncertainty strategy replaces BT phases 2/3/4.
    """
    if len(images) < 2:
        return None, None

    phase, _, unseen = coverage_phase(images, my_comps)

    if phase == 1:
        # Identical to BT Phase 1
        img_a = random.choice(unseen)
        rest        = [img for img in images if img != img_a]
        unseen_rest = [img for img in unseen  if img != img_a]
        img_b = random.choice(unseen_rest if unseen_rest else rest)
        return img_a, img_b

    # All images seen — use TrueSkill uncertainty to pick the most
    # informative pair
    return ts_uncertainty_pair(images, my_comps)


# ── Top-level pair dispatcher ────────────────────────────────────────────────

def pick_pair_dispatch(images, my_comps, phase4_active=False, model=None):
    effective = model or PAIR_SELECTION_MODEL
    if effective == "TrueSkill":
        return pick_pair_trueskill(images, my_comps)
    else:
        return pick_pair(images, my_comps, phase4_active=phase4_active)


# ── Bradley-Terry ─────────────────────────────────────────────────────────────

def fit_bradley_terry(images, comparisons, max_iter=1000, tol=1e-6):
    """MM algorithm. Returns {image: score 0-100} or None for unseen faces."""
    n = len(images)
    if n == 0:
        return {}
    idx = {img: i for i, img in enumerate(images)}

    wins     = np.zeros(n)
    total    = np.zeros((n, n))
    appeared = set()

    for c in comparisons:
        w, l = c["winner"], c["loser"]
        if w not in idx or l not in idx:
            continue
        wi, li = idx[w], idx[l]
        wins[wi] += 1
        total[wi, li] += 1
        total[li, wi] += 1
        appeared.update([w, l])

    # Sparse vectorised MM: extract non-zero indices once, then each
    # iteration is O(observed_pairs) instead of O(n²) Python loops.
    ii, jj = np.nonzero(total)
    tij = total[ii, jj]

    strength = np.ones(n)
    for _ in range(max_iter):
        sij   = tij / (strength[ii] + strength[jj])
        denom = np.zeros(n)
        np.add.at(denom, ii, sij)
        new_s = np.where(denom > 0, wins / denom, strength)
        s = new_s.sum()
        if s > 0:
            new_s /= s
        if np.max(np.abs(new_s - strength)) < tol:
            strength = new_s
            break
        strength = new_s

    raw    = np.log(strength + 1e-9)
    mn, mx = raw.min(), raw.max()
    normed = (raw - mn) / (mx - mn + 1e-9) * 100

    return {
        img: (round(float(normed[idx[img]]), 2) if img in appeared else None)
        for img in images
    }


def build_rankings(images, comparisons, top_n=None):
    if len(comparisons) < 5:
        return None, "Need at least 5 comparisons to compute rankings."
    scores = get_cached_bt_scores(images, comparisons)
    counts = comparison_counts(images, comparisons)
    ranked = sorted(
        [{"image": img, "score": sc, "comparisons": counts.get(img, 0)}
         for img, sc in scores.items() if sc is not None],
        key=lambda x: -x["score"]
    )
    for i, row in enumerate(ranked):
        row["rank"] = i + 1

    if top_n:
        ranked = ranked[:top_n]

    unranked = [
        {"image": img, "score": None, "comparisons": 0}
        for img, sc in scores.items() if sc is None
    ]
    return {"ranked": ranked, "unranked": unranked,
            "total_comparisons": len(comparisons)}, None


def _stats(images, all_comps, my_comps, phase4_active=False, model=None):
    """Rich stats dict sent with every pair response."""
    effective_model = model or PAIR_SELECTION_MODEL
    my_counts  = comparison_counts(images, my_comps)
    seen       = seen_images(my_comps)
    phase, unseen_count, _ = coverage_phase(images, my_comps)

    images_rated = len(seen)
    total_images = len(images)
    z            = zone_sizes(total_images)

    if effective_model == "TrueSkill" and phase != 1:
        effective_phase = "ts"
    elif phase4_active and phase == 3:
        effective_phase = 4
    else:
        effective_phase = phase

    return {
        "total_comparisons":    len(all_comps),
        "my_comparisons":       len(my_comps),
        "total_images":         total_images,
        "images_rated":         images_rated,
        "images_unseen":        unseen_count,
        "min_comparisons":      min(my_counts.values()) if my_counts else 0,
        "avg_comparisons":      round(
            sum(my_counts.values()) / len(my_counts), 1) if my_counts else 0,
        "phase":                effective_phase,
        "phase4_active":        phase4_active,
        "pair_selection_model": effective_model,
        "zone_top_n":           z["top_n"],
        "zone_bot_n":           z["bot_n"],
        "progress_pct":         min(100, round(
            len(my_comps) / (total_images * TARGET_PER_IMAGE) * 100))
            if total_images else 0,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET"])
def login_page():
    if not (SITE_LOGIN_REQUIRED and SITE_PASSWORD) or session.get("site_authed"):
        from flask import redirect
        return redirect("/")
    return render_template("login.html")


@app.route("/api/site-login", methods=["POST"])
def api_site_login():
    password = (request.json or {}).get("password", "")
    if SITE_PASSWORD and password != SITE_PASSWORD:
        return jsonify({"error": "Incorrect password."}), 401
    session["site_authed"] = True
    return jsonify({"ok": True})


@app.route("/")
@site_auth_required
def index():
    _load_config()
    folders = list_datasets()
    n_images = len(get_images(folders[0])) if folders else 0
    rater  = None
    if "rater_id" in session:
        rater = load_raters().get(session["rater_id"])
    if SHOW_SECTION_PAIRWISE:
        default_tab = "compare"
    elif SHOW_SECTION_STACK:
        default_tab = "rankedgrouping"
    elif SHOW_SECTION_CATEGORY:
        default_tab = "category"
    else:
        default_tab = "compare"
    return render_template("index.html", n_images=n_images, rater=rater,
                           target=TARGET_PER_IMAGE,
                           pairwise_default_folder=PAIRWISE_FOLDER or "",
                           pairwise_show_selector=PAIRWISE_FOLDER_SELECTOR,
                           show_intro=SHOW_INTRO,
                           show_pairwise=SHOW_SECTION_PAIRWISE,
                           show_stack=SHOW_SECTION_STACK,
                           show_category=SHOW_SECTION_CATEGORY,
                           default_tab=default_tab,
                           ui_font_size=UI_FONT_SIZE)


@app.route("/image/<path:filename>")
@site_auth_required
def serve_image(filename):
    folder = request.args.get("folder")
    if folder:
        d = DATASETS_DIR / folder
        if d.exists() and (d / filename).exists():
            return send_from_directory(str(d), filename)
    # Search all dataset folders
    for name in list_datasets():
        d = DATASETS_DIR / name
        if (d / filename).exists():
            return send_from_directory(str(d), filename)
    abort(404)


# ── Rater API ─────────────────────────────────────────────────────────────────

@app.route("/api/check-email", methods=["POST"])
def api_check_email():
    """
    Check whether an email belongs to a returning user.
    Returns {exists: true, name: ...} for known raters so the UI can
    skip the demographics form and log them straight in.
    """
    email = ((request.json or {}).get("email") or "").strip().lower()
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    rater_id = email_to_id(email)
    raters   = load_raters()
    if rater_id in raters:
        p = raters[rater_id]
        return jsonify({"exists": True, "name": p.get("name") or email})
    return jsonify({"exists": False})


@app.route("/api/register", methods=["POST"])
def api_register():
    d     = request.json
    email = (d.get("email") or "").strip().lower()
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    rater_id = email_to_id(email)
    raters   = load_raters()
    profile  = raters.get(rater_id, {
        "rater_id":   rater_id,
        "email":      email,
        "registered": datetime.utcnow().isoformat(),
    })
    # For returning users doing a quick login, only email is sent —
    # don't overwrite demographics with empty values in that case.
    if d.get("full_form"):
        profile.update({
            "name":                      (d.get("name") or "").strip(),
            "age":                       d.get("age"),
            "gender":                    d.get("gender"),
            "ethnicity":                 d.get("ethnicity"),
            "nationality":               (d.get("nationality") or "").strip(),
        })
    profile["last_login"] = datetime.utcnow().isoformat()
    raters[rater_id] = profile
    save_raters(raters)
    session["rater_id"]   = rater_id
    session["rater_name"] = profile["name"] or email
    return jsonify({"ok": True, "rater_id": rater_id,
                    "name": profile["name"] or email})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    if "rater_id" not in session:
        return jsonify({"logged_in": False})
    folder   = request.args.get("folder") or _first_pairwise_folder()
    raters   = load_raters()
    profile  = raters.get(session["rater_id"], {})
    images   = get_images(folder)
    all_comp = load_comparisons(folder)
    my_comp  = filter_comparisons(all_comp, session["rater_id"])
    phase4   = profile.get("phase4_active", False)
    stats    = _stats(images, all_comp, my_comp, phase4)
    return jsonify({
        "logged_in":   True,
        "rater_id":    session["rater_id"],
        "name":        session.get("rater_name"),
        "profile":     profile,
        **stats,
    })


# ── Pair / compare API ────────────────────────────────────────────────────────

@app.route("/api/pair")
def api_pair():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    folder   = request.args.get("folder") or _first_pairwise_folder()
    images   = get_images(folder)
    if len(images) < 2:
        return jsonify({"error": f"Need at least 2 images in the {folder}/ folder."}), 400
    all_comp    = load_comparisons(folder)
    my_comp     = filter_comparisons(all_comp, session["rater_id"])
    raters      = load_raters()
    phase4      = raters.get(session["rater_id"], {}).get("phase4_active", False)
    model       = session.get("pair_selection_model", PAIR_SELECTION_MODEL)
    a, b        = pick_pair_dispatch(images, my_comp, phase4_active=phase4, model=model)
    return jsonify({"left": a, "right": b,
                    "stats": _stats(images, all_comp, my_comp, phase4, model=model)})


@app.route("/api/compare", methods=["POST"])
def api_compare():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401

    d         = request.json
    winner    = d.get("winner")
    loser     = d.get("loser")
    skipped   = d.get("skipped", False)
    magnitude = d.get("magnitude", "normal")  # "normal", "large", or "both_ugly"
    if magnitude not in ("normal", "large", "both_ugly"):
        magnitude = "normal"
    folder    = d.get("folder") or _first_pairwise_folder()

    images   = get_images(folder)
    all_comp = load_comparisons(folder)

    if not skipped:
        if winner not in images or loser not in images:
            return jsonify({"error": "Unknown image"}), 400
        entry = {
            "winner":    winner,
            "loser":     loser,
            "rater_id":  session["rater_id"],
            "timestamp": datetime.utcnow().isoformat(),
            "magnitude": magnitude,
        }
        if session.get("pending_correction"):
            # Overwrite the last entry for this rater in-place
            last = session.get("last_comparison", {})
            for i in range(len(all_comp) - 1, -1, -1):
                c = all_comp[i]
                if (c.get("rater_id") == session["rater_id"] and
                        c.get("winner") == last.get("winner") and
                        c.get("loser")  == last.get("loser")):
                    all_comp[i] = entry   # replace, don't append
                    break
            session["pending_correction"] = False
        else:
            all_comp.append(entry)
        save_comparisons(all_comp, folder)
        # Store the just-saved comparison so undo can restore this exact pair
        session["last_comparison"] = {"winner": winner, "loser": loser}
        session["last_comparison_folder"] = folder
        session["can_undo"] = True
    else:
        session["can_undo"] = False

    my_comp  = filter_comparisons(all_comp, session["rater_id"])
    raters   = load_raters()
    phase4   = raters.get(session["rater_id"], {}).get("phase4_active", False)
    model    = session.get("pair_selection_model", PAIR_SELECTION_MODEL)
    a, b     = pick_pair_dispatch(images, my_comp, phase4_active=phase4, model=model)
    return jsonify({"left": a, "right": b,
                    "can_undo": session.get("can_undo", False),
                    "stats": _stats(images, all_comp, my_comp, phase4, model=model)})


@app.route("/api/undo", methods=["POST"])
def api_undo():
    """Restore the last pair so the rater can resubmit a corrected choice."""
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    if not session.get("can_undo", False):
        return jsonify({"error": "Nothing to undo."}), 400

    folder   = session.get("last_comparison_folder") or _first_pairwise_folder()
    last     = session.get("last_comparison", {})
    images   = get_images(folder)
    all_comp = load_comparisons(folder)
    my_comp  = filter_comparisons(all_comp, session["rater_id"])

    # Don't touch the JSON yet — just flag that the next submission
    # should overwrite the last entry rather than append a new one.
    session["pending_correction"] = True
    session["can_undo"] = False

    return jsonify({
        "left":     last.get("winner"),   # restore original positions
        "right":    last.get("loser"),
        "can_undo": False,
        "stats":    _stats(images, all_comp, my_comp,
                           model=session.get("pair_selection_model", PAIR_SELECTION_MODEL)),
    })


@app.route("/api/activate-phase4", methods=["POST"])
def api_activate_phase4():
    """
    Manually activate Phase 4 for this rater.

    Phase 4 locks the top zone and focuses all comparison effort on ordering
    the bottom zone correctly. This is a one-way transition stored in
    raters.json so it persists across sessions.

    The rater must be in Phase 3 to activate Phase 4.
    """
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401

    folder   = request.args.get("folder") or _first_pairwise_folder()
    images   = get_images(folder)
    all_comp = load_comparisons(folder)
    my_comp  = filter_comparisons(all_comp, session["rater_id"])
    phase, _, _ = coverage_phase(images, my_comp)

    if phase < 3:
        return jsonify({"error": "Phase 4 requires Phase 3 to be complete first."}), 400

    raters   = load_raters()
    rater_id = session["rater_id"]
    if rater_id in raters:
        raters[rater_id]["phase4_active"]    = True
        raters[rater_id]["phase4_activated"] = datetime.utcnow().isoformat()
        save_raters(raters)

    # Serve first Phase 4 pair immediately
    phase4 = True
    model  = session.get("pair_selection_model", PAIR_SELECTION_MODEL)
    a, b   = pick_pair_dispatch(images, my_comp, phase4_active=phase4, model=model)
    return jsonify({
        "ok":    True,
        "left":  a,
        "right": b,
        "stats": _stats(images, all_comp, my_comp, phase4, model=model),
    })


# ── Rankings API ──────────────────────────────────────────────────────────────

@app.route("/api/rankings")
def api_rankings():
    folder   = request.args.get("folder") or _first_pairwise_folder()
    images   = get_images(folder)
    all_comp = load_comparisons(folder)
    view     = request.args.get("view", "consensus")
    top_n    = request.args.get("top", None)
    if top_n:
        top_n = int(top_n)

    if view == "mine" and "rater_id" in session:
        comps = filter_comparisons(all_comp, session["rater_id"])
        label = "My rankings"
    elif view.startswith("rater:"):
        rid   = view.split(":", 1)[1]
        comps = filter_comparisons(all_comp, rid)
        label = f"Rater {rid}"
    elif view.startswith("gender:"):
        gender_filter = view.split(":", 1)[1].lower()
        raters_data   = load_raters()
        gender_ids    = {rid for rid, r in raters_data.items() if (r.get("gender") or "").lower() == gender_filter}
        qualified     = qualified_consensus_comparisons(all_comp)
        comps         = [c for c in qualified if c.get("rater_id") in gender_ids]
        label         = f"{'Male' if gender_filter == 'male' else 'Female'} Raters (\u2265{MIN_COMPARISONS_FOR_CONSENSUS} comparisons)"
    else:
        comps = qualified_consensus_comparisons(all_comp)
        label = f"Consensus (raters \u2265{MIN_COMPARISONS_FOR_CONSENSUS} comparisons)"

    result, err = build_rankings(images, comps, top_n=top_n)
    if err:
        return jsonify({"error": err}), 400
    result["view"]  = view
    result["label"] = label
    return jsonify(result)


@app.route("/api/ts-rankings")
def api_ts_rankings():
    """TrueSkill rankings endpoint — parallel to /api/rankings."""
    folder   = request.args.get("folder") or _first_pairwise_folder()
    images   = get_images(folder)
    all_comp = load_comparisons(folder)
    view     = request.args.get("view", "consensus")

    if view == "mine" and "rater_id" in session:
        comps = filter_comparisons(all_comp, session["rater_id"])
        label = "My TrueSkill rankings"
    elif view.startswith("rater:"):
        rid   = view.split(":", 1)[1]
        comps = filter_comparisons(all_comp, rid)
        label = f"Rater {rid} \u2014 TrueSkill"
    elif view.startswith("gender:"):
        gender_filter = view.split(":", 1)[1].lower()
        raters_data   = load_raters()
        gender_ids    = {rid for rid, r in raters_data.items() if (r.get("gender") or "").lower() == gender_filter}
        qualified     = qualified_consensus_comparisons(all_comp)
        comps         = [c for c in qualified if c.get("rater_id") in gender_ids]
        label         = f"{'Male' if gender_filter == 'male' else 'Female'} Raters TrueSkill (\u2265{MIN_COMPARISONS_FOR_CONSENSUS} comparisons)"
    else:
        comps = qualified_consensus_comparisons(all_comp)
        label = f"Consensus TrueSkill (raters \u2265{MIN_COMPARISONS_FOR_CONSENSUS} comparisons)"

    result, err = build_ts_rankings(images, comps)
    if err:
        return jsonify({"error": err}), 400

    # Also compute BT rankings for comparison
    bt_result, _ = build_rankings(images, comps)
    bt_ranks = {}
    if bt_result:
        for row in bt_result["ranked"]:
            bt_ranks[row["image"]] = row["rank"]

    # Annotate each TS row with BT rank and rank difference
    for row in result["ranked"]:
        bt_rank = bt_ranks.get(row["image"])
        row["bt_rank"]   = bt_rank
        row["rank_diff"] = (bt_rank - row["rank"]) if bt_rank else None

    result["view"]  = view
    result["label"] = label
    return jsonify(result)


@app.route("/api/my-top20")
def api_my_top20():
    """Per-rater top-20 with coverage info — used by the My Progress panel."""
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401

    folder   = request.args.get("folder") or _first_pairwise_folder()
    images   = get_images(folder)
    all_comp = load_comparisons(folder)
    my_comp  = filter_comparisons(all_comp, session["rater_id"])

    stats    = _stats(images, all_comp, my_comp)

    # Coverage breakdown per image
    counts   = comparison_counts(images, my_comp)
    seen     = seen_images(my_comp)

    coverage = {
        "seen":   len(seen),
        "unseen": len(images) - len(seen),
        "total":  len(images),
        "phase":  stats["phase"],
        # Breakdown buckets
        "bucket_0":  sum(1 for c in counts.values() if c == 0),
        "bucket_1_4": sum(1 for c in counts.values() if 1 <= c <= 4),
        "bucket_5_9": sum(1 for c in counts.values() if 5 <= c <= 9),
        "bucket_10p": sum(1 for c in counts.values() if c >= TARGET_PER_IMAGE),
    }

    # Top-20 and bottom-20 personal rankings (use the active model)
    active_model = session.get("pair_selection_model", PAIR_SELECTION_MODEL)
    if len(my_comp) >= 5:
        if active_model == "TrueSkill":
            result, err = build_ts_rankings(images, my_comp)
        else:
            result, err = build_rankings(images, my_comp)
        if result:
            ranked = result["ranked"]
            # Normalise the score field shown in the UI to 0-100 for both models
            if active_model == "TrueSkill":
                for row in ranked:
                    row["score"] = row["rank_score"]
            top20    = ranked[:20]
            bottom20 = list(reversed(ranked[-20:]))
        else:
            top20 = bottom20 = []
    else:
        top20 = bottom20 = []
        err   = "Need at least 5 comparisons for rankings."

    return jsonify({
        "stats":    stats,
        "coverage": coverage,
        "top20":    top20,
        "bottom20": bottom20,
        "message":  err,
    })


def _self_consistency(comparisons):
    """Transitivity: for chains A>B, B>C where A vs C was also compared,
    what % have A>C (logically consistent)?  Returns None if < 10 comparisons."""
    beats = defaultdict(set)
    for c in comparisons:
        w, l = c.get("winner"), c.get("loser")
        if w and l:
            beats[w].add(l)

    all_images = list(beats.keys())
    triples = []
    for b in all_images:
        for c in beats[b]:
            for a in all_images:
                if b in beats[a] and c != a:
                    triples.append((a, b, c))

    # Sample to keep it fast
    if len(triples) > 20000:
        random.shuffle(triples)
        triples = triples[:20000]

    ok = 0
    checked = 0
    for a, b, c in triples:
        if c in beats[a]:
            ok += 1; checked += 1
        elif a in beats[c]:
            checked += 1
    return round(ok / checked * 100, 1) if checked > 0 else None


def _conformity(comparisons, consensus_scores):
    """% of a rater's comparisons where they picked the face ranked higher
    by the consensus BT model.  Returns None if not enough data."""
    if not consensus_scores or len(comparisons) < 5:
        return None
    agree = 0
    total = 0
    for c in comparisons:
        w, l = c.get("winner"), c.get("loser")
        ws = consensus_scores.get(w)
        ls = consensus_scores.get(l)
        if ws is not None and ls is not None and ws != ls:
            total += 1
            if ws > ls:
                agree += 1
    return round(agree / total * 100, 1) if total > 0 else None


@app.route("/api/raters")
def api_raters():
    folder   = request.args.get("folder") or _first_pairwise_folder()
    raters   = load_raters()
    all_comp = load_comparisons(folder)
    all_cats = load_categories(folder)
    images   = get_images(folder)

    # Consensus BT scores for conformity calculation
    consensus_scores = get_cached_bt_scores(images, all_comp) if len(all_comp) >= 5 else {}

    # Category rating counts per rater for this folder
    from collections import Counter
    ratings_counts = Counter(c.get("rater_id") for c in all_cats if c.get("rater_id"))

    summary  = []
    for rid, p in raters.items():
        my_comp = filter_comparisons(all_comp, rid)
        seen    = seen_images(my_comp)

        summary.append({
            "rater_id":        rid,
            "name":            p.get("name") or p.get("email"),
            "gender":          p.get("gender"),
            "age":             p.get("age"),
            "ethnicity":       p.get("ethnicity"),
            "nationality":     p.get("nationality"),
            "comparisons":     len(my_comp),
            "ratings":         ratings_counts.get(rid, 0),
            "images_rated":    len(seen),
            "registered":      p.get("registered"),
            "self_consistency": _self_consistency(my_comp) if len(my_comp) >= 10 else None,
            "conformity":      _conformity(my_comp, consensus_scores),
        })
    summary.sort(key=lambda x: -x["comparisons"])
    return jsonify({"raters": summary, "total": len(summary),
                    "total_images": len(images)})


# ── Model toggle ──────────────────────────────────────────────────────────────

@app.route("/api/toggle-model", methods=["POST"])
def api_toggle_model():
    """Toggle the pair-selection model for this session only."""
    current = session.get("pair_selection_model", PAIR_SELECTION_MODEL)
    new_model = "BT" if current == "TrueSkill" else "TrueSkill"
    session["pair_selection_model"] = new_model
    return jsonify({"model": new_model})


# ── Export ────────────────────────────────────────────────────────────────────

@app.route("/api/export")
def api_export():
    folder   = request.args.get("folder") or _first_pairwise_folder()
    images   = get_images(folder)
    all_comp = load_comparisons(folder)
    view     = request.args.get("view", "consensus")

    if view == "mine" and "rater_id" in session:
        comps    = filter_comparisons(all_comp, session["rater_id"])
        filename = f"bt_rankings_{session['rater_id']}.csv"
    else:
        comps    = all_comp
        filename = "bt_rankings_consensus.csv"

    scores = get_cached_bt_scores(images, comps) if len(comps) >= 5 else {}
    counts = comparison_counts(images, comps)
    ranked = sorted(
        [(img, sc) for img, sc in scores.items() if sc is not None],
        key=lambda x: -x[1]
    )
    lines = ["rank,image,bt_score,comparisons"]
    for i, (img, sc) in enumerate(ranked, 1):
        lines.append(f"{i},{img},{sc},{counts.get(img, 0)}")
    return Response(
        "\n".join(lines), mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/api/export/ts-rankings")
def api_export_ts_rankings():
    """Export TrueSkill rankings as CSV."""
    folder   = request.args.get("folder") or _first_pairwise_folder()
    images   = get_images(folder)
    all_comp = load_comparisons(folder)
    view     = request.args.get("view", "consensus")

    if view == "mine" and "rater_id" in session:
        comps    = filter_comparisons(all_comp, session["rater_id"])
        filename = f"ts_rankings_{session['rater_id']}.csv"
    else:
        comps    = all_comp
        filename = "ts_rankings_consensus.csv"

    result, _ = build_ts_rankings(images, comps)
    if not result:
        return Response("No data", mimetype="text/plain")

    lines = ["rank,image,mu,sigma,rank_score,comparisons"]
    for row in result["ranked"]:
        lines.append(f"{row['rank']},{row['image']},{row['mu']},"
                     f"{row['sigma']},{row['rank_score']},{row['comparisons']}")
    return Response(
        "\n".join(lines), mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/api/export/comparisons")
def api_export_comparisons():
    folder   = request.args.get("folder") or _first_pairwise_folder()
    all_comp = load_comparisons(folder)
    raters   = load_raters()
    lines    = ["timestamp,winner,loser,rater_id,rater_name,"
                "gender,age,ethnicity,nationality"]
    for c in all_comp:
        rid = c.get("rater_id", "")
        p   = raters.get(rid, {})
        lines.append(",".join(str(x) for x in [
            c.get("timestamp", ""),
            c.get("winner", ""),
            c.get("loser", ""),
            rid,
            p.get("name", ""),
            p.get("gender", ""),
            p.get("age", ""),
            p.get("ethnicity", ""),
            p.get("nationality", ""),
        ]))
    return Response(
        "\n".join(lines), mimetype="text/csv",
        headers={"Content-Disposition":
                 "attachment; filename=comparisons_with_raters.csv"}
    )


# ── Category helpers ──────────────────────────────────────────────────────────

VALID_CATEGORIES = {"1", "2", "3", "4", "5"}


def load_categories(folder: str):
    f = _categories_file(folder)
    if f.exists():
        with open(f) as fh:
            return json.load(fh)
    return []


def save_categories(data, folder: str):
    f = _categories_file(folder)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "w") as fh:
        json.dump(data, fh, indent=2)


def _guest_categories_file(folder: str) -> Path:
    return RESULTS_DIR / _folder_slug(folder) / "categories_guest.json"

def load_guest_categories(folder: str) -> list:
    f = _guest_categories_file(folder)
    return json.load(open(f)) if f.exists() else []

def save_guest_categories(data: list, folder: str) -> None:
    f = _guest_categories_file(folder)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "w") as fh:
        json.dump(data, fh, indent=2)


@app.route("/api/face-folders")
@site_auth_required
def api_face_folders():
    """Return all datasets (subfolders of datasets/) that hold images."""
    return jsonify({"folders": list_datasets()})


@app.route("/api/category-next")
@site_auth_required
def api_category_next():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    folder = request.args.get("folder") or _first_dataset()
    images = get_category_images(folder)
    cats   = load_guest_categories(folder) if folder in PROTECTED_FOLDERS else load_categories(folder)
    done   = {c["image"] for c in cats if c.get("rater_id") == session["rater_id"]}
    remaining = [img for img in images if img not in done]
    if not remaining:
        return jsonify({"image": None, "prefetch": None, "done": len(done), "total": len(images)})
    return jsonify({
        "image":    remaining[0],
        "prefetch": remaining[1] if len(remaining) > 1 else None,
        "done":     len(done),
        "total":    len(images),
    })


@app.route("/api/categorize", methods=["POST"])
@site_auth_required
def api_categorize():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    d      = request.json
    image  = d.get("image")
    cat    = d.get("category")
    folder = d.get("folder") or _first_dataset()
    if cat not in VALID_CATEGORIES:
        return jsonify({"error": "Invalid category"}), 400
    images = get_category_images(folder)
    if image not in images:
        return jsonify({"error": "Unknown image"}), 400
    protected = folder in PROTECTED_FOLDERS
    cats = load_guest_categories(folder) if protected else load_categories(folder)
    # Overwrite if this rater already categorised this image
    cats = [c for c in cats
            if not (c.get("rater_id") == session["rater_id"] and c.get("image") == image)]
    cats.append({
        "image":     image,
        "category":  cat,
        "rater_id":  session["rater_id"],
        "timestamp": datetime.utcnow().isoformat(),
    })
    if protected:
        save_guest_categories(cats, folder)
    else:
        save_categories(cats, folder)
    # Return next image
    done = {c["image"] for c in cats if c.get("rater_id") == session["rater_id"]}
    remaining = [img for img in images if img not in done]
    return jsonify({
        "image":    remaining[0] if remaining else None,
        "prefetch": remaining[1] if len(remaining) > 1 else None,
        "done":     len(done),
        "total":    len(images),
    })


@app.route("/api/category-groupings")
@site_auth_required
def api_category_groupings():
    """Return faces grouped by category, ordered within each group by model ranking."""
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401

    view   = request.args.get("view", "mine")      # "mine", "consensus", or "rater:<id>"
    model  = request.args.get("model", "ts")        # "bt" or "ts"
    folder = request.args.get("folder") or _first_dataset()

    images   = get_category_images(folder)
    all_comp = load_comparisons()

    # Mine view on protected folders reads the guest file; everything else uses the official file
    if view == "mine" and folder in PROTECTED_FOLDERS:
        mine_cats = load_guest_categories(folder)
        all_cats  = load_categories(folder)
    else:
        all_cats  = load_categories(folder)
        mine_cats = all_cats

    # Determine which rater's categories to show
    if view == "mine":
        rater_cats = [c for c in mine_cats if c.get("rater_id") == session["rater_id"]]
        label = "My Categories"
    elif view == "consensus":
        rater_cats = _consensus_categories(all_cats, images)
        label = "Consensus Categories"
    elif view.startswith("rater:"):
        rid = view.split(":", 1)[1]
        rater_cats = [c for c in all_cats if c.get("rater_id") == rid]
        raters = load_raters()
        rname  = raters.get(rid, {}).get("name", "Unknown")
        label  = f"{rname}'s Categories"
    else:
        rater_cats = []
        label = "Categories"

    # Build image → category map
    cat_map = {}
    for c in rater_cats:
        cat_map[c["image"]] = c["category"]

    # Get ranking scores / order
    if model == "none":
        def sort_key(img): return img          # alphabetical by filename
        def sort_reverse(): return False
    elif model == "manual":
        mkey   = f"{session['rater_id']}:{folder}"
        mdata  = json.load(open(MANUAL_RANKS_FILE)) if MANUAL_RANKS_FILE.exists() else {}
        mranks = mdata.get(mkey, {}).get("ranks", [])
        rank_pos = {img: i for i, img in enumerate(mranks)}
        def sort_key(img):
            return rank_pos.get(img, len(mranks))
        def sort_reverse(): return False
    elif model == "group_avg":
        rd, _ = _build_rating_matrix(folder)
        avg_scores = _consensus_ratings_from_matrix(rd) if rd else {}
        def sort_key(img):
            return avg_scores.get(img, -1)
        def sort_reverse(): return True
    elif model == "ts":
        scores = get_cached_ts_scores(images, all_comp)
        def sort_key(img):
            s = scores.get(img)
            return s["rank_score"] if s else -1
        def sort_reverse(): return True
    else:
        scores = get_cached_bt_scores(images, all_comp)
        def sort_key(img):
            s = scores.get(img) if scores else None
            return s if s is not None else -1
        def sort_reverse(): return True

    # Group faces by category, ordered by ranking within each group
    groups = {}
    for cat_label in ["5", "4", "3", "2", "1"]:
        faces = [img for img, cat in cat_map.items() if cat == cat_label]
        faces.sort(key=sort_key, reverse=sort_reverse())
        groups[cat_label] = faces

    uncategorised = [img for img in images if img not in cat_map]
    uncategorised.sort(key=sort_key, reverse=sort_reverse())

    return jsonify({
        "groups": groups,
        "uncategorised": uncategorised,
        "label": label,
        "total": len(images),
        "categorised": len(cat_map),
    })


def _consensus_categories(all_cats, images):
    """For each image, pick the most common category across all raters."""
    from collections import Counter
    image_votes = {}
    for c in all_cats:
        img = c.get("image")
        if img not in image_votes:
            image_votes[img] = []
        image_votes[img].append(c["category"])
    result = []
    for img in images:
        if img in image_votes:
            most_common = Counter(image_votes[img]).most_common(1)[0][0]
            result.append({"image": img, "category": most_common})
    return result


# ── Manual Ranks ─────────────────────────────────────────────────────────────
#
# Stores a per-rater manually ordered list of image filenames.
# Structure: { "<rater_id>": { "ranks": ["img1.jpg", "img2.jpg", ...], "updated": "..." } }


@app.route("/api/manual-ranks", methods=["GET"])
@site_auth_required
def api_get_manual_ranks():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    folder     = request.args.get("folder") or _first_pairwise_folder()
    all_images = set(get_category_images(folder))
    key   = f"{session['rater_id']}:{folder}"
    data  = json.load(open(MANUAL_RANKS_FILE)) if MANUAL_RANKS_FILE.exists() else {}
    entry = data.get(key, {})
    saved = entry.get("ranks", [])
    basis = entry.get("basis", "ts")
    existing   = [img for img in saved if img in all_images]
    ranked_set = set(existing)
    unranked   = sorted(img for img in all_images if img not in ranked_set)
    return jsonify({
        "ranks":    existing,
        "unranked": unranked,
        "basis":    basis,
        "is_fresh": len(saved) == 0 and basis != "scratch",
        "updated":  entry.get("updated"),
    })


@app.route("/api/manual-ranks", methods=["POST"])
@site_auth_required
def api_set_manual_ranks():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    d      = request.json or {}
    ranks  = d.get("ranks", [])
    basis  = d.get("basis", "ts")
    folder = d.get("folder") or _first_pairwise_folder()
    if not isinstance(ranks, list):
        return jsonify({"error": "ranks must be a list"}), 400
    all_images = set(get_category_images(folder))
    ranks = [img for img in ranks if img in all_images]
    key   = f"{session['rater_id']}:{folder}"
    data  = json.load(open(MANUAL_RANKS_FILE)) if MANUAL_RANKS_FILE.exists() else {}
    data[key] = {
        "ranks":   ranks,
        "basis":   basis,
        "updated": datetime.utcnow().isoformat(),
    }
    with open(MANUAL_RANKS_FILE, "w") as fh:
        json.dump(data, fh, indent=2)
    return jsonify({"ok": True, "count": len(ranks)})


@app.route("/api/manual-ranks/all")
@site_auth_required
def api_get_all_manual_ranks():
    """All raters' manual rankings for a folder, plus a Borda-count consensus."""
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    folder     = request.args.get("folder") or _first_pairwise_folder()
    all_images = set(get_category_images(folder))
    raters_data = load_raters()
    raw  = json.load(open(MANUAL_RANKS_FILE)) if MANUAL_RANKS_FILE.exists() else {}

    entries = {}
    for key, entry in raw.items():
        if not key.endswith(f":{folder}"):
            continue
        rid   = key[: -(len(folder) + 1)]
        ranks = [img for img in entry.get("ranks", []) if img in all_images]
        if not ranks:
            continue
        entries[rid] = {
            "rater_id": rid,
            "name":     raters_data.get(rid, {}).get("name") or rid,
            "ranks":    ranks,
            "updated":  entry.get("updated"),
        }

    # Borda-count consensus: average rank position across all raters
    from collections import defaultdict
    pos_sum   = defaultdict(float)
    pos_count = defaultdict(int)
    for e in entries.values():
        for i, img in enumerate(e["ranks"]):
            pos_sum[img]   += i + 1
            pos_count[img] += 1

    consensus = sorted(
        [{"image": img, "avg_rank": round(pos_sum[img] / pos_count[img], 2),
          "n_raters": pos_count[img]} for img in pos_count],
        key=lambda x: x["avg_rank"]
    )

    return jsonify({
        "raters":       list(entries.values()),
        "consensus":    consensus,
        "total_raters": len(entries),
    })


@app.route("/api/my-comparisons")
@site_auth_required
def api_my_comparisons():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    folder = request.args.get("folder") or _first_pairwise_folder()
    comps = filter_comparisons(load_comparisons(folder), session["rater_id"])
    return jsonify({"comparisons": [{"winner": c["winner"], "loser": c["loser"]} for c in comps]})


# ── Rank Bands ────────────────────────────────────────────────────────────────
#
# Stores per-rater, per-model category boundary positions on the ranked list.
# Structure:  { "<rater_id>:<model>": { "s5_end": int, "s4_end": int, "s3_end": int, "s2_end": int } }
#   model is "bt", "ts", or "manual"
#   s5_end = last rank (1-based) that belongs to category 5 (Very Attractive)
#   s4_end = last rank that belongs to category 4 (Attractive)
#   s3_end = last rank that belongs to category 3 (Average)
#   s2_end = last rank that belongs to category 2 (Below Average)  — everything after = 1


def load_rank_bands():
    if RANK_BANDS_FILE.exists():
        with open(RANK_BANDS_FILE) as fh:
            return json.load(fh)
    return {}


def save_rank_bands(data):
    with open(RANK_BANDS_FILE, "w") as fh:
        json.dump(data, fh, indent=2)


@app.route("/api/rank-bands", methods=["GET"])
@site_auth_required
def api_get_rank_bands():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    model  = request.args.get("model", "bt")   # "bt" or "ts"
    key    = f"{session['rater_id']}:{model}"
    bands  = load_rank_bands()
    return jsonify(bands.get(key, {}))


@app.route("/api/rank-bands", methods=["POST"])
@site_auth_required
def api_set_rank_bands():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    d      = request.json or {}
    model  = d.get("model", "bt")
    s5_end = d.get("s5_end")
    s4_end = d.get("s4_end")
    s3_end = d.get("s3_end")
    s2_end = d.get("s2_end")
    # Basic validation — each boundary must be a positive integer, in ascending order
    try:
        s5_end = int(s5_end)
        s4_end = int(s4_end)
        s3_end = int(s3_end)
        s2_end = int(s2_end)
        assert 0 < s5_end <= s4_end <= s3_end <= s2_end
    except Exception:
        return jsonify({"error": "Invalid boundaries"}), 400
    key   = f"{session['rater_id']}:{model}"
    bands = load_rank_bands()
    bands[key] = {"s5_end": s5_end, "s4_end": s4_end, "s3_end": s3_end, "s2_end": s2_end,
                  "updated": datetime.utcnow().isoformat()}
    save_rank_bands(bands)
    return jsonify({"ok": True, "s5_end": s5_end, "s4_end": s4_end, "s3_end": s3_end, "s2_end": s2_end})


# ── Apply Rank Bands as Bucket Assignments ───────────────────────────────────

@app.route("/api/apply-rank-bands", methods=["POST"])
@site_auth_required
def api_apply_rank_bands():
    """Convert band boundaries for a model into 5/4/3/2/1 bucket assignments."""
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    d      = request.json or {}
    folder = d.get("folder") or _first_dataset()
    model  = d.get("model", "ts")

    # Load band boundaries for this rater + model
    key   = f"{session['rater_id']}:{model}"
    bands = load_rank_bands().get(key, {})
    s5_end = bands.get("s5_end", 0)
    s4_end = bands.get("s4_end", 0)
    s3_end = bands.get("s3_end", 0)
    s2_end = bands.get("s2_end", 0)
    if not (s5_end and s4_end and s3_end and s2_end):
        return jsonify({"error": "No band boundaries set. Set all four boundaries in the band controls first."}), 400

    # Compute this rater's rankings for the chosen model
    if model == "manual":
        mkey    = f"{session['rater_id']}:{folder}"
        mdata   = json.load(open(MANUAL_RANKS_FILE)) if MANUAL_RANKS_FILE.exists() else {}
        mentry  = mdata.get(mkey, {})
        msaved  = mentry.get("ranks", [])
        if not msaved:
            return jsonify({"error": "No manual ranking saved yet for this dataset — go to Rank Faces to create one."}), 400
        all_img = set(get_category_images(folder))
        ranked  = [{"image": img, "rank": i + 1} for i, img in enumerate(msaved) if img in all_img]
    else:
        images = get_images()
        comps  = filter_comparisons(load_comparisons(), session["rater_id"])
        if model == "ts":
            result, err = build_ts_rankings(images, comps)
        else:
            result, err = build_rankings(images, comps)
        if err or not result:
            return jsonify({"error": err or "Could not compute rankings — complete some comparisons first."}), 400
        ranked = result.get("ranked", [])
        if not ranked:
            return jsonify({"error": "No rankings available — complete some comparisons first."}), 400

    # Map each ranked image to a band
    folder_images = set(get_category_images(folder))
    new_entries   = []
    ts_now        = datetime.utcnow().isoformat()
    for row in ranked:
        img, rank = row["image"], row["rank"]
        if img not in folder_images:
            continue
        if   s5_end and rank <= s5_end: cat = "5"
        elif s4_end and rank <= s4_end: cat = "4"
        elif s3_end and rank <= s3_end: cat = "3"
        elif s2_end and rank <= s2_end: cat = "2"
        else:                           cat = "1"
        new_entries.append({
            "image":     img,
            "category":  cat,
            "rater_id":  session["rater_id"],
            "timestamp": ts_now,
            "source":    f"rank_bands:{model}",
        })

    if not new_entries:
        return jsonify({"error": f"None of the ranked images were found in \u2018{folder}\u2019."}), 400

    # Overwrite existing entries for this rater for those images
    assigned_imgs = {e["image"] for e in new_entries}
    protected = folder in PROTECTED_FOLDERS
    cats = load_guest_categories(folder) if protected else load_categories(folder)
    cats = [c for c in cats
            if not (c.get("rater_id") == session["rater_id"] and c.get("image") in assigned_imgs)]
    cats.extend(new_entries)
    if protected:
        save_guest_categories(cats, folder)
    else:
        save_categories(cats, folder)
    return jsonify({"ok": True, "assigned": len(new_entries)})


# ── Rater Analysis ────────────────────────────────────────────────────────────

def _img_ratings_dict(ratings_dict: dict) -> defaultdict:
    """Invert {rater: {img: val}} → {img: [val, ...]}."""
    img_vals: defaultdict = defaultdict(list)
    for img_map in ratings_dict.values():
        for img, cat in img_map.items():
            img_vals[img].append(cat)
    return img_vals


def _bucket_counts(vals: list) -> dict:
    return {str(k): sum(1 for v in vals if v == k) for k in [5, 4, 3, 2, 1]}


@lru_cache(maxsize=10)
def _build_rating_matrix(folder: str):
    """Load categories for a folder and return {rater_id: {image: int}}, image_list."""
    cats   = load_categories(folder)
    images = get_category_images(folder)
    ratings: dict = {}
    for c in cats:
        rid = c.get("rater_id")
        img = c.get("image")
        cat = c.get("category")
        if not (rid and img and cat):
            continue
        try:
            val = int(cat)
        except (ValueError, TypeError):
            continue
        if rid not in ratings:
            ratings[rid] = {}
        ratings[rid][img] = val
    return ratings, images


def _consensus_ratings_from_matrix(ratings_dict: dict) -> dict:
    """Return {image: mean_float} across all raters."""
    sums = _img_ratings_dict(ratings_dict)
    return {img: sum(v) / len(v) for img, v in sums.items()}


def _rater_stats_from_matrix(ratings_dict: dict, consensus: dict) -> list:
    """Per-rater statistics list, sorted by rater_id."""
    results = []
    for rid, img_map in sorted(ratings_dict.items()):
        vals = list(img_map.values())
        if not vals:
            continue
        n  = len(vals)
        mu = sum(vals) / n
        std = math.sqrt(sum((v - mu) ** 2 for v in vals) / n)
        counts = _bucket_counts(vals)

        if std < 0.8:
            shape = "Rates most faces highly" if mu > 3.5 else (
                "Rates most faces poorly" if mu < 2.5 else "Rates nearly everyone the same")
        elif std > 1.4:
            shape = "Loves or hates — rarely in between"
        else:
            shape = "Rates faces above average" if mu > 3.2 else (
                "Rates faces below average" if mu < 2.8 else "Spread across all ratings")

        my_v: list = []
        con_v: list = []
        agree = outlier = 0
        bias_sum = 0.0
        for img, my_cat in img_map.items():
            con = consensus.get(img)
            if con is None:
                continue
            my_v.append(my_cat)
            con_v.append(con)
            diff = my_cat - con
            if round(con) == my_cat:
                agree += 1
            if abs(diff) >= 2:
                outlier += 1
            bias_sum += diff

        compared = len(my_v)
        agree_pct   = round(agree   / compared * 100, 1) if compared else None
        outlier_pct = round(outlier / compared * 100, 1) if compared else None
        bias        = round(bias_sum / compared, 2)      if compared else None

        corr = None
        if compared >= 10:
            a = np.array(my_v,  dtype=float)
            b = np.array(con_v, dtype=float)
            if np.std(a) > 0.01 and np.std(b) > 0.01:
                corr = round(float(np.corrcoef(a, b)[0, 1]), 3)

        extremes_pct = round((counts.get("1", 0) + counts.get("5", 0)) / n * 100, 1) if n else None

        # Distribution curve label — based purely on bucket percentages
        bp            = {k: counts.get(str(k), 0) / n for k in [1, 2, 3, 4, 5]}
        high_frac     = bp[4] + bp[5]
        low_frac      = bp[1] + bp[2]
        extremes_frac = bp[1] + bp[5]
        peak          = max([1, 2, 3, 4, 5], key=lambda k: bp[k])

        if extremes_frac > 0.40 and bp[3] < 0.20:
            curve = "U-shaped"
        elif bp[3] > 0.40:
            curve = "Bell-shaped"
        elif high_frac > 0.45:
            curve = "Skews high"
        elif low_frac > 0.45:
            curve = "Skews low"
        elif peak in [4, 5]:
            curve = "Skews high"
        elif peak in [1, 2]:
            curve = "Skews low"
        else:
            curve = "Spread out"

        results.append({
            "rater_id":    rid,
            "n":           n,
            "counts":      counts,
            "mean":        round(mu,  2),
            "std":         round(std, 2),
            "shape":       shape,
            "curve":       curve,
            "extremes_pct": extremes_pct,
            "agree_pct":   agree_pct,
            "outlier_pct": outlier_pct,
            "bias":        bias,
            "corr":        corr,
        })
    return results


def _face_disagreement(ratings_dict: dict, images: list, top_n: int = 20) -> list:
    """Top-N most controversial faces by std dev of ratings."""
    img_vals = _img_ratings_dict(ratings_dict)
    stats = []
    for img in images:
        vals = img_vals.get(img, [])
        if len(vals) < 3:
            continue
        mu  = sum(vals) / len(vals)
        std = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals))
        stats.append({"image": img, "mean": round(mu, 2), "std": round(std, 2),
                      "n": len(vals), "counts": _bucket_counts(vals)})
    stats.sort(key=lambda x: -x["std"])
    return stats[:top_n]


def _inter_rater_heatmap(ratings_dict: dict, images: list):
    """Pairwise Pearson correlation matrix for all raters. Returns (rater_ids, matrix)."""
    rater_ids = sorted(ratings_dict.keys())
    n = len(rater_ids)
    if n == 0:
        return [], []

    img_list = list(images)
    img_idx  = {img: i for i, img in enumerate(img_list)}
    n_imgs   = len(img_list)

    X = np.full((n, n_imgs), np.nan)
    for i, rid in enumerate(rater_ids):
        for img, cat in ratings_dict[rid].items():
            j = img_idx.get(img)
            if j is not None:
                X[i, j] = float(cat)

    row_means = np.nanmean(X, axis=1, keepdims=True)
    row_stds  = np.nanstd(X,  axis=1, keepdims=True)
    row_stds[row_stds < 0.01] = 1.0
    X_norm = np.nan_to_num((X - row_means) / row_stds, nan=0.0)

    corr   = np.clip(X_norm @ X_norm.T / n_imgs, -1.0, 1.0)
    matrix = [[round(float(corr[i, j]), 3) for j in range(n)] for i in range(n)]
    return rater_ids, matrix


def _rater_clusters(ratings_dict: dict, images: list, n_clusters: int = 5):
    """K-means clustering of raters by rating vector. Returns (assignments, summaries)."""
    rater_ids = sorted(ratings_dict.keys())
    n_raters  = len(rater_ids)
    if n_raters < n_clusters:
        return {rid: i % n_clusters for i, rid in enumerate(rater_ids)}, []

    img_list = list(images)
    img_idx  = {img: i for i, img in enumerate(img_list)}
    n_imgs   = len(img_list)

    X = np.full((n_raters, n_imgs), 3.0)
    for i, rid in enumerate(rater_ids):
        for img, cat in ratings_dict[rid].items():
            j = img_idx.get(img)
            if j is not None:
                X[i, j] = float(cat)

    means = X.mean(axis=1, keepdims=True)
    stds  = X.std( axis=1, keepdims=True)
    stds[stds < 0.01] = 1.0
    X_norm = (X - means) / stds

    # K-means++ init
    np.random.seed(42)
    ci = [0]
    for _ in range(n_clusters - 1):
        dists = np.min(np.sum((X_norm[:, None, :] - X_norm[ci][None, :, :]) ** 2, axis=2), axis=1)
        probs = dists / dists.sum()
        ci.append(int(np.random.choice(n_raters, p=probs)))
    centroids = X_norm[ci].copy()

    labels = np.zeros(n_raters, dtype=int)
    for _ in range(100):
        dists      = np.linalg.norm(X_norm[:, None, :] - centroids[None, :, :], axis=2) ** 2
        new_labels = np.argmin(dists, axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for k in range(n_clusters):
            m = X_norm[labels == k]
            if len(m):
                centroids[k] = m.mean(axis=0)

    raters_data = load_raters()
    cluster_labels = ["A", "B", "C", "D", "E"]
    summaries = []
    for k in range(n_clusters):
        members = [rater_ids[i] for i in range(n_raters) if labels[i] == k]
        if not members:
            continue
        all_vals = [cat for rid in members for cat in ratings_dict[rid].values()]
        mu  = sum(all_vals) / len(all_vals) if all_vals else 0
        std = math.sqrt(sum((v - mu) ** 2 for v in all_vals) / len(all_vals)) if all_vals else 0
        summaries.append({
            "cluster_id": k,
            "label":      cluster_labels[k] if k < len(cluster_labels) else str(k),
            "members":    members,
            "names":      [raters_data.get(rid, {}).get("name", rid) for rid in members],
            "size":       len(members),
            "mean":       round(mu,  2),
            "std":        round(std, 2),
        })

    assignments = {rid: int(labels[i]) for i, rid in enumerate(rater_ids)}
    return assignments, summaries


def _consensus_distribution(ratings_dict: dict) -> dict:
    """Distribution of images by their consensus bucket (mean rounded to nearest int)."""
    img_vals = _img_ratings_dict(ratings_dict)
    dist = {str(k): 0 for k in [5, 4, 3, 2, 1]}
    for vals in img_vals.values():
        bucket = str(min(5, max(1, round(sum(vals) / len(vals)))))
        dist[bucket] += 1
    total = sum(dist.values())
    return {
        "counts": dist,
        "total":  total,
        "pcts":   {k: round(v / total * 100, 1) if total else 0 for k, v in dist.items()},
    }


@app.route("/api/rater-analysis")
@site_auth_required
def api_rater_analysis():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    folder = request.args.get("folder") or _first_pairwise_folder()
    ratings_dict, images = _build_rating_matrix(folder)
    if not ratings_dict:
        return jsonify({"error": "No ratings data found for this folder."}), 400
    consensus   = _consensus_ratings_from_matrix(ratings_dict)
    stats       = _rater_stats_from_matrix(ratings_dict, consensus)
    raters_data = load_raters()
    for s in stats:
        s["name"] = raters_data.get(s["rater_id"], {}).get("name", s["rater_id"])
    cons_dist = _consensus_distribution(ratings_dict)
    return jsonify({"stats": stats, "folder": folder, "consensus_dist": cons_dist})


@app.route("/api/heatmap")
@site_auth_required
def api_heatmap():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    folder = request.args.get("folder") or _first_pairwise_folder()
    ratings_dict, images = _build_rating_matrix(folder)
    if not ratings_dict:
        return jsonify({"error": "No ratings data found for this folder."}), 400
    rater_ids, matrix = _inter_rater_heatmap(ratings_dict, images)
    raters_data = load_raters()
    names = [raters_data.get(rid, {}).get("name", rid) for rid in rater_ids]
    return jsonify({"rater_ids": rater_ids, "names": names, "matrix": matrix})


@app.route("/api/face-disagreement")
@site_auth_required
def api_face_disagreement():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    folder  = request.args.get("folder") or _first_pairwise_folder()
    top_n   = int(request.args.get("top_n", 20))
    agreed_n = int(request.args.get("agreed_n", 20))
    ratings_dict, images = _build_rating_matrix(folder)
    if not ratings_dict:
        return jsonify({"error": "No ratings data found for this folder."}), 400
    all_faces = _face_disagreement(ratings_dict, images, top_n=len(images))
    contested = all_faces[:top_n]
    agreed    = list(reversed(all_faces[-agreed_n:])) if len(all_faces) >= agreed_n else list(reversed(all_faces))
    return jsonify({"faces": contested, "agreed": agreed, "folder": folder})


@app.route("/api/rater-clusters")
@site_auth_required
def api_rater_clusters():
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401
    folder         = request.args.get("folder") or _first_pairwise_folder()
    k              = max(2, min(10, int(request.args.get("k", 5))))
    exclude_rater  = request.args.get("exclude_rater")
    ratings_dict, images = _build_rating_matrix(folder)
    if exclude_rater:
        ratings_dict.pop(exclude_rater, None)
    if not ratings_dict:
        return jsonify({"error": "No ratings data found for this folder."}), 400
    assignments, summaries = _rater_clusters(ratings_dict, images, n_clusters=k)
    return jsonify({"assignments": assignments, "summaries": summaries, "folder": folder})


# ── Pairwise inter-rater analysis ─────────────────────────────────────────────

@app.route("/api/pw-rater-analysis")
@site_auth_required
def api_pw_rater_analysis():
    """Per-rater BT rankings, rank correlation matrix, contrarian scores, face spread."""
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401

    folder    = request.args.get("folder") or _first_pairwise_folder()
    all_comp  = load_comparisons(folder)
    images    = get_images(folder)
    raters_db = load_raters()

    if not all_comp:
        return jsonify({"error": "No comparison data found for this folder."}), 400
    if not images:
        return jsonify({"error": "No images found for this folder."}), 400

    MIN_COMPS = 400
    from collections import defaultdict
    by_rater = defaultdict(list)
    for c in all_comp:
        rid = c.get("rater_id")
        if rid:
            by_rater[rid].append(c)

    active = {rid: comps for rid, comps in by_rater.items() if len(comps) >= MIN_COMPS}
    if len(active) < 2:
        return jsonify({"error": f"Need at least 2 raters with {MIN_COMPS}+ comparisons. "
                                  f"Currently {len(active)} qualify."}), 400

    rater_scores = {rid: fit_bradley_terry(images, comps) for rid, comps in active.items()}
    cons_scores  = fit_bradley_terry(images, all_comp)

    def to_ranks(scores):
        seen = sorted(((img, s) for img, s in scores.items() if s is not None), key=lambda x: -x[1])
        return {img: rank + 1 for rank, (img, _) in enumerate(seen)}

    rater_ranks = {rid: to_ranks(s) for rid, s in rater_scores.items()}
    cons_ranks  = to_ranks(cons_scores)

    rater_ids = sorted(active.keys())
    names     = [raters_db.get(rid, {}).get("name", rid) for rid in rater_ids]
    n         = len(rater_ids)

    # Common faces seen by every active rater, sorted by consensus rank
    common = set(cons_ranks.keys())
    for rr in rater_ranks.values():
        common &= set(rr.keys())
    common  = sorted(common, key=lambda f: cons_ranks[f])
    n_faces = len(common)

    if n_faces < 3:
        return jsonify({"error": "Too few faces in common across all qualifying raters."}), 400

    # Optional face filter — restricts which faces feed the Spearman / contrarian / spread calc
    face_filter = request.args.get("filter", "all")
    if face_filter == "top20":
        analysis_faces = common[:20]
    elif face_filter == "top30":
        analysis_faces = common[:30]
    elif face_filter == "bottom20":
        analysis_faces = common[-20:]
    else:
        face_filter    = "all"
        analysis_faces = common

    n_filtered = len(analysis_faces)   # count after face_filter, before exclusion

    # Optional exclusion of the most contested faces within the filtered set.
    # If exclude_rater is set, rank by that rater's deviation from consensus;
    # otherwise rank by global rank_std across all raters.
    exclude_contested = max(0, int(request.args.get("exclude_contested", 0)))
    exclude_rater     = request.args.get("exclude_rater", "")
    excluded_faces    = []
    if exclude_contested > 0 and n_filtered > exclude_contested + 2:
        if exclude_rater and exclude_rater in rater_ranks:
            key = lambda f: -abs(rater_ranks[exclude_rater].get(f, 0) - cons_ranks.get(f, 0))
        else:
            face_stds = {}
            for f in analysis_faces:
                rv = [rater_ranks[rid][f] for rid in rater_ids if f in rater_ranks[rid]]
                face_stds[f] = float(np.std(rv)) if len(rv) > 1 else 0.0
            key = lambda f: -face_stds[f]
        excluded_faces = sorted(analysis_faces, key=key)[:exclude_contested]
        excluded_set   = set(excluded_faces)
        analysis_faces = [f for f in analysis_faces if f not in excluded_set]

    n_analysis = len(analysis_faces)

    if n_analysis < 3:
        return jsonify({"error": "Too few faces for this filter."}), 400

    # Re-rank within analysis_faces so ranks run 1..n_analysis.
    # Using full-set ranks in the Spearman formula when n_analysis < n_faces
    # produces values wildly outside [-1, 1].
    def sub_rank(rid):
        ordered = sorted(analysis_faces, key=lambda f: -(rater_scores[rid].get(f) or 0))
        return {f: rank + 1 for rank, f in enumerate(ordered)}

    sub_rater_ranks = {rid: sub_rank(rid) for rid in rater_ids}
    sub_cons_ranks  = {f: rank + 1 for rank, f in enumerate(
        sorted(analysis_faces, key=lambda f: -(cons_scores.get(f) or 0))
    )}

    def spearman(sr_a, sr_b):
        a  = np.array([sr_a[f] for f in analysis_faces], dtype=float)
        b  = np.array([sr_b[f] for f in analysis_faces], dtype=float)
        d2 = float(np.sum((a - b) ** 2))
        return round(1.0 - 6.0 * d2 / (n_analysis * (n_analysis ** 2 - 1)), 3)

    matrix = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            rho = spearman(sub_rater_ranks[rater_ids[i]], sub_rater_ranks[rater_ids[j]])
            matrix[i][j] = matrix[j][i] = rho

    pairs = sorted([
        {"rater_a": rater_ids[i], "name_a": names[i],
         "rater_b": rater_ids[j], "name_b": names[j],
         "rho": matrix[i][j]}
        for i in range(n) for j in range(i + 1, n)
    ], key=lambda x: -x["rho"])

    contrarian = sorted([
        {"rater_id": rid,
         "name":     raters_db.get(rid, {}).get("name", rid),
         "score":    round(float(np.mean([abs(sub_rater_ranks[rid][f] - sub_cons_ranks[f]) for f in analysis_faces])), 2),
         "n_comps":  len(active[rid])}
        for rid in rater_ids
    ], key=lambda x: -x["score"])

    face_spread = []
    for f in analysis_faces:
        rv = [sub_rater_ranks[rid][f] for rid in rater_ids]
        face_spread.append({
            "image":           f,
            "consensus_rank":  sub_cons_ranks[f],
            "consensus_score": round(float(cons_scores.get(f) or 0), 2),
            "rank_std":        round(float(np.std(rv)), 2),
            "rank_min":        int(min(rv)),
            "rank_max":        int(max(rv)),
            "per_rater":       {rid: sub_rater_ranks[rid][f] for rid in rater_ids},
        })
    face_spread.sort(key=lambda x: -x["rank_std"])

    rater_detail = []
    for i, rid in enumerate(rater_ids):
        pts = [{
            "image":       f,
            "cons_score":  round(float(cons_scores.get(f) or 0), 2),
            "rater_score": round(float(rater_scores[rid].get(f) or 0), 2),
            "cons_rank":   cons_ranks[f],
            "rater_rank":  rater_ranks[rid][f],
            "rank_diff":   rater_ranks[rid][f] - cons_ranks[f],
        } for f in analysis_faces]
        pts.sort(key=lambda x: -abs(x["rank_diff"]))
        cr = [p["cons_rank"] for p in pts]
        rr = [p["rater_rank"] for p in pts]
        rho_vs_cons = round(float(np.corrcoef(cr, rr)[0, 1]), 3) if len(pts) > 1 else 0.0
        rater_detail.append({
            "rater_id":    rid,
            "name":        names[i],
            "n_comps":     len(active[rid]),
            "rho_vs_cons": rho_vs_cons,
            "points":      pts,
        })

    avg_rho = round(float(np.mean([p["rho"] for p in pairs])), 3) if pairs else 0.0

    # Classical MDS: project raters into 2D taste-space from the Spearman distance matrix
    dist    = np.maximum(1.0 - np.array(matrix), 0.0)
    dist_sq = dist ** 2
    H       = np.eye(n) - np.ones((n, n)) / n
    B       = -0.5 * H @ dist_sq @ H
    evals, evecs = np.linalg.eigh(B)
    idx     = np.argsort(evals)[::-1]
    scale   = np.sqrt(np.maximum(evals[idx[:2]], 0.0))
    coords  = evecs[:, idx[:2]] * scale
    mds_coords = [[round(float(coords[i, 0]), 4), round(float(coords[i, 1]), 4)] for i in range(n)]

    return jsonify({
        "folder":             folder,
        "face_filter":        face_filter,
        "exclude_contested":  exclude_contested,
        "exclude_rater":      exclude_rater,
        "excluded_faces":     excluded_faces,
        "rater_ids":          rater_ids,
        "names":              names,
        "n_faces":            n_faces,
        "n_filtered":         n_filtered,
        "n_analysis":         n_analysis,
        "n_raters":           n,
        "avg_rho":            avg_rho,
        "matrix":             matrix,
        "mds_coords":         mds_coords,
        "pairs":              pairs,
        "contrarian":         contrarian,
        "face_spread":        face_spread,
        "rater_detail":       rater_detail,
    })


# ── Cross-dataset comparison ──────────────────────────────────────────────────

@app.route("/api/cross-dataset")
@site_auth_required
def api_cross_dataset():
    """Per-rater stats for two datasets side by side."""
    if "rater_id" not in session:
        return jsonify({"error": "not_registered"}), 401

    folders = request.args.getlist("folder") or list_datasets()[:2]
    if len(folders) < 2:
        return jsonify({"error": "Need at least two folders."}), 400

    raters_data = load_raters()

    # Build per-folder stats keyed by rater_id
    folder_stats: dict = {}
    for folder in folders:
        rd, imgs = _build_rating_matrix(folder)
        if not rd:
            folder_stats[folder] = {}
            continue
        con = _consensus_ratings_from_matrix(rd)
        per_rater = _rater_stats_from_matrix(rd, con)
        folder_stats[folder] = {s["rater_id"]: s for s in per_rater}

    # Collect all rater_ids present in any folder
    all_rids = sorted({rid for fs in folder_stats.values() for rid in fs})

    rows = []
    for rid in all_rids:
        entry: dict = {
            "rater_id": rid,
            "name": raters_data.get(rid, {}).get("name", rid),
        }
        means = []
        for folder in folders:
            s = folder_stats[folder].get(rid)
            entry[folder] = {
                "mean":    s["mean"]    if s else None,
                "std":     s["std"]     if s else None,
                "shape":   s["shape"]   if s else None,
                "counts":  s["counts"]  if s else None,
                "n":       s["n"]       if s else 0,
            }
            if s:
                means.append(s["mean"])

        # Difference: folder[0] mean minus folder[1] mean
        if len(means) == 2:
            entry["diff"] = round(means[0] - means[1], 2)
        else:
            entry["diff"] = None

        rows.append(entry)

    rows.sort(key=lambda x: (x["diff"] is None, x["diff"] or 0), reverse=True)
    return jsonify({"rows": rows, "folders": folders})


# ── Admin panel ───────────────────────────────────────────────────────────────

def admin_auth_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_authed"):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.route("/admin")
@site_auth_required
def admin_index():
    return render_template("admin.html", admin_authed=session.get("admin_authed", False))


@app.route("/api/admin/auth", methods=["POST"])
@site_auth_required
def api_admin_auth():
    pwd = (request.json or {}).get("password", "")
    if pwd == ADMIN_PASSWORD:
        session["admin_authed"] = True
        return jsonify({"ok": True})
    return jsonify({"error": "Incorrect password"}), 401


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.pop("admin_authed", None)
    return jsonify({"ok": True})


@app.route("/api/admin/config", methods=["GET"])
@site_auth_required
@admin_auth_required
def api_admin_get_config():
    _load_config()
    all_folders = list_datasets()
    return jsonify({
        "site_password":             SITE_PASSWORD,
        "site_login_required":       SITE_LOGIN_REQUIRED,
        "admin_password":            ADMIN_PASSWORD,
        "pairwise_folder":           PAIRWISE_FOLDER or "",
        "pairwise_folder_selector":  PAIRWISE_FOLDER_SELECTOR,
        "show_intro":                SHOW_INTRO,
        "show_pairwise":             SHOW_SECTION_PAIRWISE,
        "show_stack":                SHOW_SECTION_STACK,
        "show_category":             SHOW_SECTION_CATEGORY,
        "pair_selection_model":      PAIR_SELECTION_MODEL,
        "target_per_image":          TARGET_PER_IMAGE,
        "min_comparisons_consensus": MIN_COMPARISONS_FOR_CONSENSUS,
        "protected_folders":         PROTECTED_FOLDERS,
        "ui_font_size":              UI_FONT_SIZE,
        "all_folders":               all_folders,
    })


@app.route("/api/admin/config", methods=["POST"])
@site_auth_required
@admin_auth_required
def api_admin_set_config():
    global SITE_PASSWORD, SITE_LOGIN_REQUIRED, ADMIN_PASSWORD, PAIRWISE_FOLDER, PAIRWISE_FOLDER_SELECTOR
    global SHOW_INTRO, SHOW_SECTION_PAIRWISE, SHOW_SECTION_STACK, SHOW_SECTION_CATEGORY
    global PAIR_SELECTION_MODEL, TARGET_PER_IMAGE, MIN_COMPARISONS_FOR_CONSENSUS, PROTECTED_FOLDERS
    global UI_FONT_SIZE
    d = request.json or {}
    if "site_password"             in d: SITE_PASSWORD              = d["site_password"] or SITE_PASSWORD
    if "site_login_required"       in d: SITE_LOGIN_REQUIRED         = bool(d["site_login_required"])
    if "admin_password"            in d: ADMIN_PASSWORD             = d["admin_password"] or ADMIN_PASSWORD
    if "pairwise_folder"           in d: PAIRWISE_FOLDER            = d["pairwise_folder"] or None
    if "pairwise_folder_selector"  in d: PAIRWISE_FOLDER_SELECTOR   = bool(d["pairwise_folder_selector"])
    if "show_intro"                in d: SHOW_INTRO                 = bool(d["show_intro"])
    if "show_pairwise"             in d: SHOW_SECTION_PAIRWISE      = bool(d["show_pairwise"])
    if "show_stack"                in d: SHOW_SECTION_STACK         = bool(d["show_stack"])
    if "show_category"             in d: SHOW_SECTION_CATEGORY      = bool(d["show_category"])
    if "pair_selection_model"      in d and d["pair_selection_model"] in ("BT", "TrueSkill"):
        PAIR_SELECTION_MODEL = d["pair_selection_model"]
    if "target_per_image"          in d: TARGET_PER_IMAGE           = max(1, int(d["target_per_image"]))
    if "min_comparisons_consensus" in d: MIN_COMPARISONS_FOR_CONSENSUS = max(1, int(d["min_comparisons_consensus"]))
    if "protected_folders"         in d: PROTECTED_FOLDERS          = list(d["protected_folders"])
    if "ui_font_size"              in d: UI_FONT_SIZE               = max(70, min(150, int(d["ui_font_size"])))
    _save_config()
    return jsonify({"ok": True})


# ── Reset ─────────────────────────────────────────────────────────────────────

@app.route("/api/reset", methods=["POST"])
def api_reset():
    scope = (request.json or {}).get("scope", "all")
    if scope == "mine" and "rater_id" in session:
        kept = [c for c in load_comparisons()
                if c.get("rater_id") != session["rater_id"]]
        save_comparisons(kept)
    elif scope == "all":
        for f in [DATA_FILE, RATERS_FILE]:
            if f.exists():
                f.unlink()
        session.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    print(f"\n  Attractiveness Ranker  (with rater profiles + coverage tracking)")
    print(f"  → Open: http://localhost:5000\n")
    app.run(debug=True, port=5000)
