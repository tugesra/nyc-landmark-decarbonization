"""Export landmark buildings (Article 320, calendar year 2024) as GeoJSON for the web map."""
import json
import pandas as pd

d = pd.read_csv('outputs/buildings_ll97_2024.csv')
d = d[d.article_320_from_2024 & (d.group != 'Not landmarked')].dropna(subset=['Latitude', 'Longitude'])
d['fossil'] = (d.steam + d.oil2 + d.oil4 + d.oil56) > 0
d['status'] = d.apply(lambda r: 'over_2024' if r.over_2024 else ('over_2030' if r.over_2030 else 'ok_2034'), axis=1)
feats = []
for _, r in d.iterrows():
    fuels = [n for n, c in [('electricity', r.elec_kwh), ('natural gas', r.gas), ('district steam', r.steam),
                            ('fuel oil', r.oil2 + r.oil4 + r.oil56)] if c > 0]
    feats.append({'type': 'Feature',
                  'geometry': {'type': 'Point', 'coordinates': [round(r.Longitude, 6), round(r.Latitude, 6)]},
                  'properties': {
                      'name': str(r['Property Name']), 'address': str(r['Address 1']),
                      'type': str(r['Largest Property Use Type']), 'group': r.group,
                      'year_built': None if pd.isna(r.year_built) else int(r.year_built),
                      'gfa': int(r.gfa), 'status': r.status, 'fossil': bool(r.fossil), 'fuels': ', '.join(fuels),
                      'intensity': round(r.intensity_kg_sf, 2),
                      'limit24': round(r.limit_2024 * 1000 / r.gfa, 2), 'limit30': round(r.limit_2030 * 1000 / r.gfa, 2),
                      'penalty24': int(round(r.penalty_2024)), 'penalty30': int(round(r.penalty_2030))}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open('docs/landmarks_ll97_2024.geojson', 'w'),
          separators=(',', ':'))
print(len(feats), d.status.value_counts().to_dict(), d.group.value_counts().to_dict())
