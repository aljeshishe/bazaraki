"""Build the candidate pool of Limassol rentals matching hard filters.

Pre-scores by price/distance/description-signals so we can hand off the top ~80
to photo-review agents.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from bazaraki.utils import to_legacy_format

PARQUET = (
    "/Users/alekseygrachev/git/bazaraki/output/"
    "2026-05-17 11:22:54 real-estate-to-rent_real-estate-for-sale.parquet"
)
ORIGIN = (34.6854, 33.0557)  # Alber Blanc office

# Approximate district centroids in Limassol municipality.
# Used because lat/lng columns are all NaN in current parquet dumps.
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


# Major arteries — if a listing's description mentions one, the unit likely
# sits on/near a busy through-road.
BUSY_ROAD_KEYWORDS = [
    "makarios", "makariou", "griva digeni", "griva dhigeni", "gryva digeni",
    "spyrou kyprianou", "spirou kiprianou", "franklin roosevelt",
    "archiepiskopou leontiou", "leontiou", "omonias avenue", "omonia avenue",
    "28th october avenue", "28 october", "amathountos", "armenias",
    "vasileos konstantinou", "vasileos georgiou",
]


def haversine(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    R = 6371.0
    lat1, lng1 = map(math.radians, p1)
    lat2, lng2 = map(math.radians, p2)
    dlat, dlng = lat2 - lat1, lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def parse_district(loc: str) -> str:
    parts = [p.strip() for p in loc.split(",")]
    return parts[1] if len(parts) >= 2 else parts[0]


def dist_to_origin(district: str) -> float:
    coords = DISTRICT_COORDS.get(district)
    return haversine(ORIGIN, coords) if coords else math.nan


def extract_signals(desc: str) -> dict:
    if not isinstance(desc, str):
        desc = ""
    d = desc.lower()

    def has(*terms: str) -> bool:
        return any(t in d for t in terms)

    # Utilities included by landlord
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

    # Deposit
    deposit_months: int | None = None
    m = re.search(r"(\d)\s*(?:months?|month's)\s*(?:deposit|rent\s*deposit|security)", d)
    if m:
        deposit_months = int(m.group(1))
    if not deposit_months and ("two months deposit" in d or "two-month deposit" in d
                               or "2-month deposit" in d):
        deposit_months = 2

    # Features
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

    # Busy roads
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

    # Furnishing — unfurnished is a non-starter for many; partly is ok
    furn = (row.get("Furnishing") or "").lower()
    if "unfurnished" in furn:
        s -= 0.5

    return s


def main() -> None:
    df = to_legacy_format(pd.read_parquet(PARQUET))
    df["city"] = df.location.fillna("").str.split(",").str[0].str.strip()

    f = df[
        (df.cat1 == "Apartments, flats to rent")
        & (df.city == "Limassol")
        & (df.price <= 1750)
        & (df.Bedrooms.isin(["Studio", "1", "2"]))
        & (~df.sold)
    ].copy()
    f["district"] = f["location"].apply(parse_district)
    f["dist_km"] = f["district"].apply(dist_to_origin)

    signals = f["description"].apply(extract_signals).apply(pd.Series)
    f = pd.concat([f.reset_index(drop=True), signals.reset_index(drop=True)], axis=1)

    f["prescore"] = f.apply(pre_score, axis=1)
    f = f.sort_values("prescore", ascending=False).reset_index(drop=True)

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = Path("/Users/alekseygrachev/git/bazaraki/analytics") / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    keep_cols = [
        "ad_id", "url", "title", "price", "Bedrooms", "Bathrooms",
        "location", "district", "dist_km", "Property area", "Floor", "Furnishing",
        "Construction year", "Condition", "Included", "Parking", "Air conditioning",
        "Pets", "images", "description",
        "utilities_included", "deposit_months", "has_pool", "has_seaview",
        "has_mountainview", "has_greenview", "has_desk", "has_quiet",
        "has_new_building", "busy_road", "prescore",
    ]
    out_full = f[keep_cols].copy()
    # Coerce image list field for JSON serialization
    out_full["images"] = out_full["images"].apply(
        lambda x: list(x) if hasattr(x, "tolist") or isinstance(x, list) else []
    )
    out_full.to_json(out_dir / "candidates_all.json", orient="records", force_ascii=False, indent=2)

    # Top 80 → photo review pool
    top = out_full.head(80).copy()
    top.to_json(out_dir / "candidates_top80.json", orient="records", force_ascii=False, indent=2)

    print(f"Total candidates: {len(out_full)}")
    print(f"Top-80 saved.")
    print(f"Run dir: {out_dir}")
    print(f"Pre-score range: {out_full.prescore.min():.2f} … {out_full.prescore.max():.2f}")
    print(f"Top80 pre-score range: {top.prescore.min():.2f} … {top.prescore.max():.2f}")
    print(f"Districts in top80: {top.district.value_counts().to_dict()}")
    # write a tiny pointer
    (out_dir / "RUN_DIR.txt").write_text(str(out_dir))
    print(out_dir)


if __name__ == "__main__":
    main()
