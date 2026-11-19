"""Write docs/seattle.html and docs/boston.html (same look as the NYC map) and copy their GeoJSON layers."""
import json, shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
# Inside the repository multi-city/ sits next to docs/; in the author's working folder it sits beside the repo copies.
REPOS = [r for r in (BASE.parent, BASE.parent / "GitHub-upload-nyc-landmark-decarbonization", BASE.parent / "nyc-landmark-decarbonization")
         if (r / "docs" / "index.html").exists()]

CITIES = {
 "seattle": dict(
  title="Seattle landmarks under BEPS", center=[47.612, -122.335], zoom=14,
  intro="Seattle landmarks and historic-district buildings covered by the Building Emissions Performance Standard, colored by whether their 2024 energy use would meet the emissions targets. District steam counted.",
  status={"over_2031": ["#d03b3b", "Over the 2031–2035 target"], "over_2036": ["#fab219", "Within 2031–35, over the 2036–2040 target"],
          "ok": ["#0ca30c", "Within both targets"], "exempt": ["#5aa9e6", "All-electric (exempt from targets)"]},
  order=["exempt", "ok", "over_2036", "over_2031"], fuel_filter="Only buildings on district steam",
  source='Data: Seattle Building Energy Benchmarking (2024), Seattle City Landmarks and Historic &amp; Special Review Districts. Targets and factors: OSE BEPS Director\'s Rule 2025-01 (provisional 2031–35 factors). Steam emissions can be deducted in 2031–35 only.',
  rows="""<tr><td>Designation</td><td>${p.group}${p.landmark ? ': ' + p.landmark : ''}${p.district ? ' (' + p.district + ')' : ''}</td></tr>
      <tr><td>Main use</td><td>${p.use ?? 'n/a'}</td></tr>
      <tr><td>Year built</td><td>${p.year_built ?? 'n/a'}</td></tr>
      <tr><td>Floor area</td><td>${fmt(p.gfa)} sq ft</td></tr>
      <tr><td>Heating fuel</td><td>${FUEL[p.fuel]}</td></tr>
      <tr><td>Emissions</td><td>${p.ghgi} kgCO₂e/sq ft${p.fuel === 'steam' ? ' (' + p.ghgi_ded + ' with steam deducted)' : ''}</td></tr>
      <tr><td>Target 2031–35</td><td>${p.t2031} kgCO₂e/sq ft</td></tr>
      <tr><td>Target 2036–40</td><td>${p.t2036} kgCO₂e/sq ft</td></tr>"""),
 "boston": dict(
  title="Boston landmarks under BERDO", center=[42.352, -71.068], zoom=14,
  intro="Boston landmarks and historic-district buildings covered by BERDO, colored by whether their 2024 emissions would meet the emissions standards.",
  status={"over_2025": ["#d03b3b", "Over the 2025–2029 standard"], "over_2030": ["#fab219", "Within 2025–29, over the 2030–2034 standard"],
          "ok": ["#0ca30c", "Within both standards"]},
  order=["ok", "over_2030", "over_2025"], fuel_filter="Only buildings on district steam or fuel oil",
  source="Data: BERDO disclosure (2024 energy use), Boston Landmarks Commission landmarks and districts, Parcels 2025. Standards: BERDO 2.0; 2030 grid factor from BERDO Policies &amp; Procedures, Appendix B.",
  rows="""<tr><td>Designation</td><td>${p.group}${p.landmark ? ': ' + p.landmark : ''}${p.district ? ' (' + p.district + ')' : ''}</td></tr>
      <tr><td>Main use</td><td>${p.use ?? 'n/a'}</td></tr>
      <tr><td>Floor area</td><td>${fmt(p.gfa)} sq ft</td></tr>
      <tr><td>Heating fuel</td><td>${FUEL[p.fuel]}</td></tr>
      <tr><td>Emissions 2024</td><td>${p.e2025} kgCO₂e/sq ft (est. ${p.e2030} in 2030)</td></tr>
      <tr><td>Standard 2025–29</td><td>${p.s2025} kgCO₂e/sq ft</td></tr>
      <tr><td>Standard 2030–34</td><td>${p.s2030} kgCO₂e/sq ft</td></tr>"""),
}

def switcher(cur):
    links = [("index.html", "New York", "nyc"), ("seattle.html", "Seattle", "seattle"), ("boston.html", "Boston", "boston")]
    return '<div class="cities">' + " · ".join(f"<b>{n}</b>" if k == cur else f'<a href="{h}">{n}</a>' for h, n, k in links) + "</div>"

def page(key, c, head_style, basemap_js):
    legend = "\n  ".join(f'<div class="legend-row"><span class="dot" style="background:{v[0]}"></span>{v[1]}</div>' for v in c["status"].values())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{c['title']}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.css">
{head_style}
</head>
<body>
<div id="map"></div>
<div class="panel">
  {switcher(key)}
  <h1>{c['title']}</h1>
  <p>{c['intro']}</p>
  {legend}
  <div class="legend-row"><span class="dot ring" style="background:#9a998f"></span>Larger, ringed dot: individual landmark</div>
  <div class="filters">
    <label><input type="checkbox" id="f-ind" checked> Individual landmarks</label>
    <label><input type="checkbox" id="f-hd" checked> Historic district buildings</label>
    <label><input type="checkbox" id="f-fossil"> {c['fuel_filter']}</label>
    <div class="counts" id="counts"></div>
  </div>
  <div class="source">
    {c['source']} Exposure assumes 2024 energy use does not change.
    <a href="https://github.com/tugesra/nyc-landmark-decarbonization">Method and code</a> · Esra Tug
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@maplibre/maplibre-gl-leaflet@0.1.4/dist/leaflet-maplibre-gl.js"></script>
<script>
const STATUS = {json.dumps({k: {"color": v[0], "label": v[1]} for k, v in c['status'].items()}, ensure_ascii=False)};
const ORDER = {json.dumps({k: i for i, k in enumerate(c['order'])})};
const FUEL = {{ steam: 'District steam', oil: 'Fuel oil', gas: 'Natural gas', 'all-electric': 'All-electric' }};
const map = L.map('map', {{ zoomControl: false }}).setView({json.dumps(c['center'])}, {c['zoom']});
L.control.zoom({{ position: 'topright' }}).addTo(map);
{basemap_js}
const fmt = n => n.toLocaleString('en-US');
function popup(p) {{
  const s = STATUS[p.status];
  return `<h3>${{p.name}}</h3>
    <div>${{p.address ?? ''}}</div>
    <div class="status" style="color:${{s.color === '#fab219' ? '#9a6a00' : s.color}}">● ${{s.label}}</div>
    <table>
      {c['rows']}
    </table>`;
}}
let all = [];
const layer = L.layerGroup().addTo(map);
function draw() {{
  const ind = document.getElementById('f-ind').checked, hd = document.getElementById('f-hd').checked, fossil = document.getElementById('f-fossil').checked;
  layer.clearLayers();
  const shown = all.filter(f => {{ const g = f.properties.group;
    return ((g === 'Individual landmark' && ind) || (g === 'Historic district' && hd)) && (!fossil || f.properties.steam); }})
    .sort((a, b) => ORDER[a.properties.status] - ORDER[b.properties.status]);
  const n = {{}};
  for (const f of shown) {{
    const p = f.properties, [lng, lat] = f.geometry.coordinates, isInd = p.group === 'Individual landmark';
    n[p.status] = (n[p.status] || 0) + 1;
    L.circleMarker([lat, lng], {{ radius: isInd ? 7 : 4.5, fillColor: STATUS[p.status].color, fillOpacity: 0.9,
      color: isInd ? '#f0efec' : '#1a1a19', weight: isInd ? 2 : 1 }}).bindPopup(popup(p)).addTo(layer);
  }}
  document.getElementById('counts').textContent = `${{fmt(shown.length)}} buildings: ` +
    Object.keys(STATUS).map(k => `${{n[k] || 0}} ${{STATUS[k].label.toLowerCase()}}`).join(', ');
}}
fetch('{key}_landmarks.geojson').then(r => r.json()).then(g => {{ all = g.features; draw(); }});
['f-ind', 'f-hd', 'f-fossil'].forEach(id => document.getElementById(id).addEventListener('change', draw));
</script>
<script data-goatcounter="https://esratug.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body>
</html>
"""

def main():
    nyc = (REPOS[0] / "docs" / "index.html").read_text(encoding="utf-8")
    style = nyc[nyc.index("<style>"): nyc.index("</style>") + len("</style>")]
    style = style.replace("  .panel h1 {", "  .cities { font-size: 12px; margin-bottom: 8px; color: #c3c2b7; }\n  .cities a { color: #9fc3f0; text-decoration: none; }\n  .panel h1 {")
    a = nyc.index("const CARTO_KEY"); b = nyc.index("const STATUS")      # API key + attribution lines
    m = nyc.index("// Slate blue-gray basemap"); z = nyc.index("const fmt")  # basemap colours + loader
    basemap = nyc[a:b] + nyc[m:z]
    for repo in REPOS:
        docs = repo / "docs"
        for key, c in CITIES.items():
            (docs / f"{key}.html").write_text(page(key, c, style, basemap), encoding="utf-8")
            shutil.copy(BASE / "outputs" / "map" / f"{key}_landmarks.geojson", docs / f"{key}_landmarks.geojson")
        print("wrote", docs)

if __name__ == "__main__":
    main()
