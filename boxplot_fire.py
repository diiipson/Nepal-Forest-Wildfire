import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

df = pd.read_csv(r'S:\viirs\fire_daily_2021_2024.csv', parse_dates=['date'])
mam = df[df['month'].isin([3, 4, 5])].copy()
mam['month_name'] = mam['month'].map({3: 'March', 4: 'April', 5: 'May'})

years = sorted(mam['year'].unique())
month_names = ['March', 'April', 'May']
colors = {'March': '#7fbfff', 'April': '#ff9955', 'May': '#77dd77'}

# Print skewness table for caption
print('Skewness (for caption):')
print(f"{'Year':<6} {'March':>8} {'April':>8} {'May':>8}")
for yr in years:
    yr_data = mam[mam['year'] == yr]
    row = [stats.skew(yr_data[yr_data['month_name'] == m]['fire_count_daily'].values)
           for m in month_names]
    print(f"{yr:<6} {row[0]:>8.2f} {row[1]:>8.2f} {row[2]:>8.2f}")

fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
fig.patch.set_facecolor('white')
axes_flat = axes.flatten()

for i, yr in enumerate(years):
    ax = axes_flat[i]
    yr_data = mam[mam['year'] == yr]

    data_by_month = [yr_data[yr_data['month_name'] == m]['fire_count_daily'].values
                     for m in month_names]

    bp = ax.boxplot(data_by_month, patch_artist=True, widths=0.55,
                    medianprops=dict(color='black', linewidth=2.5),
                    whiskerprops=dict(linewidth=1.4),
                    capprops=dict(linewidth=1.4),
                    flierprops=dict(marker='o', markersize=3.5, alpha=0.5,
                                    markerfacecolor='gray', markeredgecolor='gray',
                                    linestyle='none'))

    for patch, m in zip(bp['boxes'], month_names):
        patch.set_facecolor(colors[m])
        patch.set_alpha(0.8)

    ax.set_title(str(yr), fontsize=12, fontweight='bold', pad=6)
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(month_names, fontsize=10)
    ax.set_ylabel('Daily Fire Count per Cluster', fontsize=10)
    ax.tick_params(axis='both', labelsize=10)
    ax.yaxis.set_tick_params(labelleft=True)

plt.tight_layout()
out = r'S:\viirs\pictures\sample\fire_count_boxplot_by_year.png'
plt.savefig(out, dpi=300, bbox_inches='tight')
plt.show()
print('Saved:', out)
