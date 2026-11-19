"""Case study: New York Public Library buildings in the 2024 LL84 data.

NYPL buildings are city-owned and follow the LL97 city portfolio requirements, not the
building-by-building limits. This compares them with the limits a private library of the
same size would face.

Fuel check (v2, 19 Nov 2026): LL84 reports a missing fuel as "Not Available", which script 02
reads as zero. A building with no fossil fuel in 2024 is therefore only counted as electric-only
if it also reports no fossil fuel in 2022, 2023 and 2025. Buildings with no fossil fuel in 2024
but fossil fuel in another year are flagged as "fuel data incomplete": their 2024 emissions are
understated.
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
ELEC, FOSSIL, MISSING = '#2a78d6', '#eb6834', '#8a8984'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'figure.facecolor': SURF,
                     'axes.facecolor': SURF, 'axes.edgecolor': GRID, 'xtick.color': INK2, 'ytick.color': INK})

FOSSIL_COLS = ['Natural Gas Use (kBtu)', 'District Steam Use (kBtu)', 'Fuel Oil #1 Use (kBtu)',
               'Fuel Oil #2 Use (kBtu)', 'Fuel Oil #4 Use (kBtu)', 'Fuel Oil #5 & 6 Use (kBtu)',
               'Diesel #2 Use (kBtu)', 'Propane Use (kBtu)', 'Kerosene Use (kBtu)']

d = pd.read_csv('outputs/buildings_ll97_2024.csv')
n = d[d['Property Name'].astype(str).str.startswith('NYPL_')].copy()
n['building'] = n['Property Name'].str.replace(r'^NYPL_\d+_', '', regex=True).str.replace('Schwartzman', 'Schwarzman').str.replace('Starvos', 'Stavros')
fos24 = n[['gas', 'steam', 'oil1', 'oil2', 'oil4', 'oil56', 'diesel', 'propane', 'kerosene']].sum(axis=1)
n['fossil_2024'] = fos24 > 0
n['uses_steam'] = n.steam > 0

# Fossil fuel reported in other years (2022, 2023, 2025) for the same Property ID
raw = pd.read_csv('data/ll84_selected.csv', low_memory=False, usecols=['Calendar Year', 'Property ID'] + FOSSIL_COLS)
raw = raw[raw['Calendar Year'].isin([2022, 2023, 2025])].drop_duplicates(['Calendar Year', 'Property ID'], keep='last')
raw['fossil'] = raw[FOSSIL_COLS].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
other = raw.groupby('Property ID').fossil.max()
n['fossil_other_years'] = n['Property ID'].map(other).fillna(0) > 0
n['fuel_status'] = 'fossil fuel reported'
n.loc[~n.fossil_2024 & n.fossil_other_years, 'fuel_status'] = 'fuel data incomplete'
n.loc[~n.fossil_2024 & ~n.fossil_other_years, 'fuel_status'] = 'no fossil fuel 2022-2025'
n['all_electric'] = n.fuel_status == 'no fossil fuel 2022-2025'

n['limit_2024_kg_sf'] = n.limit_2024 * 1000 / n.gfa
n['limit_2030_kg_sf'] = n.limit_2030 * 1000 / n.gfa
n['landmark'] = n.group.ne('Not landmarked')
n['intensity_2030_basis'] = n.em_2030 * 1000 / n.gfa  # same energy use, 2030-34 emission factors
cols = ['building', 'group', 'Largest Property Use Type', 'gfa', 'year_built', 'fuel_status', 'all_electric',
        'uses_steam', 'intensity_kg_sf', 'intensity_2030_basis', 'limit_2024_kg_sf', 'limit_2030_kg_sf',
        'over_2024', 'over_2030']
n[cols].sort_values('intensity_kg_sf').round(2).to_csv('outputs/nypl_buildings_2024.csv', index=False)

print('buildings:', len(n), '| landmarked:', n.landmark.sum())
print(n.groupby('fuel_status').agg(k=('gfa', 'size'), landmarks=('landmark', 'sum'),
                                   over_2030=('over_2030', 'sum')))
print(n[n.fuel_status != 'fossil fuel reported'][['building', 'group', 'year_built', 'fuel_status',
                                                  'intensity_2030_basis']].to_string())

# Figure: one dot per library, sorted by emissions intensity
lib = n[n['Largest Property Use Type'] == 'Library'].sort_values('intensity_2030_basis')
fos = lib[lib.fuel_status == 'fossil fuel reported']
inc = lib[lib.fuel_status == 'fuel data incomplete']
fig, ax = plt.subplots(figsize=(8.5, 9.5))
pos = {b: i for i, b in enumerate(lib.building)}
style = {'fossil fuel reported': dict(c=FOSSIL, edgecolors=SURF),
         'fuel data incomplete': dict(facecolors='none', edgecolors=MISSING, linewidths=1.6),
         'no fossil fuel 2022-2025': dict(c=ELEC, edgecolors=SURF)}
labels = {'fossil fuel reported': 'Gas or steam reported in 2024',
          'fuel data incomplete': 'No fossil fuel in 2024 but in other years\n(fuel data incomplete; emissions understated)',
          'no fossil fuel 2022-2025': 'No fossil fuel reported, 2022–2025'}
for s, g in lib.groupby('fuel_status'):
    ax.scatter(g.intensity_2030_basis, [pos[b] for b in g.building], s=46, zorder=3, label=labels[s], **style[s])
ax.axvline(2.22, color=INK2, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
ax.text(2.32, len(lib) - 0.3, '2030–34 limit\nfor a library (2.22)', color=INK2, fontsize=9, va='top')
ax.set_yticks(range(len(lib)))
ax.set_yticklabels([f'{b}{"  ★" if l else ""}' for b, l in zip(lib.building, lib.landmark)], fontsize=8.5)
ax.set_xlabel('kgCO₂e per sq ft: 2024 energy use, 2030–34 LL97 emission factors', color=INK2)
ax.set_xlim(0, 10)
ax.xaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
for s in ('top', 'right', 'left'):
    ax.spines[s].set_visible(False)
ax.tick_params(length=0)
h, l = ax.get_legend_handles_labels()
order = [labels[k] for k in ['fossil fuel reported', 'fuel data incomplete', 'no fossil fuel 2022-2025'] if labels[k] in l]
ax.legend([h[l.index(o)] for o in order], order, frameon=False, loc='lower right', fontsize=8.5, borderpad=0.4)
title = (f'{fos.over_2030.sum()} of {len(fos)} NYPL libraries reporting gas or steam exceed the\n'
         f'2030 limit a private library would face; {len(inc)} more have incomplete fuel data')
print(title)
fig.text(0.01, 0.985, title, color=INK, fontsize=12.5, fontweight='bold', va='top', ha='left')
fig.text(0.01, 0.006, '★ landmark or historic district building. NYPL buildings follow the LL97 city portfolio path;\n'
         'the limit shown is the one for a private library (1 RCNY 103-14). Source: LL84 benchmarking, 2022–2025.',
         color=INK2, fontsize=7.8)
fig.tight_layout(rect=(0, 0.035, 1, 0.93))
fig.savefig('figures/fig4_nypl_libraries.png', dpi=200)
