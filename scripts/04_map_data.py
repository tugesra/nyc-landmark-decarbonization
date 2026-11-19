"""Export landmark buildings (Article 320, calendar year 2024) as GeoJSON for the web map."""
import json
import pandas as pd

d = pd.read_csv('outputs/buildings_ll97_2024.csv')
d = d[d.in_analysis & (d.group != 'Not landmarked')].dropna(subset=['Latitude', 'Longitude'])
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
                      'intensity30': round(r.em_2030 * 1000 / r.gfa, 2),  # same 2024 energy use, 2030-2034 emission factors
                      'limit24': round(r.limit_2024 * 1000 / r.gfa, 2), 'limit30': round(r.limit_2030 * 1000 / r.gfa, 2),
                      'penalty24': int(round(r.penalty_2024)), 'penalty30': int(round(r.penalty_2030))}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open('docs/landmarks_ll97_2024.geojson', 'w'),
          separators=(',', ':'))
print(len(feats), d.status.value_counts().to_dict(), d.group.value_counts().to_dict())


# ---------------------------------------------------------------------------
# Other LL97-covered landmark lots (grey points): covered by LL97 but not in the
# Article 320 analysis above (other compliance path, or no usable 2024 report).
import re
import numpy as np

PATH_LABEL = {
    '1': 'Rent-regulated housing: LL97 limits start in 2026',
    '2': 'Income-restricted housing: LL97 limits start in 2035',
    '3': 'Article 321 (houses of worship, some affordable housing): one-time requirements',
    '4': 'City-owned: covered by the city portfolio requirements',
    '0': 'Covered from 2024, but no usable 2024 energy report',
}

lpc = pd.read_csv('../Individual_Landmark_and_Historic_District_Building_Database.csv',
                  usecols=['the_geom', 'BBL', 'DESIG_ADDRESS', 'LM_NAME', 'HIST_DISTRICT', 'DATE_HIGH'], low_memory=False)
lpc['BBL'] = pd.to_numeric(lpc['BBL'], errors='coerce').astype('Int64').astype(str)
cbl = pd.read_csv('data/cbl26_pathway_by_bbl.csv', dtype=str).set_index('BBL')['pathway'].to_dict()
on_map = set(b for v in d['NYC Borough, Block and Lot (BBL)'].astype(str) for b in re.findall(r'\d{10}', v))


def centroid(wkt):
    nums = re.findall(r'(-?\d+\.\d+) (-?\d+\.\d+)', str(wkt))
    if not nums:
        return None
    a = np.array(nums, dtype=float)
    return round(a[:, 0].mean(), 6), round(a[:, 1].mean(), 6)


other = []
for bbl, g in lpc[lpc['BBL'].isin(cbl.keys())].groupby('BBL'):
    if bbl in on_map:
        continue
    paths = cbl[bbl].split(',')
    key = next((p for p in ['4', '3', '1', '2'] if p in paths), '0')
    pt = centroid(g['the_geom'].iloc[0])
    if pt is None:
        continue
    names = [n for n in g['LM_NAME'].astype(str) if n not in ('0', 'nan')]
    districts = [h for h in g['HIST_DISTRICT'].astype(str) if h not in ('0', 'nan')]
    other.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': list(pt)},
                  'properties': {'name': names[0] if names else str(g['DESIG_ADDRESS'].iloc[0]),
                                 'address': str(g['DESIG_ADDRESS'].iloc[0]),
                                 'group': 'Individual landmark' if names else 'Historic district',
                                 'district': districts[0] if districts else '',
                                 'path': PATH_LABEL[key], 'path_code': key}})
json.dump({'type': 'FeatureCollection', 'features': other}, open('docs/landmarks_other_ll97.geojson', 'w'),
          separators=(',', ':'))
print('other covered landmark lots:', len(other),
      pd.Series([f['properties']['path_code'] for f in other]).value_counts().to_dict())
