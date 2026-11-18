"""
LL97 exposure of NYC landmark and historic-district buildings.

Inputs (data/):
  ll84_selected.csv                    - extract of the LL84 benchmarking dataset (01_extract_ll84.py)
  ll97_limits_by_property_type.csv     - LL97 limits by ENERGY STAR property type (1 RCNY 103-14)
  ../Individual_Landmark_and_Historic_District_Building_Database.csv - LPC building database

Method:
  1. Keep calendar year 2024 (first LL97 compliance year), one row per property,
     standalone/parent properties only, with 12 months of data and floor area > 0;
     drop implausible site EUIs and duplicate reports of the same building.
  2. Recompute emissions with the LL97 coefficients for 2024-2029 and 2030-2034.
  3. Build each property's limit from its mix of property types and floor areas.
  4. Keep properties on the DOB LL97 Covered Buildings List under Article 320 from 2024 (pathway CP0).
  5. Flag properties whose BBL appears in the LPC database (individual landmark or
     historic district building).
  6. Estimate excess emissions and the maximum penalty ($268 per tCO2e).
"""
import re
import sys
import numpy as np
import pandas as pd

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
PENALTY = 268.0

# LL97 emission coefficients, tCO2e per unit (Admin Code 28-320.3.1.1; 1 RCNY 103-14(d)(3))
COEF = {
    '2024': {'elec_kwh': 0.000288962, 'gas': 0.00005311, 'oil2': 0.00007421, 'oil4': 0.00007529,
             'oil56': 0.00007529, 'steam': 0.00004493, 'diesel': 0.00007421, 'oil1': 0.0000735,
             'propane': 0.00006425, 'kerosene': 0.00007769},
    '2030': {'elec_kwh': 0.000145, 'gas': 0.00005311, 'oil2': 0.00007421, 'oil4': 0.00007529,
             'oil56': 0.00007529, 'steam': 0.0000432, 'diesel': 0.00007421, 'oil1': 0.0000735,
             'propane': 0.00006425, 'kerosene': 0.00007769},
}
FUEL_COLS = {
    'elec_kwh': 'Electricity Use - Grid Purchase (kWh)',
    'gas': 'Natural Gas Use (kBtu)', 'oil2': 'Fuel Oil #2 Use (kBtu)', 'oil4': 'Fuel Oil #4 Use (kBtu)',
    'oil56': 'Fuel Oil #5 & 6 Use (kBtu)', 'steam': 'District Steam Use (kBtu)',
    'diesel': 'Diesel #2 Use (kBtu)', 'oil1': 'Fuel Oil #1 Use (kBtu)',
    'propane': 'Propane Use (kBtu)', 'kerosene': 'Kerosene Use (kBtu)',
}
# ENERGY STAR type names in the LL84 data that are not in the LL97 limits table,
# mapped to the closest listed type (assumption; share of floor area reported below).
TYPE_MAP = {
    'COMMUNITY CENTER AND SOCIAL MEETING HALL': 'SOCIAL/MEETING HALL',
    'SENIOR LIVING COMMUNITY': 'SENIOR CARE COMMUNITY',
    'VEHICLE REPAIR SERVICES': 'REPAIR SERVICES (VEHICLE SHOE LOCKSMITH ETC.)',
    'FAST FOOD RESTAURANT': 'RESTAURANT',
    'BAR/NIGHTCLUB': 'OTHER - RESTAURANT/BAR',
    'VEHICLE DEALERSHIP': 'AUTOMOBILE DEALERSHIP',
    'HEATED SWIMMING POOL': 'OTHER - RECREATION',
    'ICE/CURLING RINK': 'OTHER - RECREATION',
    'ROLLER RINK': 'OTHER - RECREATION',
    'ZOO': 'OTHER - ENTERTAINMENT/PUBLIC ASSEMBLY',
    'AQUARIUM': 'OTHER - ENTERTAINMENT/PUBLIC ASSEMBLY',
    'CONVENTION CENTER': 'OTHER - ENTERTAINMENT/PUBLIC ASSEMBLY',
    'STADIUM (OPEN)': 'OTHER - ENTERTAINMENT/PUBLIC ASSEMBLY',
    'STADIUM (CLOSED)': 'OTHER - ENTERTAINMENT/PUBLIC ASSEMBLY',
    'OTHER - STADIUM': 'OTHER - ENTERTAINMENT/PUBLIC ASSEMBLY',
    'INDOOR ARENA': 'OTHER - ENTERTAINMENT/PUBLIC ASSEMBLY',
    'POLICE STATION': 'OTHER - PUBLIC SERVICES',
    'FIRE STATION': 'OTHER - PUBLIC SERVICES',
    'PRISON/INCARCERATION': 'OTHER - PUBLIC SERVICES',
    'VETERINARY OFFICE': 'OTHER - SERVICES',
    'OTHER': 'OTHER - SERVICES',
    'ELECTRIC VEHICLE CHARGING STATION': 'PARKING',
    'SINGLE-FAMILY HOME': 'MULTIFAMILY HOUSING',
    'PERSONAL SERVICES (HEALTH/BEAUTY, DRY CLEANING, ETC.)': 'PERSONAL SERVICES (HEALTH/BEAUTY DRY CLEANING ETC.)',
    'REPAIR SERVICES (VEHICLE, SHOE, LOCKSMITH, ETC.)': 'REPAIR SERVICES (VEHICLE SHOE LOCKSMITH ETC.)',
    'SUPERMARKET/GROCERY': 'SUPERMARKET/GROCERY STORE',
}
EXCLUDED_TYPES = {'ENERGY/POWER STATION', 'WASTEWATER TREATMENT PLANT', 'OTHER - UTILITY',
                  'DRINKING WATER TREATMENT & DISTRIBUTION'}


def num(s):
    return pd.to_numeric(s, errors='coerce')


def parse_uses(text):
    """'Office (1000.0), Retail Store (200.0)' -> [('OFFICE', 1000.0), ('RETAIL STORE', 200.0)]"""
    if not isinstance(text, str):
        return []
    out = []
    for name, gfa in re.findall(r'\s*(.+?) \(([\d.]+)\)(?:,|$)', text):
        out.append((name.strip().upper().replace('–', '-'), float(gfa)))
    return out


def bbls(value):
    return [b for b in re.findall(r'\d{10}', str(value))]


def main():
    limits = pd.read_csv('data/ll97_limits_by_property_type.csv').set_index('property_type')
    df = pd.read_csv('data/ll84_selected.csv', low_memory=False)
    n0 = len(df[df['Calendar Year'] == YEAR])
    df = df[df['Calendar Year'] == YEAR].copy()
    df = df[df['Parent Property ID'].astype(str).str.startswith('Not Applicable')]
    df = df.drop_duplicates('Property ID', keep='last')
    df['gfa'] = num(df['Property GFA - Self-Reported (ft²)'])
    df = df[df['gfa'] > 0]
    df = df[df['Alert - Energy Meter has less than 12 full calendar months of data'].astype(str) == 'Ok']
    df = df[df['Default Values'].astype(str) != 'True']
    for k, c in FUEL_COLS.items():
        df[k] = num(df[c]).fillna(0)
    df['site_eui'] = num(df['Site EUI (kBtu/ft²)'])
    # Plausibility filters (outlier review): site EUI below 10 kBtu/sf is almost always a reporting error;
    # above 500 kBtu/sf is only plausible for energy-intensive types.
    intensive = df['Largest Property Use Type'].astype(str).str.upper().isin(
        ['DATA CENTER', 'LABORATORY', 'HOSPITAL (GENERAL MEDICAL & SURGICAL)', 'SUPERMARKET/GROCERY STORE',
         'RESTAURANT', 'FOOD SERVICE', 'FOOD SALES', 'OTHER - SPECIALTY HOSPITAL', 'OTHER - TECHNOLOGY/SCIENCE'])
    upper = np.where(intensive, 1000, 500)
    df = df[(df['site_eui'] >= 10) & (df['site_eui'] <= upper)]
    # The same building is sometimes reported under two Property IDs: keep one per BBL and floor area.
    df = df.drop_duplicates(['NYC Borough, Block and Lot (BBL)', 'gfa'], keep='last')
    df['year_built'] = num(df['Year Built'])

    # Emissions under LL97 coefficients
    for p in ('2024', '2030'):
        df[f'em_{p}'] = sum(df[k] * COEF[p][k] for k in FUEL_COLS)

    # Limits from the property-use mix
    approx_gfa = 0.0
    total_gfa = 0.0
    lim24, lim30, keep = [], [], []
    for uses, gfa in zip(df['List of All Property Use Types (GFA) (ft²)'], df['gfa']):
        parsed = parse_uses(uses) or []
        parsed = [(t, a) for t, a in parsed if a > 0]
        if not parsed or any(t in EXCLUDED_TYPES for t, _ in parsed):
            lim24.append(np.nan); lim30.append(np.nan); keep.append(False); continue
        l24 = l30 = 0.0
        ok = True
        for t, a in parsed:
            total_gfa += a
            key = t if t in limits.index else TYPE_MAP.get(t)
            if key is None or key not in limits.index:
                ok = False; break
            if key != t:
                approx_gfa += a
            l24 += a * limits.loc[key, 'limit_2024_2029_kg_per_sf'] / 1000
            l30 += a * limits.loc[key, 'limit_2030_2034_kg_per_sf'] / 1000
        lim24.append(l24 if ok else np.nan); lim30.append(l30 if ok else np.nan); keep.append(ok)
    df['limit_2024'] = lim24
    df['limit_2030'] = lim30
    df = df[np.array(keep)]

    for p in ('2024', '2030'):
        df[f'excess_{p}'] = (df[f'em_{p}'] - df[f'limit_{p}']).clip(lower=0)
        df[f'over_{p}'] = df[f'excess_{p}'] > 0
        df[f'penalty_{p}'] = df[f'excess_{p}'] * PENALTY
    df['intensity_kg_sf'] = df['em_2024'] * 1000 / df['gfa']

    # Landmark flags
    lpc = pd.read_csv('../Individual_Landmark_and_Historic_District_Building_Database.csv',
                      usecols=['BBL', 'LM_NAME', 'HIST_DISTRICT', 'DATE_HIGH', 'STYLE1'], low_memory=False)
    lpc['BBL'] = num(lpc['BBL']).astype('Int64').astype(str)
    indiv = set(lpc.loc[~lpc['LM_NAME'].astype(str).isin(['0', 'nan']), 'BBL'])
    district = set(lpc.loc[~lpc['HIST_DISTRICT'].astype(str).isin(['0', 'nan']), 'BBL'])
    b = df['NYC Borough, Block and Lot (BBL)'].map(bbls)
    df['individual_landmark'] = b.map(lambda xs: any(x in indiv for x in xs))
    df['historic_district'] = b.map(lambda xs: any(x in district for x in xs))
    df['lpc_regulated'] = df['individual_landmark'] | df['historic_district']
    # LL97 compliance pathway from the DOB Covered Buildings List (filing year 2026)
    cbl = pd.read_csv('data/cbl26_pathway_by_bbl.csv', dtype=str).set_index('BBL')['pathway'].to_dict()
    df['ll97_pathways'] = b.map(lambda xs: ','.join(sorted({p for x in xs for p in str(cbl.get(x, '')).split(',') if p})))
    df['article_320_from_2024'] = df['ll97_pathways'].str.contains('0')
    df['group'] = np.where(df['individual_landmark'], 'Individual landmark',
                  np.where(df['historic_district'], 'Historic district', 'Not landmarked'))

    out_cols = ['Property ID', 'Property Name', 'NYC Borough, Block and Lot (BBL)', 'Address 1', 'Borough',
                'Largest Property Use Type', 'gfa', 'year_built', 'site_eui', 'ENERGY STAR Score',
                'em_2024', 'em_2030', 'limit_2024', 'limit_2030', 'excess_2024', 'excess_2030',
                'penalty_2024', 'penalty_2030', 'over_2024', 'over_2030', 'intensity_kg_sf',
                'individual_landmark', 'historic_district', 'group', 'll97_pathways', 'article_320_from_2024', 'Latitude', 'Longitude'] + list(FUEL_COLS)
    df[out_cols].to_csv(f'outputs/buildings_ll97_{YEAR}.csv', index=False)

    def summary(g):
        return pd.Series({
            'properties': len(g),
            'floor_area_msf': g['gfa'].sum() / 1e6,
            'median_site_eui': g['site_eui'].median(),
            'median_intensity_kg_sf': g['intensity_kg_sf'].median(),
            'pct_over_2024': 100 * g['over_2024'].mean(),
            'pct_over_2030': 100 * g['over_2030'].mean(),
            'max_penalty_2024_musd': g['penalty_2024'].sum() / 1e6,
            'max_penalty_2030_musd': g['penalty_2030'].sum() / 1e6,
            'pct_properties_using_steam_or_oil': 100 * ((g['steam'] + g['oil2'] + g['oil4'] + g['oil56']) > 0).mean(),
        })
    print('Pathways (all cleaned properties):', df['ll97_pathways'].replace('', 'not on CBL').value_counts().head(8).to_dict())
    df_all = df
    df = df[df['article_320_from_2024']].copy()
    print(f'Article 320 (CP0) properties analysed: {len(df)}')
    s = df.groupby('group').apply(summary, include_groups=False).round(2)
    s.loc['All'] = summary(df).round(2)
    s.to_csv(f'outputs/summary_by_group_{YEAR}_article320.csv')
    s_all = df_all.groupby('group').apply(summary, include_groups=False).round(2)
    s_all.loc['All'] = summary(df_all).round(2)
    s_all.to_csv(f'outputs/summary_by_group_{YEAR}_all_properties.csv')
    print(f'Calendar year {YEAR}: {n0} rows -> {len(df)} properties after cleaning')
    print(f'Floor area mapped to a near-match property type: {100*approx_gfa/total_gfa:.1f}%')
    print(s.T.to_string())

    lm = df[df['lpc_regulated']]
    t = lm.groupby('Largest Property Use Type').apply(summary, include_groups=False)
    t = t[t['properties'] >= 15].sort_values('properties', ascending=False).round(2)
    t.to_csv(f'outputs/landmarks_by_type_{YEAR}_article320.csv')
    print(t[['properties', 'median_intensity_kg_sf', 'pct_over_2024', 'pct_over_2030', 'max_penalty_2030_musd']].head(12).to_string())


if __name__ == '__main__':
    main()
