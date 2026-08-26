"""Full pipeline: build candidates → photo review → HTML output.

Run: python analytics/scripts/run_pipeline_2026_05_27.py
  or: ANTHROPIC_API_KEY=sk-... python analytics/scripts/run_pipeline_2026_05_27.py
  or: python analytics/scripts/run_pipeline_2026_05_27.py --api-key sk-...
  or: python analytics/scripts/run_pipeline_2026_05_27.py --run-dir <existing dir>  (re-run from step 2)

A .env file in the project root with ANTHROPIC_API_KEY=... is also read automatically.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import time
from datetime import datetime
from pathlib import Path

import anthropic
import pandas as pd

from bazaraki.utils import to_legacy_format

# Load .env file if present (simple parser, no dotenv dependency required)
_env_path = Path("/Users/alekseygrachev/git/bazaraki/.env")
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            if _k.strip() not in os.environ:
                os.environ[_k.strip()] = _v.strip().strip('"').strip("'")

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
PARQUET = (
    "/Users/alekseygrachev/git/bazaraki/output/"
    "2026-05-27 01:10:46 real-estate-to-rent_real-estate-for-sale.parquet"
)
ORIGIN = (34.6854, 33.0557)  # Alber Blanc office
SNAPSHOT_LABEL = "2026-05-27 01:10"

# ─────────────────────────────────────────────────────────────────────────────
# District centroids (same as build_candidates.py)
# ─────────────────────────────────────────────────────────────────────────────
DISTRICT_COORDS: dict[str, tuple[float, float]] = {
    "Limassol - Mesa Geitonia": (34.703, 33.063),
    "Limassol - Zakaki": (34.701, 33.030),
    "Kato Polemidia": (34.701, 33.050),
    "Limassol - Neapolis": (34.694, 33.030),
    "Germasogeia Tourist Area": (34.713, 33.115),
    "Agios Tychon Tourist Area": (34.703, 33.160),
    "Agios Athanasios": (34.705, 33.075),
    "Germasogeia": (34.722, 33.110),
    "Limassol - Katholiki": (34.679, 33.044),
    "Historical Center": (34.674, 33.044),
    "Ypsonas": (34.708, 32.965),
    "Limassol - Kapsalos": (34.696, 33.043),
    "Limassol - Agia Zoni": (34.687, 33.043),
    "Potamos Germasogeias": (34.711, 33.107),
    "Limassol - Agios Nicolaos": (34.682, 33.040),
    "Agios Tychon": (34.710, 33.135),
    "Limassol - Apostolos Andreas": (34.703, 33.025),
    "Limassol - Petrou Kai Pavlou": (34.703, 33.040),
    "Limassol - Agia Fyla": (34.720, 33.045),
    "Limassol - Agios Ioannis": (34.700, 33.040),
    "Limassol - Omonia": (34.677, 33.041),
    "Trachoni Lemesou": (34.682, 33.000),
    "Parekklisia": (34.708, 33.166),
    "Limassol - Agios Spyridon": (34.677, 33.044),
    "Limassol - Agia Triada": (34.678, 33.038),
    "Mouttagiaka Tourist Area": (34.708, 33.155),
    "Erimi": (34.694, 32.917),
    "Pyrgos Lemesou": (34.715, 33.195),
    "Limassol - Tsirion": (34.682, 33.027),
    "Panthea": (34.688, 33.026),
    "Pissouri": (34.665, 32.700),
    "Agios Ioannis Lemesou": (34.700, 33.040),
    "Ekali": (34.689, 33.024),
    "Chalkoutsa": (34.682, 33.034),
    "Limassol - Agios Antonios": (34.677, 33.040),
    "Kolossi -Agios Loukas": (34.660, 32.940),
    "Asomatos Lemesou": (34.660, 32.985),
    "Limassol": (34.684, 33.040),
    "Limassol - Agia Napa": (34.679, 33.046),
    "Limassol - Tsiflikoudia": (34.690, 33.057),
    "Polemidia - Apostolos Varnavas": (34.708, 33.052),
    "Kontovathkeia": (34.715, 33.040),
    "Pyrgos Lemesou Tourist Area": (34.708, 33.180),
    "Limassol - Agios Nektarios": (34.684, 33.041),
    "Fasoula Lemesou": (34.755, 33.025),
    "Pano Platres": (34.890, 32.880),
    "Limassol - Linopetra": (34.692, 33.013),
    "Mouttagiaka": (34.722, 33.150),
    "Kato Platres": (34.880, 32.880),
    "Polemidia - Makarios III": (34.708, 33.052),
    "Dora": (34.835, 32.770),
    "Trimiklini": (34.840, 32.910),
    "Tserkez Tsiftlik (Tserkezoi)": (34.680, 32.965),
    "Episkopi Lemesou": (34.670, 32.890),
    "Timiou Prodromou  Mesa Geitonias": (34.703, 33.063),
    "Limassol - Panag. Evangelistria": (34.685, 33.040),
    "Limassol - Agios Georgios": (34.690, 33.050),
    "Agios Georgios Lemesou": (34.690, 33.050),
    "Anogyra": (34.730, 32.800),
    "Palodeia": (34.755, 33.000),
    "Parekklisia Tourist Area": (34.715, 33.180),
    "Fasouri": (34.660, 32.985),
}

BUSY_ROAD_KEYWORDS = [
    "makarios", "makariou", "griva digeni", "griva dhigeni", "gryva digeni",
    "spyrou kyprianou", "spirou kiprianou", "franklin roosevelt",
    "archiepiskopou leontiou", "leontiou", "omonias avenue", "omonia avenue",
    "28th october avenue", "28 october", "amathountos", "armenias",
    "vasileos konstantinou", "vasileos georgiou",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def haversine(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    R = 6371.0
    lat1, lng1 = map(math.radians, p1)
    lat2, lng2 = map(math.radians, p2)
    dlat, dlng = lat2 - lat1, lng2 - lng1
    a = (math.sin(dlat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def parse_district(loc: str) -> str:
    parts = [p.strip() for p in loc.split(",")]
    return parts[1] if len(parts) >= 2 else parts[0]


def dist_to_origin(district: str) -> float:
    coords = DISTRICT_COORDS.get(district)
    return haversine(ORIGIN, coords) if coords else math.nan


def is_old_building(row: pd.Series) -> bool:
    """Return True if the building should be excluded as too old."""
    cy = row["Construction year"]
    if pd.isna(cy) or cy is None:
        return False
    desc = str(row["description"]).lower() if row["description"] else ""
    if cy == "Older":
        # Keep if description mentions renovation
        if any(kw in desc for kw in ["renovat", "refurb", "fully refurb"]):
            return False
        return True
    try:
        year = int(cy)
        if year < 2000:
            return True
    except (ValueError, TypeError):
        pass
    return False


def extract_signals(desc: str) -> dict:
    if not isinstance(desc, str):
        desc = ""
    d = desc.lower()

    def has(*terms: str) -> bool:
        return any(t in d for t in terms)

    utilities_included: list[str] = []
    if has("bills included", "all bills included", "all inclusive", "all-inclusive"):
        utilities_included.append("all_bills")
    if has("electricity included", "electric included", "electricity is included"):
        utilities_included.append("electricity")
    if has("water included", "water bill included", "water is included"):
        utilities_included.append("water")
    if has("internet included", "wifi included", "wi-fi included", "internet is included"):
        utilities_included.append("internet")
    if has("common expenses included", "communal expenses included", "common fees included",
           "common charges included", "service charge included", "common expenses are included"):
        utilities_included.append("common_expenses")

    deposit_months: int | None = None
    m = re.search(r"(\d)\s*(?:months?|month's)\s*(?:deposit|rent\s*deposit|security)", d)
    if m:
        deposit_months = int(m.group(1))
    if not deposit_months and ("two months deposit" in d or "two-month deposit" in d
                               or "2-month deposit" in d):
        deposit_months = 2

    has_pool = has("swimming pool", "communal pool", "private pool", " pool ", " pool.")
    has_seaview = has("sea view", "sea views", "panoramic sea", "ocean view")
    has_mountainview = has("mountain view", "mountain views")
    has_greenview = has("garden view", "park view", "green view")
    has_desk = has("desk", "office space", "study", "work from home", "home office", "workspace")
    has_quiet = has("quiet area", "quiet neighbour", "quiet neighbor", "no traffic",
                    "quiet street", "calm area")
    has_new_building = has("new building", "brand new", "newly built", "newly constructed",
                           "recently built", "2023", "2024", "2025", "newly renovated",
                           "fully renovated", "modern building")
    busy_road = any(kw in d for kw in BUSY_ROAD_KEYWORDS)

    return {
        "utilities_included": utilities_included,
        "deposit_months": deposit_months,
        "has_pool": has_pool,
        "has_seaview": has_seaview,
        "has_mountainview": has_mountainview,
        "has_greenview": has_greenview,
        "has_desk": has_desk,
        "has_quiet": has_quiet,
        "has_new_building": has_new_building,
        "busy_road": busy_road,
    }


def pre_score(row: pd.Series) -> float:
    s = 6.0
    price = row["price"]
    if price <= 1500:
        s += 1.0
    elif price <= 1650:
        s += 0.5
    elif price > 1700:
        s -= 0.3

    dist = row["dist_km"]
    if pd.notna(dist):
        if dist <= 3:
            s += 0.8
        elif dist <= 6:
            s += 0.4
        elif dist <= 10:
            s += 0.1
        elif dist <= 15:
            s -= 0.3
        else:
            s -= 1.0

    if row["has_seaview"]:
        s += 0.8
    if row["has_mountainview"]:
        s += 0.4
    if row["has_greenview"]:
        s += 0.3
    if row["has_pool"]:
        s += 0.8
    if row["has_desk"]:
        s += 0.4
    if row["has_quiet"]:
        s += 0.4
    if row["has_new_building"]:
        s += 0.6
    if row["busy_road"]:
        s -= 1.5
    if row["deposit_months"] and row["deposit_months"] >= 2:
        s -= 1.0
    if row["utilities_included"]:
        s += 0.4

    return s


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Build candidates
# ─────────────────────────────────────────────────────────────────────────────
def build_candidates(out_dir: Path) -> list[dict]:
    print("\n=== STEP 1: Building candidates ===")
    df = to_legacy_format(pd.read_parquet(PARQUET))
    df["city"] = df.location.fillna("").str.split(",").str[0].str.strip()

    f = df[
        (df.cat1 == "Apartments, flats to rent")
        & (df.city == "Limassol")
        & (df.price <= 1750)
        & (df.Bedrooms.isin(["Studio", "1", "2"]))
        & (~df.sold)
    ].copy()

    # Exclude old buildings (pre-2000 and "Older" without renovation mention)
    old_mask = f.apply(is_old_building, axis=1)
    f = f[~old_mask].copy()
    print(f"After old-building filter: {len(f)}")

    # Exclude Unfurnished and Appliances only (has Greek omicron in 'οnly')
    furn = f["Furnishing"].fillna("")
    f = f[~furn.isin(["Unfurnished"]) & ~furn.str.contains("Appliances", na=False)].copy()
    print(f"After furnishing filter: {len(f)}")

    f["district"] = f["location"].apply(parse_district)
    f["dist_km"] = f["district"].apply(dist_to_origin)

    signals = f["description"].apply(extract_signals).apply(pd.Series)
    f = pd.concat([f.reset_index(drop=True), signals.reset_index(drop=True)], axis=1)

    f["prescore"] = f.apply(pre_score, axis=1)
    f = f.sort_values("prescore", ascending=False).reset_index(drop=True)

    keep_cols = [
        "ad_id", "url", "title", "price", "Bedrooms", "Bathrooms",
        "location", "district", "dist_km", "Property area", "Floor", "Furnishing",
        "Construction year", "Condition", "Included", "Parking", "Air conditioning",
        "Pets", "images", "description",
        "utilities_included", "deposit_months", "has_pool", "has_seaview",
        "has_mountainview", "has_greenview", "has_desk", "has_quiet",
        "has_new_building", "busy_road", "prescore",
    ]
    # Only keep columns that exist
    keep_cols = [c for c in keep_cols if c in f.columns]
    out_full = f[keep_cols].copy()

    # Coerce image list for JSON serialization
    out_full["images"] = out_full["images"].apply(
        lambda x: list(x) if hasattr(x, "tolist") else (x if isinstance(x, list) else [])
    )

    out_full.to_json(
        out_dir / "candidates_all.json",
        orient="records", force_ascii=False, indent=2,
    )
    print(f"Saved candidates_all.json ({len(out_full)} records)")

    top100 = out_full.head(100).copy()
    top100.to_json(
        out_dir / "candidates_top100.json",
        orient="records", force_ascii=False, indent=2,
    )
    print(f"Saved candidates_top100.json ({len(top100)} records)")
    print(f"Pre-score range (all): {out_full.prescore.min():.2f} … {out_full.prescore.max():.2f}")
    print(f"Pre-score range (top100): {top100.prescore.min():.2f} … {top100.prescore.max():.2f}")

    candidates = json.loads(top100.to_json(orient="records", force_ascii=False))
    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Photo + description review via Claude API
# ─────────────────────────────────────────────────────────────────────────────
REVIEW_SYSTEM = """You are an expert apartment reviewer. Analyze the provided apartment photos and description.
Return ONLY a valid JSON object (no markdown, no explanation) with these exact fields:
- furniture_style: one of "modern_stylish", "modern_neutral", "ikea_basic", "dated", "old_dingy"
- building_age: one of "new", "renovated", "modern_2010s", "older_but_ok", "old_dated"
- condition: one of "pristine", "good", "worn", "shabby"
- light_quality: one of "bright", "ok", "dark"
- has_desk: boolean
- has_pool_visible: boolean
- has_seaview_visible: boolean
- has_mountainview_visible: boolean
- has_greenview_visible: boolean
- has_balcony: boolean
- red_flags: list of short strings (max 5), e.g. ["dark rooms", "old appliances"]
- green_flags: list of short strings (max 5), e.g. ["modern kitchen", "large windows"]
- summary: 1-2 sentences in Russian summarizing the apartment's key qualities

Be honest and critical. If photos are missing or unclear, base assessment on description."""


def review_single(client: anthropic.Anthropic, candidate: dict) -> dict:
    """Call Claude to review one candidate. Returns dict with ad_id + review fields."""
    ad_id = candidate["ad_id"]
    desc = candidate.get("description") or ""
    images = candidate.get("images") or []
    # Limit to first 6 images
    images = images[:6]

    # Build content blocks
    content: list[dict] = []

    # Text block: description
    text_block = {
        "type": "text",
        "text": f"Apartment description:\n{desc[:3000]}\n\nPlease analyze the photos and description above."
    }

    # Image blocks
    img_blocks = []
    for url in images:
        if url and isinstance(url, str) and url.startswith("http"):
            img_blocks.append({
                "type": "image",
                "source": {
                    "type": "url",
                    "url": url,
                }
            })

    # Put images first, then text
    content = img_blocks + [text_block]

    if not content:
        content = [text_block]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=REVIEW_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[^\n]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        raw = raw.strip()

    review = json.loads(raw)
    review["ad_id"] = ad_id
    return review


def photo_review(candidates: list[dict], out_dir: Path) -> dict[int, dict]:
    """Review all candidates in batches of 10. Returns dict ad_id -> review."""
    print("\n=== STEP 2: Photo + description review ===")
    client = anthropic.Anthropic()

    # Check which batches already exist (resumable) — only count successes
    existing_reviews: dict[int, dict] = {}
    for f in sorted(out_dir.glob("result_batch_*.json")):
        try:
            batch_data = json.loads(f.read_text())
            successes = [r for r in batch_data if "error" not in r]
            for r in successes:
                existing_reviews[r["ad_id"]] = r
            if successes:
                print(f"  Loaded existing {f.name} ({len(successes)}/{len(batch_data)} successes)")
        except Exception as e:
            print(f"  Warning: could not load {f.name}: {e}")

    # Only skip candidates with successful (non-error) reviews
    already_done = set(existing_reviews.keys())
    remaining = [c for c in candidates if c["ad_id"] not in already_done]
    print(f"Total candidates: {len(candidates)}, already reviewed: {len(already_done)}, remaining: {len(remaining)}")

    BATCH_SIZE = 10
    # Use a counter for new batch files to avoid collisions
    next_batch_num = len(list(out_dir.glob("result_batch_*.json")))

    for batch_idx in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[batch_idx:batch_idx + BATCH_SIZE]
        batch_results = []

        print(f"\n  Processing batch {next_batch_num:02d} ({len(batch)} items)...")
        for i, cand in enumerate(batch):
            ad_id = cand["ad_id"]
            try:
                review = review_single(client, cand)
                batch_results.append(review)
                print(f"    [{i+1}/{len(batch)}] ad_id={ad_id} OK — {review.get('furniture_style','?')} / {review.get('condition','?')}")
            except Exception as e:
                print(f"    [{i+1}/{len(batch)}] ad_id={ad_id} ERROR: {e}")
                batch_results.append({"ad_id": ad_id, "error": str(e)})

        # Save batch
        batch_path = out_dir / f"result_batch_{next_batch_num:02d}.json"
        batch_path.write_text(json.dumps(batch_results, ensure_ascii=False, indent=2))
        print(f"  Saved {batch_path.name}")
        next_batch_num += 1

        # Add successful reviews to running results
        for r in batch_results:
            if "error" not in r:
                existing_reviews[r["ad_id"]] = r

        # Rate limit: sleep between batches (except after last)
        if batch_idx + BATCH_SIZE < len(remaining):
            time.sleep(3)

    print(f"\nTotal reviews collected: {len(existing_reviews)}")
    return existing_reviews


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Scoring + HTML generation
# ─────────────────────────────────────────────────────────────────────────────
FURNITURE_DELTA = {
    "modern_stylish": 1.5,
    "modern_neutral": 0.8,
    "ikea_basic": 0.0,
    "dated": -1.2,
    "old_dingy": -2.5,
}
BUILDING_AGE_DELTA = {
    "new": 1.2,
    "renovated": 0.8,
    "modern_2010s": 0.3,
    "older_but_ok": -0.4,
    "old_dated": -1.5,
}
CONDITION_DELTA = {
    "pristine": 0.8,
    "good": 0.3,
    "worn": -0.7,
    "shabby": -2.0,
}
LIGHT_DELTA = {"bright": 0.4, "ok": 0.0, "dark": -0.6}


def raw_score(row: dict) -> float:
    s = 0.0

    price = row["price"]
    if price <= 1300:
        s += 1.0
    elif price <= 1500:
        s += 0.6
    elif price <= 1650:
        s += 0.2
    elif price <= 1700:
        s -= 0.1
    else:
        s -= 0.5

    if row.get("utilities_included"):
        s += 0.7

    dist = row.get("dist_km")
    if dist is not None and not (isinstance(dist, float) and math.isnan(dist)):
        if dist <= 3:
            s += 0.8
        elif dist <= 6:
            s += 0.4
        elif dist <= 10:
            s += 0.0
        elif dist <= 15:
            s -= 0.5
        else:
            s -= 1.5

    s += FURNITURE_DELTA.get(row.get("furniture_style") or "", 0)
    s += BUILDING_AGE_DELTA.get(row.get("building_age") or "", 0)
    s += CONDITION_DELTA.get(row.get("condition") or "", 0)
    s += LIGHT_DELTA.get(row.get("light_quality") or "", 0)

    if row.get("has_desk"):
        s += 0.5
    if row.get("has_pool_visible") or row.get("has_pool"):
        s += 0.7
    if row.get("has_seaview_visible") or row.get("has_seaview"):
        s += 1.0
    if row.get("has_mountainview_visible") or row.get("has_mountainview"):
        s += 0.4
    if row.get("has_greenview_visible") or row.get("has_greenview"):
        s += 0.3
    if row.get("has_balcony"):
        s += 0.15
    if row.get("has_quiet"):
        s += 0.3
    if row.get("has_new_building"):
        s += 0.2
    if row.get("busy_road"):
        s -= 2.0
    if row.get("deposit_months") and row["deposit_months"] >= 2:
        s -= 1.5

    rf = row.get("red_flags") or []
    s -= 0.4 * len(rf)
    gf = row.get("green_flags") or []
    s += 0.15 * len(gf)

    return s


def build_explanation(row: dict) -> str:
    parts = []
    fs = row.get("furniture_style")
    ba = row.get("building_age")
    cond = row.get("condition")
    nice = {
        "modern_stylish": "стильная современная мебель",
        "modern_neutral": "современная нейтральная мебель",
        "ikea_basic": "простая базовая мебель",
        "dated": "устаревшая мебель",
        "old_dingy": "очень старая мебель",
        "new": "новостройка",
        "renovated": "после реновации",
        "modern_2010s": "здание 2010-х",
        "older_but_ok": "более старое здание, но в порядке",
        "old_dated": "старое здание",
        "pristine": "идеальное состояние",
        "good": "хорошее состояние",
        "worn": "видны следы износа",
        "shabby": "обшарпано",
    }
    if fs:
        parts.append(nice.get(fs, fs))
    if ba:
        parts.append(nice.get(ba, ba))
    if cond and cond not in ("good",):
        parts.append(nice.get(cond, cond))
    if row.get("has_seaview_visible") or row.get("has_seaview"):
        parts.append("вид на море")
    if row.get("has_mountainview_visible") or row.get("has_mountainview"):
        parts.append("вид на горы")
    if row.get("has_greenview_visible") or row.get("has_greenview"):
        parts.append("вид на зелень")
    if row.get("has_pool_visible") or row.get("has_pool"):
        parts.append("бассейн")
    if row.get("has_desk"):
        parts.append("рабочий стол")
    if row.get("has_balcony"):
        parts.append("балкон")
    if row.get("utilities_included"):
        parts.append("часть КУ включена")
    if row.get("busy_road"):
        parts.append("⚠ проездная улица")
    if row.get("deposit_months") and row["deposit_months"] >= 2:
        parts.append(f"⚠ депозит {row['deposit_months']} мес")
    dist = row.get("dist_km")
    if dist is not None and not (isinstance(dist, float) and math.isnan(dist)):
        parts.append(f"{dist:.1f} км от Alber Blanc")
    summary = row.get("summary") or ""
    rf = row.get("red_flags") or []
    if rf:
        parts.append("минусы: " + ", ".join(rf[:4]))
    gf = row.get("green_flags") or []
    if gf:
        parts.append("плюсы: " + ", ".join(gf[:4]))
    head = ". ".join(parts)
    if summary:
        head = f"{summary} {head}"
    return head


HTML_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Топ-50 квартир в Лимассоле — {stamp}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
         margin: 0; padding: 24px; background: #f5f5f7; color: #1d1d1f; }}
  h1 {{ font-size: 24px; margin: 0 0 4px; }}
  .meta {{ color: #6e6e73; font-size: 13px; margin-bottom: 20px; }}
  table {{ border-collapse: collapse; width: 100%; background: white;
          box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-radius: 8px; overflow: hidden; }}
  thead th {{ position: sticky; top: 0; background: #1d1d1f; color: white;
              text-align: left; padding: 10px 12px; font-size: 13px; font-weight: 600; }}
  td {{ padding: 12px; border-top: 1px solid #e5e5ea; vertical-align: top; font-size: 14px; }}
  tr:nth-child(even) td {{ background: #fafafa; }}
  td.rank {{ font-weight: 700; font-size: 18px; color: #1d1d1f; width: 36px; text-align: center; }}
  td.price {{ font-weight: 600; white-space: nowrap; }}
  td.score {{ font-weight: 700; font-size: 20px; color: #007aff; text-align: center; width: 60px; }}
  td.bedrooms {{ text-align: center; width: 80px; }}
  td.photo {{ width: 250px; }}
  td.photo img {{ width: 240px; height: 180px; object-fit: cover; border-radius: 6px;
                  display: block; }}
  td.expl {{ font-size: 13px; line-height: 1.4; color: #3a3a3c; max-width: 480px; }}
  td.link {{ width: 140px; }}
  td.link a {{ color: #007aff; text-decoration: none; font-size: 13px; }}
  td.link a:hover {{ text-decoration: underline; }}
  .badge {{ display: inline-block; padding: 2px 8px; background: #34c759; color: white;
            border-radius: 10px; font-size: 11px; margin-left: 4px; }}
  .badge.warn {{ background: #ff9500; }}
  .badge.gray {{ background: #8e8e93; }}
</style>
</head>
<body>
  <h1>Топ-50 квартир в Лимассоле</h1>
  <div class="meta">
    Источник: bazaraki.com · Снимок: {snapshot} · Сгенерировано: {stamp}<br>
    Фильтры: Лимассол · студия/1/2 спальни · цена ≤ 1750€ · не старше 2000 г. · с мебелью · {total_candidates} кандидатов, top-50 показано<br>
    Опорная точка для расстояния: Alber Blanc, Limassol (34.6854, 33.0557)
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Цена</th>
        <th>Спальни</th>
        <th>Фото</th>
        <th>Балл</th>
        <th>Оценка</th>
        <th>Ссылка</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""


def render_row(rank: int, row: dict) -> str:
    photo = ""
    imgs = row.get("images") or []
    if imgs:
        photo = f'<img src="{html.escape(imgs[0])}" loading="lazy" alt="">'

    price_val = int(row["price"])
    price_str = f"{price_val}€"
    badges = ""
    util = row.get("utilities_included") or []
    if util:
        badges += '<span class="badge">КУ ↓</span>'
    if row.get("has_pool_visible") or row.get("has_pool"):
        badges += '<span class="badge">🏊</span>'
    if row.get("has_seaview_visible") or row.get("has_seaview"):
        badges += '<span class="badge">🌊</span>'
    if row.get("has_desk"):
        badges += '<span class="badge gray">стол</span>'
    if row.get("busy_road"):
        badges += '<span class="badge warn">⚠ проезд</span>'

    bedrooms = html.escape(str(row.get("Bedrooms") or row.get("bedrooms") or ""))
    expl = html.escape(build_explanation(row))
    url = html.escape(row["url"])
    score = row["score"]

    return f"""      <tr>
        <td class="rank">{rank}</td>
        <td class="price">{price_str}<br><small style="color:#6e6e73">{html.escape(row.get('district') or '')}</small>{badges}</td>
        <td class="bedrooms">{bedrooms}</td>
        <td class="photo">{photo}</td>
        <td class="score">{score}</td>
        <td class="expl">{expl}</td>
        <td class="link"><a href="{url}" target="_blank">открыть →</a></td>
      </tr>"""


def generate_html(candidates: list[dict], reviews: dict[int, dict], out_dir: Path, stamp: str) -> None:
    print("\n=== STEP 3: Generating HTML ===")

    by_id = {r["ad_id"]: r for r in candidates}

    enriched = []
    for aid, cand in by_id.items():
        rev = reviews.get(aid, {})
        merged = {**cand, **rev}
        merged["raw"] = raw_score(merged)
        enriched.append(merged)

    raw_vals = [r["raw"] for r in enriched]
    raw_min, raw_max = min(raw_vals), max(raw_vals)
    print(f"Raw score range: {raw_min:.2f} … {raw_max:.2f}")

    target_lo, target_hi = 4.0, 9.5
    span = max(raw_max - raw_min, 1e-6)
    for r in enriched:
        scaled = target_lo + (r["raw"] - raw_min) / span * (target_hi - target_lo)
        r["score"] = round(scaled, 1)

    enriched.sort(key=lambda r: r["score"], reverse=True)
    top50 = enriched[:50]

    # Save scored.json
    (out_dir / "scored.json").write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2, default=str)
    )

    rows_html = "\n".join(render_row(i + 1, r) for i, r in enumerate(top50))
    html_content = HTML_TEMPLATE.format(
        stamp=stamp,
        snapshot=SNAPSHOT_LABEL,
        total_candidates=len(candidates),
        rows=rows_html,
    )
    html_path = out_dir / "index.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"HTML written to: {html_path}")
    print(f"Top-50 scores: {[r['score'] for r in top50]}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Limassol rental pipeline")
    parser.add_argument("--api-key", default=None,
                        help="Anthropic API key (overrides ANTHROPIC_API_KEY env var)")
    parser.add_argument("--run-dir", default=None,
                        help="Resume from an existing run directory (skips step 1)")
    args = parser.parse_args()

    # Set API key if provided via CLI arg
    if args.api_key:
        os.environ["ANTHROPIC_API_KEY"] = args.api_key

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY not set. Step 2 (photo review) will fail.")
        print("  Set it via: ANTHROPIC_API_KEY=sk-... python run_pipeline_2026_05_27.py")
        print("  Or create /Users/alekseygrachev/git/bazaraki/.env with ANTHROPIC_API_KEY=...")

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if args.run_dir:
        out_dir = Path(args.run_dir)
        if not out_dir.exists():
            raise FileNotFoundError(f"Run dir not found: {out_dir}")
        print(f"Resuming from existing run directory: {out_dir}")
        candidates = json.loads((out_dir / "candidates_top100.json").read_text())
        # Delete existing error-only batch files so we can re-run cleanly
        for bf in sorted(out_dir.glob("result_batch_*.json")):
            data = json.loads(bf.read_text())
            if all("error" in r for r in data):
                print(f"  Removing all-error batch file: {bf.name}")
                bf.unlink()
    else:
        out_dir = Path("/Users/alekseygrachev/git/bazaraki/analytics") / f"2026-05-27_{stamp.split('_')[1]}"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {out_dir}")
        # Step 1
        candidates = build_candidates(out_dir)

    # Step 2
    reviews = photo_review(candidates, out_dir)

    # Step 3
    generate_html(candidates, reviews, out_dir, stamp)

    print(f"\nPipeline complete.")
    print(f"Output: {out_dir}")
    print(out_dir)


if __name__ == "__main__":
    main()
