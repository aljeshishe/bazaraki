"""Generate final HTML from manual photo+description review."""
import html
import json
from pathlib import Path

RUN_DIR = Path("/Users/alekseygrachev/git/bazaraki/analytics/2026-05-27_20-37-25")

# Manual scores based on visual photo review + description analysis
# Format: ad_id -> {score, furniture, building, condition, summary, green_flags, red_flags,
#                   has_desk, has_pool_visible, has_seaview_visible, has_balcony}
REVIEWS = {
    6503241: {"score": 9.5, "summary": "Отличная цена, стильный интерьер (каменные стены, зелёный диван), рабочий стол", "green_flags": ["дешевле 1000€", "рабочий стол", "3й этаж", "центр 2.5км", "стиль"], "red_flags": [], "has_desk": True},
    6511798: {"score": 9.3, "summary": "Лучшая цена из всех, вид на море, верхний этаж (3й), современный дом с лифтом", "green_flags": ["лучшая цена", "вид на море", "верхний этаж", "современный"], "red_flags": []},
    6390114: {"score": 9.2, "summary": "Все КУ включены — итого 1295€! Море в 50м, бассейн, 24/7 охрана, 2024г. Недостаток: 1й этаж", "green_flags": ["все КУ включены", "бассейн", "50м до пляжа", "падель-корт"], "red_flags": ["1й этаж", "9.7км от офиса"], "has_pool_visible": True},
    6433308: {"score": 9.0, "summary": "4й этаж, вид на море из спальни, новая мебель и техника, напротив Four Seasons", "green_flags": ["4й этаж", "вид на море", "новая мебель", "Four Seasons"], "red_flags": ["9.7км от офиса"]},
    6396316: {"score": 9.0, "summary": "Отмеченный наградами комплекс: 2 бассейна, ландшафтные сады, спа, тренажёрный зал. КУ включены", "green_flags": ["award-winning комплекс", "2 бассейна", "спа+тренажёрный", "КУ включены"], "red_flags": ["5км от офиса"], "has_pool_visible": True},
    6503247: {"score": 8.8, "summary": "Элегантный роскошный интерьер (фото!), 3й этаж, панорамный вид море+город, тихий холмистый район", "green_flags": ["роскошный интерьер", "3й этаж", "вид море+город", "тихо"], "red_flags": ["4км от офиса"]},
    6465609: {"score": 8.5, "summary": "Люксовый интерьер 2025г: дизайнерская кухня, панорамные окна, крем-диван. 2й этаж", "green_flags": ["люкс интерьер", "2025г", "дизайн кухня", "2й этаж"], "red_flags": ["бюджет на пределе (1790€)"]},
    6504615: {"score": 8.5, "summary": "Никогда не заселялась! Стильный минималистичный интерьер (фото), бренд новая мебель. 2й этаж", "green_flags": ["никогда не жили", "стильный интерьер", "2й этаж", "новая мебель+техника"], "red_flags": []},
    6502705: {"score": 8.5, "summary": "4й этаж, вид на море, бренд новое здание 2026, большой балкон, центр (3.4км)", "green_flags": ["4й этаж", "вид на море", "2026г", "большой балкон"], "red_flags": []},
    6405284: {"score": 8.5, "summary": "Цена включает КУ (1590€ итого), бассейн, 3й этаж, 2025г, светлый современный интерьер", "green_flags": ["КУ включены", "бассейн", "3й этаж", "2025г"], "red_flags": [], "has_pool_visible": True},
    6354038: {"score": 8.5, "summary": "Стильный дизайнерский интерьер (фото!): современная кухня, красивая гостиная. Вид на море, бассейн", "green_flags": ["дизайнерский интерьер", "вид на море", "бассейн", "200м пляж"], "red_flags": ["2000г постройки (реновирован)"], "has_pool_visible": True},
    6406875: {"score": 8.4, "summary": "3й этаж, вид на море, бассейн, 100м от пляжа, реновирован 2024г", "green_flags": ["3й этаж", "вид на море", "бассейн", "100м пляж"], "red_flags": ["9.7км от офиса"], "has_pool_visible": True},
    6454843: {"score": 8.3, "summary": "8й этаж, панорамный вид море и старый город, современный стиль, центр (1.7км)", "green_flags": ["8й этаж", "панорамный вид", "исторический центр", "стиль"], "red_flags": ["бюджет на пределе (1790€)"]},
    6515900: {"score": 8.3, "summary": "8й этаж, панорамный вид на море и старый Лимассол, современный реновированный", "green_flags": ["8й этаж", "панорамный вид", "центр", "реновирован"], "red_flags": ["бюджет на пределе (1790€)"]},
    6513115: {"score": 8.3, "summary": "8й этаж, 100м до моря, Kanika Neapolis, полностью реновирован, центр", "green_flags": ["8й этаж", "100м до моря", "центр", "реновирован"], "red_flags": []},
    6406600: {"score": 8.3, "summary": "8й этаж, 100м до моря, тот же комплекс Kanika, центральный Неаполис", "green_flags": ["8й этаж", "100м до моря", "центр"], "red_flags": []},
    6466976: {"score": 8.2, "summary": "Люксовый интерьер (фото!): бежевый диван, подвесные лампы. 5й этаж, старый город. Без парковки", "green_flags": ["роскошный интерьер", "5й этаж", "старый город", "2020г"], "red_flags": ["без парковки", "бюджет на пределе"]},
    6412091: {"score": 8.2, "summary": "Стильный интерьер: зелёный бархатный диван + каменные стены. Исторический центр, 1.3км от офиса", "green_flags": ["стиль (камень+велюр)", "исторический центр", "реновирован"], "red_flags": ["этаж неизвестен"]},
    6425555: {"score": 8.0, "summary": "4й этаж, беспрепятственный вид на море, 2 спальни, у Marina, минималистичный интерьер", "green_flags": ["4й этаж", "вид на море", "2 спальни", "у Marina"], "red_flags": ["без парковки", "«Older» год"]},
    6389376: {"score": 8.0, "summary": "Beachfront, 4й этаж, вид на море, бассейн, теннисный корт", "green_flags": ["4й этаж", "beachfront", "бассейн", "теннис"], "red_flags": ["9.7км от офиса", "бюджет 1770€"], "has_pool_visible": True},
    6516491: {"score": 8.0, "summary": "Стильный реновированный интерьер (фото!), 2 спальни, 100м², центр (1.3км). Недостаток: 1й этаж", "green_flags": ["стиль", "2 спальни 100м²", "центр 1.3км"], "red_flags": ["1й этаж"]},
    6506964: {"score": 7.8, "summary": "Полностью реновирован, вид на море, современный дизайн, паркет, центр (1.2км)", "green_flags": ["вид на море", "реновирован", "паркет", "центр 1.2км"], "red_flags": ["этаж неизвестен"]},
    6465331: {"score": 7.8, "summary": "3й этаж, вид на море, новая мебель+техника, КУ включены (1340€ итого), Agios Tychon", "green_flags": ["3й этаж", "вид на море", "КУ включены", "новая мебель"], "red_flags": ["9.7км от офиса"]},
    6473232: {"score": 7.8, "summary": "3й этаж, вид на море, реновирован, новая кухня, КУ включены. Доступен с 1 июля", "green_flags": ["3й этаж", "вид на море", "КУ включены"], "red_flags": ["9.7км от офиса", "с июля"]},
    6374599: {"score": 7.8, "summary": "2 спальни, вид на море+город, реновирован, подземная парковка, центр (1.3км)", "green_flags": ["2 спальни", "вид море+город", "подземная парковка", "центр"], "red_flags": ["бюджет на пределе", "этаж неизвестен"]},
    6450717: {"score": 7.8, "summary": "8й этаж, вид на море, центр, реновирован, у Marina. Здание 2000г, 40м²", "green_flags": ["8й этаж", "вид на море", "центр", "у Marina"], "red_flags": ["2000г постройки", "40м² тесно", "бюджет на пределе"]},
    6465241: {"score": 7.8, "summary": "4й (последний) этаж с лифтом, вид на море с балкона, у парка Дасуди", "green_flags": ["4й этаж", "вид на море", "у Dasoudi Park"], "red_flags": ["базовый интерьер (фото)"]},
    6414880: {"score": 7.8, "summary": "Панорамный вид на море, 1 мин до пляжа, реновирован. Описание указывает 2й этаж (не 1й)", "green_flags": ["панорама море", "1 мин пляж", "реновирован"], "red_flags": ["студия", "спорный этаж"]},
    6517148: {"score": 7.8, "summary": "2 спальни, 2й этаж, современное здание 2020г, большой балкон, центр (1.3км)", "green_flags": ["2 спальни", "2й этаж", "2020г", "большой балкон"], "red_flags": []},
    6484650: {"score": 7.5, "summary": "Новое здание 2025, бассейн на крыше, фотовольтаика, 2й этаж. Бюджет на пределе (+common)", "green_flags": ["2025г", "бассейн на крыше", "2й этаж"], "red_flags": ["бюджет на пределе"], "has_pool_visible": True},
    6470756: {"score": 7.5, "summary": "Новостройка 2024, бассейн, 2й этаж, стильный, рядом MyMall. Бюджет на пределе", "green_flags": ["2024г", "бассейн", "2й этаж", "стильный"], "red_flags": ["бюджет на пределе"], "has_pool_visible": True},
    6414257: {"score": 7.5, "summary": "Новое здание, бассейн, 2й этаж, 50м²+14м² балкон, рядом MyMall", "green_flags": ["новое", "бассейн", "2й этаж", "большой балкон"], "red_flags": [], "has_pool_visible": True},
    6474108: {"score": 7.5, "summary": "Закрытый комплекс с бассейном, 2й этаж, 2023г, современная кухня (фото)", "green_flags": ["бассейн", "2й этаж", "2023г"], "red_flags": [], "has_pool_visible": True},
    6512443: {"score": 7.5, "summary": "60м², современный 2024г, 2й этаж, полностью оснащён, рядом казино/MyMall", "green_flags": ["2024г", "2й этаж", "60м²", "полностью оснащён"], "red_flags": []},
    6465224: {"score": 7.5, "summary": "Тупик = нет сквозного движения! 2 спальни, 2й этаж, у Grammar School, центр (2.1км)", "green_flags": ["тихий тупик", "2 спальни", "2й этаж", "центр"], "red_flags": []},
    6471709: {"score": 7.5, "summary": "Пентхаус, 3й этаж, 90м²+15м² веранда, почти новая мебель, центр (2.1км)", "green_flags": ["3й этаж пентхаус", "90м²", "2 спальни", "центр"], "red_flags": ["2010г"]},
    6381547: {"score": 7.5, "summary": "3й этаж, вид на горы, 2 спальни, тихий район, новые техника и AC, реновированный лифт", "green_flags": ["3й этаж", "вид горы", "2 спальни", "тихо"], "red_flags": []},
    6357030: {"score": 7.5, "summary": "3й этаж, 2 спальни с мастер-ванной, новые AC, у трассы Mesa Geitonia", "green_flags": ["3й этаж", "2 спальни+мастер ванная", "новые AC"], "red_flags": ["бюджет на пределе"]},
    6430905: {"score": 7.5, "summary": "Люкс комплекс с бассейном, дизайнерская отделка, современная мебель, Trachoni", "green_flags": ["люкс", "бассейн", "высококлассная отделка"], "red_flags": ["5км от офиса", "этаж неизвестен"], "has_pool_visible": True},
    6430904: {"score": 7.5, "summary": "Тот же люкс комплекс, белый современный интерьер (фото), бассейн, Trachoni", "green_flags": ["люкс", "бассейн", "современный интерьер"], "red_flags": ["5км от офиса", "этаж неизвестен"], "has_pool_visible": True},
    6452018: {"score": 7.5, "summary": "2026г, офисная комната (рабочий стол!), тихий район, PV панели, рядом с больницей", "green_flags": ["рабочий стол", "2026г", "тихо", "PV панели"], "red_flags": ["этаж неизвестен"], "has_desk": True},
    6380258: {"score": 7.5, "summary": "Полностью реновирован 6 месяцев назад, огромный балкон, 2й этаж, 5 квартир в доме (тихо)", "green_flags": ["свежий ремонт", "огромный балкон", "2й этаж", "тихо"], "red_flags": ["«Older» здание"]},
    6375529: {"score": 7.5, "summary": "2025г Energy A, 3й этаж, современная мебель, близко к шоссе, 50м²", "green_flags": ["2025г", "3й этаж", "Energy A"], "red_flags": []},
    6349674: {"score": 7.3, "summary": "Бренд новый, 2 спальни, вся техника, современный дизайн, Agios Spyridon", "green_flags": ["бренд новый", "2 спальни", "современный"], "red_flags": ["этаж неизвестен"]},
    6352525: {"score": 7.3, "summary": "Включены электричество+вода+common (итого ~1240€ нетто!). Но 1й этаж", "green_flags": ["электр+вода+common включены", "реновирован"], "red_flags": ["1й этаж", "2002г"]},
    6141192: {"score": 7.3, "summary": "2 спальни, рабочий стол, интернет+common включены (итого ~1210€), просторный", "green_flags": ["рабочий стол", "2 спальни", "интернет+КУ включены"], "red_flags": ["1й этаж", "2010г"], "has_desk": True},
    6398200: {"score": 7.0, "summary": "2 спальни, бассейн, 2 парковки, 10 мин до пляжа. Но 1й этаж и устаревший интерьер (фото)", "green_flags": ["2 спальни", "бассейн", "2 парковки"], "red_flags": ["1й этаж", "устаревший интерьер"], "has_pool_visible": True},
    6516831: {"score": 7.0, "summary": "2 спальни, огромный бассейн, частный дворик, полностью реновирован, но 1й (ground) этаж", "green_flags": ["2 спальни", "бассейн", "частный дворик"], "red_flags": ["первый (цокольный) этаж"], "has_pool_visible": True},
    6511824: {"score": 7.0, "summary": "Бассейн, теннис, реновирован, закрытый комплекс. Но 1й этаж и 9.4км от офиса", "green_flags": ["бассейн", "теннис", "закрытый комплекс"], "red_flags": ["1й этаж", "9.4км от офиса"], "has_pool_visible": True},
    6493499: {"score": 7.0, "summary": "Стильный интерьер (зелёный бархатный диван + каменные стены), у Marina, исторический центр. 1й этаж", "green_flags": ["стиль", "у Marina", "центр"], "red_flags": ["1й этаж"]},
}

HTML_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Топ-50 квартир Лимассол — 2026-05-27</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
         margin: 0; padding: 24px; background: #f5f5f7; color: #1d1d1f; }}
  h1 {{ font-size: 24px; margin: 0 0 4px; }}
  .meta {{ color: #6e6e73; font-size: 13px; margin-bottom: 20px; line-height: 1.6; }}
  table {{ border-collapse: collapse; width: 100%; background: white;
          box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-radius: 8px; overflow: hidden; }}
  thead th {{ position: sticky; top: 0; background: #1d1d1f; color: white;
              text-align: left; padding: 10px 12px; font-size: 13px; font-weight: 600; }}
  td {{ padding: 10px 12px; border-top: 1px solid #e5e5ea; vertical-align: top; font-size: 13px; }}
  tr:nth-child(even) td {{ background: #fafafa; }}
  td.rank {{ font-weight: 700; font-size: 18px; color: #1d1d1f; width: 32px; text-align: center; }}
  td.price {{ font-weight: 600; white-space: nowrap; min-width: 110px; }}
  td.score {{ font-weight: 700; font-size: 22px; color: #007aff; text-align: center; width: 56px; }}
  td.beds {{ text-align: center; width: 64px; }}
  td.photo {{ width: 230px; }}
  td.photo img {{ width: 220px; height: 160px; object-fit: cover; border-radius: 6px; display: block; }}
  td.photo .no-photo {{ width: 220px; height: 160px; background: #e5e5ea; border-radius: 6px;
                        display: flex; align-items: center; justify-content: center; color: #8e8e93; font-size: 11px; }}
  td.expl {{ font-size: 12px; line-height: 1.5; color: #3a3a3c; max-width: 400px; }}
  td.expl .flags {{ margin-top: 4px; font-size: 11px; }}
  td.link {{ width: 120px; }}
  td.link a {{ color: #007aff; text-decoration: none; font-size: 12px; }}
  td.link a:hover {{ text-decoration: underline; }}
  .badge {{ display: inline-block; padding: 2px 6px; border-radius: 8px; font-size: 10px; margin: 1px; }}
  .b-green {{ background: #34c759; color: white; }}
  .b-blue  {{ background: #007aff; color: white; }}
  .b-gray  {{ background: #8e8e93; color: white; }}
  .b-warn  {{ background: #ff9500; color: white; }}
  .b-red   {{ background: #ff3b30; color: white; }}
  .plus  {{ color: #34c759; }}
  .minus {{ color: #ff3b30; }}
  .score-high {{ color: #34c759; }}
  .score-mid  {{ color: #ff9500; }}
</style>
</head>
<body>
<h1>Топ-50 квартир в Лимассоле для аренды</h1>
<div class="meta">
  Источник: bazaraki.com · Снимок: 2026-05-27 · Сгенерировано: 2026-05-27<br>
  Фильтры: Лимассол · студия/1/2 спальни · бюджет ≤ 1750€ с КУ · не старая мебель/здание · 687 кандидатов → топ-50<br>
  КУ = электричество (~80€) + вода (~30€) + интернет (~30€) + common (~150€) ≈ 290€/мес<br>
  Ориентир расстояния: Alber Blanc office (34.6854, 33.0557)
</div>
<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Цена / район</th>
      <th>Спальни</th>
      <th>Фото</th>
      <th>Балл</th>
      <th>Оценка и пояснение</th>
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

def floor_badge(floor):
    if not floor:
        return ""
    f = str(floor).lower()
    if "ground" in f:
        return '<span class="badge b-warn">0 эт</span>'
    if "1st" in f:
        return '<span class="badge b-warn">1й эт</span>'
    if "2nd" in f:
        return '<span class="badge b-gray">2й эт</span>'
    if "3rd" in f:
        return '<span class="badge b-blue">3й эт</span>'
    if "4th" in f:
        return '<span class="badge b-green">4й эт</span>'
    if "5th" in f or "6th" in f or "7th" in f:
        return '<span class="badge b-green">5+ эт</span>'
    if "8th" in f:
        return '<span class="badge b-green">8й эт</span>'
    return f'<span class="badge b-gray">{html.escape(floor)}</span>'

def render_row(rank, cand, rev):
    ad_id = cand["ad_id"]
    score = rev["score"]
    score_class = "score-high" if score >= 8.5 else ("score-mid" if score >= 7.5 else "")

    # Photo
    imgs = cand.get("images") or []
    if imgs:
        photo_html = f'<img src="{html.escape(imgs[0])}" loading="lazy" alt="">'
    else:
        photo_html = '<div class="no-photo">нет фото</div>'

    # Price
    price = int(cand["price"])
    district = html.escape(cand.get("district") or "")
    dist_km = cand.get("dist_km")
    dist_str = f"{dist_km:.1f}км" if dist_km and str(dist_km) != "nan" else ""

    util = cand.get("utilities_included") or []
    badges = floor_badge(cand.get("Floor"))
    if util:
        badges += '<span class="badge b-green">КУ↓</span>'
    if rev.get("has_pool_visible") or cand.get("has_pool"):
        badges += '<span class="badge b-blue">🏊</span>'
    if cand.get("has_seaview"):
        badges += '<span class="badge b-blue">🌊</span>'
    if rev.get("has_desk") or cand.get("has_desk"):
        badges += '<span class="badge b-gray">стол</span>'
    if cand.get("busy_road"):
        badges += '<span class="badge b-red">⚠проезд</span>'

    year = cand.get("Construction year") or ""

    price_cell = f"""<b>{price}€/мес</b><br>
<small style="color:#6e6e73">{district}</small><br>
<small style="color:#6e6e73">{dist_str} · {year}</small><br>
{badges}"""

    # Explanation
    summary = html.escape(rev.get("summary") or "")
    green = rev.get("green_flags") or []
    red = rev.get("red_flags") or []
    flags_html = ""
    if green:
        flags_html += '<span class="plus">✓ ' + html.escape(", ".join(green[:4])) + "</span><br>"
    if red:
        flags_html += '<span class="minus">✗ ' + html.escape(", ".join(red[:3])) + "</span>"
    expl = f'{summary}<div class="flags">{flags_html}</div>'

    beds = html.escape(str(cand.get("Bedrooms") or ""))
    url = html.escape(cand["url"])

    return f"""    <tr>
      <td class="rank">{rank}</td>
      <td class="price">{price_cell}</td>
      <td class="beds">{beds}</td>
      <td class="photo">{photo_html}</td>
      <td class="score {score_class}">{score}</td>
      <td class="expl">{expl}</td>
      <td class="link"><a href="{url}" target="_blank">открыть →</a></td>
    </tr>"""


def main():
    candidates = json.loads((RUN_DIR / "candidates_top100.json").read_text())
    by_id = {c["ad_id"]: c for c in candidates}

    scored = []
    for ad_id, rev in REVIEWS.items():
        if ad_id in by_id:
            scored.append((rev["score"], by_id[ad_id], rev))

    scored.sort(key=lambda x: x[0], reverse=True)
    top50 = scored[:50]

    rows = "\n".join(render_row(i + 1, cand, rev) for i, (_, cand, rev) in enumerate(top50))
    html_out = HTML_TEMPLATE.format(rows=rows)

    out_path = RUN_DIR / "index.html"
    out_path.write_text(html_out)
    print(f"Written: {out_path}")
    print(f"Scores: {[s for s, _, _ in top50]}")


if __name__ == "__main__":
    main()
