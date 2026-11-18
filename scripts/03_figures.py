"""Figures for the README (calendar year 2024, Article 320 buildings)."""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
S1, S2 = '#2a78d6', '#eb6834'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.edgecolor': GRID,
                     'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                     'figure.facecolor': SURF, 'axes.facecolor': SURF})

d = pd.read_csv('outputs/buildings_ll97_2024.csv')
d = d[d.in_analysis]
d['fossil'] = (d.steam + d.oil2 + d.oil4 + d.oil56) > 0
order = ['Individual landmark', 'Historic district', 'Not landmarked']
n = d.group.value_counts()
labels = [f'{g}\n(n={n[g]:,})' for g in order]
g = d.groupby('group').agg(o24=('over_2024', 'mean'), o30=('over_2030', 'mean'), fos=('fossil', 'mean')).loc[order] * 100


def style(ax, title):
    ax.set_title(title, loc='left', color=INK, fontsize=13, fontweight='bold', pad=14)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def label(ax, bars, vals):
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f'{v:.0f}%', ha='center',
                va='bottom', color=INK, fontsize=10)


# Figure 1: share over the LL97 limits
fig, ax = plt.subplots(figsize=(8, 4.6))
x = range(len(order)); w = 0.36
b1 = ax.bar([i - w / 2 - 0.01 for i in x], g.o24, w, color=S1, label='2024-2029 limits')
b2 = ax.bar([i + w / 2 + 0.01 for i in x], g.o30, w, color=S2, label='2030-2034 limits')
label(ax, b1, g.o24); label(ax, b2, g.o30)
ax.set_xticks(list(x)); ax.set_xticklabels(labels)
ax.set_ylabel('Buildings over the limit (%)'); ax.set_ylim(0, 75)
ax.legend(frameon=False, loc='upper right', labelcolor=INK)
style(ax, 'Individual landmarks exceed LL97 limits more often')
fig.text(0.01, 0.01, 'NYC Article 320 buildings, 2024 energy use. Sources: LL84, LPC, DOB Covered Buildings List.',
         color=INK2, fontsize=8.5)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig('figures/fig1_over_limits.png', dpi=200); plt.close(fig)

# Figure 2: steam or oil use
fig, ax = plt.subplots(figsize=(8, 4.2))
b = ax.bar(list(x), g.fos, 0.5, color=S1)
label(ax, b, g.fos)
ax.set_xticks(list(x)); ax.set_xticklabels(labels)
ax.set_ylabel('Buildings using district steam or fuel oil (%)'); ax.set_ylim(0, 60)
style(ax, 'Half of individual landmarks still rely on steam or oil')
fig.text(0.01, 0.01, 'NYC Article 320 buildings, 2024 energy use. Sources: LL84, LPC, DOB Covered Buildings List.',
         color=INK2, fontsize=8.5)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig('figures/fig2_steam_oil.png', dpi=200); plt.close(fig)

# Figure 3: 2030 exposure by fuel
f = d.groupby('fossil').agg(o24=('over_2024', 'mean'), o30=('over_2030', 'mean')).sort_index() * 100
v24, v30 = f.o24.tolist(), f.o30.tolist()  # [no steam/oil, steam/oil]
nf = d.fossil.value_counts()
fl = [f'No steam or oil\n(n={nf[False]:,})', f'Uses steam or oil\n(n={nf[True]:,})']
fig, ax = plt.subplots(figsize=(7, 4.4))
xx = [0, 1]
c1 = ax.bar([i - w / 2 - 0.01 for i in xx], v24, w, color=S1, label='2024-2029 limits')
c2 = ax.bar([i + w / 2 + 0.01 for i in xx], v30, w, color=S2, label='2030-2034 limits')
label(ax, c1, v24); label(ax, c2, v30)
ax.set_xticks(xx); ax.set_xticklabels(fl)
ax.set_ylabel('Buildings over the limit (%)'); ax.set_ylim(0, 90)
ax.legend(frameon=False, loc='upper left', ncol=2, labelcolor=INK)
style(ax, 'In 2030, steam and oil buildings fall behind')
fig.text(0.01, 0.01, 'All NYC Article 320 buildings, 2024 energy use. Sources: LL84, DOB Covered Buildings List.',
         color=INK2, fontsize=8.5)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig('figures/fig3_fuel_2030.png', dpi=200); plt.close(fig)
print(g.round(1)); print(f.round(1))
