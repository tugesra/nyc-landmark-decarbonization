"""Case study: New York Public Library buildings in the 2024 LL84 data.

NYPL buildings are city-owned and follow the LL97 city portfolio requirements, not the
building-by-building limits. This compares them with the limits a private library of the
same size would face, to show which buildings are closest to 2030-level performance.
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
ELEC, FOSSIL = '#2a78d6', '#eb6834'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'figure.facecolor': SURF,
                     'axes.facecolor': SURF, 'axes.edgecolor': GRID, 'xtick.color': INK2, 'ytick.color': INK})

d = pd.read_csv('outputs/buildings_ll97_2024.csv')
n = d[d['Property Name'].astype(str).str.startswith('NYPL_')].copy()
n['building'] = n['Property Name'].str.replace(r'^NYPL_\d+_', '', regex=True).str.replace('Schwartzman', 'Schwarzman')
n['all_electric'] = (n.gas + n.steam + n.oil2 + n.oil4 + n.oil56) == 0
n['uses_steam'] = n.steam > 0
n['limit_2024_kg_sf'] = n.limit_2024 * 1000 / n.gfa
n['limit_2030_kg_sf'] = n.limit_2030 * 1000 / n.gfa
n['landmark'] = n.group.ne('Not landmarked')
n['intensity_2030_basis'] = n.em_2030 * 1000 / n.gfa  # same energy use, 2030-34 emission factors
cols = ['building', 'group', 'Largest Property Use Type', 'gfa', 'year_built', 'all_electric', 'uses_steam',
        'intensity_kg_sf', 'intensity_2030_basis', 'limit_2024_kg_sf', 'limit_2030_kg_sf', 'over_2024', 'over_2030']
n[cols].sort_values('intensity_kg_sf').round(2).to_csv('outputs/nypl_buildings_2024.csv', index=False)

print('buildings:', len(n), '| landmarked:', n.landmark.sum(), '| all-electric:', n.all_electric.sum())
print(n.groupby('all_electric').agg(k=('gfa', 'size'), within_2030=('over_2030', lambda s: (~s).sum()),
                                    median_2030_basis=('intensity_2030_basis', 'median')))
print('all-electric buildings:', n[n.all_electric][['building', 'group', 'year_built', 'intensity_kg_sf']].to_string())

# Figure: one dot per building, sorted by emissions intensity
lib = n[n['Largest Property Use Type'] == 'Library'].sort_values('intensity_2030_basis')
fig, ax = plt.subplots(figsize=(8.5, 9.5))
y = range(len(lib))
ax.scatter(lib.intensity_2030_basis, list(y), s=46, zorder=3,
           c=[ELEC if e else FOSSIL for e in lib.all_electric], edgecolors=SURF, linewidths=1)
for lim, lab in [(2.22, '2030–34 limit\nfor a library (2.22)')]:
    ax.axvline(lim, color=INK2, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    ax.text(lim + 0.1, len(lib) - 0.3, lab, color=INK2, fontsize=9, va='top')
ax.set_yticks(list(y))
ax.set_yticklabels([f'{b}{"  ★" if l else ""}' for b, l in zip(lib.building, lib.landmark)], fontsize=8.5)
ax.set_xlabel('kgCO₂e per sq ft: 2024 energy use, 2030–34 LL97 emission factors', color=INK2)
ax.set_xlim(0, 10)
ax.xaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
for s in ('top', 'right', 'left'):
    ax.spines[s].set_visible(False)
ax.tick_params(length=0)
ax.scatter([], [], c=ELEC, s=46, label='All-electric')
ax.scatter([], [], c=FOSSIL, s=46, label='Uses natural gas or district steam')
ax.legend(frameon=False, loc='lower right', fontsize=9.5)
fos = lib[~lib.all_electric]
title = (f'Every all-electric NYPL library already meets the 2030 limit\na private library would face; '
         f'{fos.over_2030.sum()} of {len(fos)} using gas or steam do not')
print(title)
fig.text(0.01, 0.985, title,
         color=INK, fontsize=12.5, fontweight='bold', va='top', ha='left')
fig.text(0.01, 0.006, '★ landmark or historic district building. NYPL buildings follow the LL97 city portfolio path;\n'
         'the limit shown is the one for a private library (1 RCNY 103-14). Source: LL84 benchmarking, 2024.',
         color=INK2, fontsize=7.8)
fig.tight_layout(rect=(0, 0.035, 1, 0.93))
fig.savefig('figures/fig4_nypl_libraries.png', dpi=200)
