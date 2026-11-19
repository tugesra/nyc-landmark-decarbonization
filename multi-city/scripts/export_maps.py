"""Build map layers (GeoJSON) for Seattle and Boston from the analysis outputs.
Only landmarks and historic-district buildings with usable data and known fuel are exported."""
import json, math
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs" / "map"
OUT.mkdir(parents=True, exist_ok=True)
r2 = lambda v: None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), 2)
clean = lambda v: None if v is None or (isinstance(v, float) and math.isnan(v)) else v

def write(name, feats):
    json.dump({"type": "FeatureCollection", "features": feats}, open(OUT / name, "w"), separators=(",", ":"))
    print(name, len(feats))

s = pd.read_csv(BASE / "outputs" / "seattle_buildings_2024.csv")
s = s[s.valid & (s.fuel != "incomplete") & s.group.isin(["landmark", "district"]) & s.lat.notna()]
feats = []
for _, r in s.iterrows():
    status = "exempt" if r.fuel == "all-electric" else "over_2031" if r.over_2031 else "over_2036" if r.over_2036 else "ok"
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(r.lon, 6), round(r.lat, 6)]},
        "properties": {"name": str(r["name"]).title(), "address": clean(r.address), "group": "Individual landmark" if r.group == "landmark" else "Historic district",
            "landmark": clean(r.landmark), "district": clean(r.district), "use": clean(r.use), "activity": r.activity,
            "year_built": None if pd.isna(r.year_built) else int(r.year_built), "gfa": int(r.gfa), "fuel": r.fuel,
            "ghgi": r2(r.ghgi), "ghgi_ded": r2(r.ghgi_steam_deducted), "t2031": r2(r.target_2031), "t2036": r2(r.target_2036),
            "status": status, "steam": r.fuel == "steam"}})
write("seattle_landmarks.geojson", feats)

b = pd.read_csv(BASE / "outputs" / "boston_buildings_2024data.csv")
b = b[b.valid & (b.fuel != "incomplete") & b.group.isin(["landmark", "district"]) & b.lat.notna() & b.std_2030.notna()]
feats = []
for _, r in b.iterrows():
    status = "over_2025" if r.over_2025 else "over_2030" if r.over_2030 else "ok"
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(r.lon, 6), round(r.lat, 6)]},
        "properties": {"name": clean(r.landmark) or clean(r.address), "address": clean(r.address),
            "group": "Individual landmark" if r.group == "landmark" else "Historic district",
            "landmark": clean(r.landmark), "district": clean(r.district), "use": clean(r.use), "gfa": int(r.gfa), "fuel": r.fuel,
            "e2025": r2(r.ei_2025), "e2030": r2(r.ei_2030), "s2025": r2(r.std_2025), "s2030": r2(r.std_2030),
            "status": status, "steam": r.fuel in ("steam", "oil")}})
write("boston_landmarks.geojson", feats)
