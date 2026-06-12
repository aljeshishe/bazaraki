"""Build an interactive Leaflet map of the top-50 rentals.

Each point is placed at its district centroid (since lat/lng is missing in the
parquet) with a small deterministic jitter so overlapping listings don't fully
stack. Clicking a marker opens a side panel with full details.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from build_candidates import DISTRICT_COORDS, ORIGIN
from finalize import build_explanation

RUN_DIR_DEFAULT = "/Users/alekseygrachev/git/bazaraki/analytics/2026-05-17_16-02-49"


def jittered(ad_id: int, base: tuple[float, float]) -> tuple[float, float]:
    """Deterministic jitter so same ad always lands on the same spot."""
    h = hashlib.md5(str(ad_id).encode()).digest()
    # ±0.004 deg ≈ ±400m
    dlat = ((h[0] - 128) / 128) * 0.0035
    dlng = ((h[1] - 128) / 128) * 0.0045
    return base[0] + dlat, base[1] + dlng


def color_for_score(score: float) -> str:
    if score >= 9.0:
        return "#34c759"  # green
    if score >= 8.5:
        return "#5ac8fa"  # blue
    if score >= 8.0:
        return "#007aff"  # darker blue
    if score >= 7.5:
        return "#ff9500"  # orange
    return "#ff3b30"  # red


HTML_DOC = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Карта аренды в Лимассоле — top-50</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<style>
  * {{ box-sizing: border-box; }}
  body, html {{ margin: 0; padding: 0; height: 100%;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    color: #1d1d1f; }}
  #app {{ display: flex; height: 100vh; }}
  #map {{ flex: 1; min-width: 0; }}
  #panel {{
    width: 380px; max-width: 50vw; flex-shrink: 0; background: white;
    border-left: 1px solid #d2d2d7; overflow-y: auto; padding: 0;
    display: flex; flex-direction: column;
  }}
  #panel.empty .empty-state {{ display: block; }}
  #panel:not(.empty) .empty-state {{ display: none; }}
  #panel:not(.empty) .panel-content {{ display: block; }}
  .panel-content {{ display: none; }}
  .panel-header {{
    padding: 16px 18px; background: #1d1d1f; color: white; flex-shrink: 0;
  }}
  .panel-header h2 {{ margin: 0 0 4px; font-size: 18px; font-weight: 600; }}
  .panel-header .sub {{ color: #a1a1a6; font-size: 12px; }}
  .panel-photo {{
    width: 100%; height: 240px; object-fit: cover; display: block; background: #f5f5f7;
  }}
  .panel-meta {{ padding: 14px 18px; border-bottom: 1px solid #e5e5ea; }}
  .row {{ display: flex; justify-content: space-between; align-items: baseline; margin: 4px 0; font-size: 14px; }}
  .row .k {{ color: #6e6e73; font-size: 12px; }}
  .row .v {{ font-weight: 500; }}
  .score-pill {{ font-size: 24px; font-weight: 700; color: white; padding: 6px 14px;
                  border-radius: 14px; display: inline-block; }}
  .badges {{ margin: 8px 0; }}
  .badge {{ display: inline-block; padding: 3px 10px; background: #34c759; color: white;
            border-radius: 10px; font-size: 11px; margin: 2px 4px 2px 0; }}
  .badge.warn {{ background: #ff9500; }}
  .badge.gray {{ background: #8e8e93; }}
  .badge.red {{ background: #ff3b30; }}
  .panel-section {{ padding: 14px 18px; border-bottom: 1px solid #e5e5ea; }}
  .panel-section h3 {{ margin: 0 0 8px; font-size: 12px; text-transform: uppercase;
                       letter-spacing: 0.5px; color: #6e6e73; font-weight: 600; }}
  .panel-section p {{ margin: 0; font-size: 14px; line-height: 1.5; color: #1d1d1f; }}
  .flag-list {{ margin: 4px 0 0; padding-left: 18px; font-size: 13px; }}
  .flag-list li {{ margin: 3px 0; }}
  .open-btn {{
    display: block; margin: 16px 18px; padding: 12px; text-align: center;
    background: #007aff; color: white; text-decoration: none; font-weight: 600;
    border-radius: 8px; font-size: 14px;
  }}
  .empty-state {{
    display: none; padding: 40px 24px; text-align: center; color: #6e6e73; font-size: 14px;
  }}
  .empty-state h2 {{ color: #1d1d1f; margin-bottom: 8px; }}
  .legend {{
    position: absolute; top: 16px; right: 16px; z-index: 1000; background: white;
    padding: 10px 12px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    font-size: 12px;
  }}
  .legend .item {{ display: flex; align-items: center; margin: 3px 0; }}
  .legend .dot {{ width: 14px; height: 14px; border-radius: 50%; margin-right: 8px;
                  border: 2px solid white; box-shadow: 0 0 0 1px rgba(0,0,0,0.2); }}
  .price-tag {{
    background: white; border: 2px solid #1d1d1f; border-radius: 14px;
    padding: 2px 8px; font-weight: 700; font-size: 12px; white-space: nowrap;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
  }}
  .price-tag .rank {{ background: #1d1d1f; color: white; border-radius: 8px;
                       padding: 0 5px; margin-right: 4px; font-size: 11px; }}
  .anchor-pin {{
    background: #ff2d55; color: white; padding: 6px 10px; border-radius: 16px;
    font-weight: 700; font-size: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }}
</style>
</head>
<body>
<div id="app">
  <div id="map">
    <div class="legend">
      <div class="item"><div class="dot" style="background:#34c759"></div>9.0+ отличный</div>
      <div class="item"><div class="dot" style="background:#5ac8fa"></div>8.5–8.9 очень хорошо</div>
      <div class="item"><div class="dot" style="background:#007aff"></div>8.0–8.4 хорошо</div>
      <div class="item"><div class="dot" style="background:#ff9500"></div>7.5–7.9 средне</div>
      <div class="item"><div class="dot" style="background:#ff3b30"></div>&lt; 7.5 ниже среднего</div>
      <div class="item" style="margin-top:8px"><div class="dot" style="background:#ff2d55"></div>Alber Blanc (офис)</div>
    </div>
  </div>
  <aside id="panel" class="empty">
    <div class="empty-state">
      <h2>Выберите точку на карте</h2>
      <p>Кликните маркер с ценой, чтобы увидеть детали объявления, фото и оценку.</p>
    </div>
    <div class="panel-content">
      <div class="panel-header">
        <h2 id="p-title"></h2>
        <div class="sub" id="p-sub"></div>
      </div>
      <img class="panel-photo" id="p-photo" src="" alt="">
      <div class="panel-meta">
        <div class="row"><span class="k">Цена</span><span class="v" id="p-price"></span></div>
        <div class="row"><span class="k">Спальни</span><span class="v" id="p-beds"></span></div>
        <div class="row"><span class="k">Район</span><span class="v" id="p-district"></span></div>
        <div class="row"><span class="k">До Alber Blanc</span><span class="v" id="p-dist"></span></div>
        <div class="row" style="margin-top:10px"><span class="k">Балл</span><span id="p-score" class="score-pill">—</span></div>
        <div class="badges" id="p-badges"></div>
      </div>
      <div class="panel-section">
        <h3>Резюме</h3>
        <p id="p-summary"></p>
      </div>
      <div class="panel-section" id="p-pros-section">
        <h3>Плюсы</h3>
        <ul class="flag-list" id="p-pros"></ul>
      </div>
      <div class="panel-section" id="p-cons-section">
        <h3>Минусы</h3>
        <ul class="flag-list" id="p-cons"></ul>
      </div>
      <a class="open-btn" id="p-link" href="#" target="_blank">Открыть на Bazaraki →</a>
    </div>
  </aside>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
const POINTS = {points_json};
const ORIGIN = {origin};

const map = L.map('map', {{ zoomControl: true }}).setView([34.692, 33.060], 12);

L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '© OpenStreetMap',
  maxZoom: 19,
}}).addTo(map);

// Alber Blanc pin
L.marker(ORIGIN, {{
  icon: L.divIcon({{
    className: 'anchor-marker',
    html: '<div class="anchor-pin">Alber Blanc</div>',
    iconSize: [110, 28], iconAnchor: [55, 14],
  }}),
}}).addTo(map);

const panel = document.getElementById('panel');

function setPanel(p) {{
  panel.classList.remove('empty');
  document.getElementById('p-title').textContent = `#${{p.rank}} · ${{p.title || 'Без названия'}}`;
  document.getElementById('p-sub').textContent = `ad ${{p.ad_id}}`;
  document.getElementById('p-photo').src = p.photo || '';
  document.getElementById('p-photo').style.display = p.photo ? 'block' : 'none';
  document.getElementById('p-price').textContent = p.price + ' €/мес';
  document.getElementById('p-beds').textContent = p.bedrooms;
  document.getElementById('p-district').textContent = p.district || '—';
  document.getElementById('p-dist').textContent = p.dist_km != null ? p.dist_km.toFixed(1) + ' км' : '—';
  const score = document.getElementById('p-score');
  score.textContent = p.score.toFixed(1);
  score.style.background = p.color;
  // badges
  const b = document.getElementById('p-badges');
  b.innerHTML = '';
  for (const tag of (p.badges || [])) {{
    const el = document.createElement('span');
    el.className = 'badge ' + (tag.kind || '');
    el.textContent = tag.text;
    b.appendChild(el);
  }}
  document.getElementById('p-summary').textContent = p.summary || '—';
  // pros/cons
  function fill(id, list, sectionId) {{
    const ul = document.getElementById(id);
    ul.innerHTML = '';
    const section = document.getElementById(sectionId);
    if (!list || list.length === 0) {{ section.style.display = 'none'; return; }}
    section.style.display = '';
    for (const item of list) {{
      const li = document.createElement('li');
      li.textContent = item;
      ul.appendChild(li);
    }}
  }}
  fill('p-pros', p.green_flags, 'p-pros-section');
  fill('p-cons', p.red_flags, 'p-cons-section');
  document.getElementById('p-link').href = p.url;
}}

for (const p of POINTS) {{
  const marker = L.marker([p.lat, p.lng], {{
    icon: L.divIcon({{
      className: 'price-icon',
      html: `<div class="price-tag" style="border-color:${{p.color}}"><span class="rank" style="background:${{p.color}}">${{p.rank}}</span>${{p.price}}€</div>`,
      iconSize: [80, 24], iconAnchor: [40, 12],
    }}),
  }});
  marker.addTo(map);
  marker.on('click', () => {{ setPanel(p); }});
}}

// Auto-fit bounds to all points
const bounds = L.latLngBounds(POINTS.map(p => [p.lat, p.lng]));
bounds.extend(ORIGIN);
map.fitBounds(bounds, {{ padding: [40, 40] }});
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default=RUN_DIR_DEFAULT)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)

    scored = json.loads((run_dir / "scored.json").read_text())
    scored.sort(key=lambda r: r["score"], reverse=True)
    top50 = scored[:50]

    points = []
    for rank, r in enumerate(top50, 1):
        district = r.get("district") or ""
        base = DISTRICT_COORDS.get(district)
        if not base:
            # fallback to Limassol center
            base = (34.684, 33.040)
        lat, lng = jittered(r["ad_id"], base)
        photo = (r.get("images") or [None])[0]
        score = float(r["score"])
        color = color_for_score(score)

        badges = []
        util = r.get("utilities_included") or []
        if util:
            badges.append({"text": "КУ ↓", "kind": ""})
        if r.get("has_pool_visible") or r.get("has_pool"):
            badges.append({"text": "🏊 бассейн", "kind": ""})
        if r.get("has_seaview_visible") or r.get("has_seaview"):
            badges.append({"text": "🌊 море", "kind": ""})
        if r.get("has_mountainview_visible") or r.get("has_mountainview"):
            badges.append({"text": "⛰ горы", "kind": ""})
        if r.get("has_greenview_visible"):
            badges.append({"text": "🌿 зелень", "kind": ""})
        if r.get("has_desk"):
            badges.append({"text": "🖥 стол", "kind": "gray"})
        if r.get("has_balcony"):
            badges.append({"text": "балкон", "kind": "gray"})
        if r.get("busy_road"):
            badges.append({"text": "⚠ проездная улица", "kind": "warn"})
        if r.get("deposit_months") and r["deposit_months"] >= 2:
            badges.append({"text": f"⚠ депозит {r['deposit_months']} мес", "kind": "red"})

        points.append({
            "rank": rank,
            "ad_id": r["ad_id"],
            "title": r.get("title"),
            "url": r["url"],
            "price": int(r["price"]),
            "bedrooms": str(r.get("Bedrooms") or ""),
            "district": district,
            "dist_km": r.get("dist_km"),
            "score": score,
            "color": color,
            "lat": lat,
            "lng": lng,
            "photo": photo,
            "summary": r.get("summary") or "",
            "green_flags": r.get("green_flags") or [],
            "red_flags": r.get("red_flags") or [],
            "badges": badges,
        })

    out = HTML_DOC.format(
        points_json=json.dumps(points, ensure_ascii=False),
        origin=json.dumps(list(ORIGIN)),
    )
    (run_dir / "map.html").write_text(out)
    print(f"Map written to: {run_dir/'map.html'}")
    print(f"Points: {len(points)}")


if __name__ == "__main__":
    main()
