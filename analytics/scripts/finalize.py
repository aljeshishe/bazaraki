"""Combine photo-review results, apply final scoring, write top-50 HTML."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import pandas as pd

RUN_DIR_DEFAULT = "/Users/alekseygrachev/git/bazaraki/analytics/2026-05-17_16-02-49"

# Mapping from photo-review classifications to score deltas.
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
    """Unclamped raw score — will be rescaled at the end."""
    s = 0.0

    # Price relative to ceiling
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

    # Distance bucket
    dist = row.get("dist_km")
    if dist is not None and not pd.isna(dist):
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

    # Photo-derived (the heaviest contributors)
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
    """One-paragraph plain-text explanation of why this got the score."""
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
    if dist is not None and not pd.isna(dist):
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
    Фильтры: Лимассол · студия/1/2 спальни · цена ≤ 1750€ · {total_candidates} кандидатов до отсева, top-50 показано<br>
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

    price = f"{int(row['price'])}€"
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
        badges += '<span class="badge warn">проезд</span>'

    bedrooms = html.escape(str(row.get("Bedrooms") or row.get("bedrooms") or ""))
    expl = html.escape(build_explanation(row))
    url = html.escape(row["url"])
    score = row["score"]

    return f"""      <tr>
        <td class="rank">{rank}</td>
        <td class="price">{price}<br><small style="color:#6e6e73">{html.escape(row.get('district') or '')}</small>{badges}</td>
        <td class="bedrooms">{bedrooms}</td>
        <td class="photo">{photo}</td>
        <td class="score">{score}</td>
        <td class="expl">{expl}</td>
        <td class="link"><a href="{url}" target="_blank">открыть →</a></td>
      </tr>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default=RUN_DIR_DEFAULT)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)

    # Load candidate top-80
    top80 = json.loads((run_dir / "candidates_top80.json").read_text())
    by_id = {r["ad_id"]: r for r in top80}

    # Merge all batch results
    reviews: dict[int, dict] = {}
    for f in sorted(run_dir.glob("result_batch_*.json")):
        for r in json.loads(f.read_text()):
            reviews[r["ad_id"]] = r

    print(f"Loaded {len(reviews)} reviews for {len(by_id)} candidates")
    missing = [aid for aid in by_id if aid not in reviews]
    if missing:
        print(f"WARNING: {len(missing)} candidates missing review: {missing[:10]}")

    enriched = []
    for aid, cand in by_id.items():
        rev = reviews.get(aid, {})
        merged = {**cand, **rev}
        merged["raw"] = raw_score(merged)
        enriched.append(merged)

    raw_vals = [r["raw"] for r in enriched]
    raw_min, raw_max = min(raw_vals), max(raw_vals)
    print(f"Raw score range: {raw_min:.2f} … {raw_max:.2f}")
    # Map raw range to [4.0, 9.5] so even worst candidates of top-80 stay > 4
    # (they all passed prefilter, so they're not awful).
    target_lo, target_hi = 4.0, 9.5
    span = max(raw_max - raw_min, 1e-6)

    for r in enriched:
        scaled = target_lo + (r["raw"] - raw_min) / span * (target_hi - target_lo)
        r["score"] = round(scaled, 1)

    enriched.sort(key=lambda r: r["score"], reverse=True)
    top50 = enriched[:50]

    # Save scored.json
    (run_dir / "scored.json").write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2, default=str)
    )

    rows = "\n".join(render_row(i + 1, r) for i, r in enumerate(top50))
    html_out = HTML_TEMPLATE.format(
        stamp=run_dir.name,
        snapshot="2026-05-17 11:22",
        total_candidates=len(top80),
        rows=rows,
    )
    (run_dir / "index.html").write_text(html_out)
    print(f"HTML written to: {run_dir/'index.html'}")
    print(f"Top-50 scores: {[r['score'] for r in top50]}")


if __name__ == "__main__":
    main()
