"""Reproduce descriptive ERA5 tables, figures, and an offline location explorer."""
import argparse
import json
import os
from pathlib import Path
import tempfile

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'era5-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd
import shapefile

ROOT = Path(__file__).resolve().parents[1]


def load_monthly(root):
    from package_monthly import sha256
    folder = root / 'data/monthly'
    manifest = json.loads((folder / 'manifest.json').read_text())
    frames = []
    for entry in manifest['parts']:
        path = folder / entry['file']
        if sha256(path) != entry['sha256']:
            raise ValueError(f'Checksum mismatch: {path}')
        frame = pd.read_csv(path)
        if len(frame) != entry['rows']:
            raise ValueError(f'Row count mismatch: {path}')
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    coords = df.iloc[:, 0].str.extract(r'^\(\s*([-\d.]+),\s*([-\d.]+)\s*\)$').astype(float).to_numpy()
    dates = pd.to_datetime(df.columns[1:], format='%Y-%m')
    values = df.iloc[:, 1:].to_numpy(dtype=float)
    if not np.isfinite(coords).all() or not np.isfinite(values).all():
        raise ValueError('Missing/nonfinite values require an explicit missing-data policy')
    if pd.DataFrame(coords).duplicated().any() or dates.duplicated().any():
        raise ValueError('Duplicate locations or months')
    if not dates.equals(pd.date_range(dates.min(), dates.max(), freq='MS')):
        raise ValueError('Monthly timestamps are not contiguous and sorted')
    if len(np.unique(coords[:, 0])) * len(np.unique(coords[:, 1])) != len(coords):
        raise ValueError('Expected a complete regular rectangular grid')
    return df, coords, dates, values


def build(root):
    df, coords, dates, values = load_monthly(root)
    figures = root / 'figures'
    tables = root / 'data/derived'
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    years = np.array([y for y in np.unique(dates.year) if sum(dates.year == y) == 12])
    annual = np.column_stack([values[:, dates.year == y].mean(axis=1) for y in years])
    # Equal-month aggregation intentionally matches the supplied workbook.
    annual_table = pd.DataFrame(annual, columns=years)
    annual_table.insert(0, 'Latitude_Longitude', df.iloc[:, 0])
    annual_table.to_csv(tables / 'annual_temperature.csv.gz', index=False, float_format='%.10f',
                        compression={'method': 'gzip', 'mtime': 0})
    weights = np.cos(np.deg2rad(coords[:, 0]))
    weighted_monthly = np.average(values, axis=0, weights=weights)
    equal_monthly = values.mean(axis=0)
    base = (dates.year >= 1961) & (dates.year <= 1990)
    if sum(base) != 360:
        raise ValueError('Expected all 360 months in the 1961–1990 baseline')
    climate = np.array([weighted_monthly[base & (dates.month == m)].mean() for m in range(1, 13)])
    monthly_anomaly = weighted_monthly - climate[dates.month - 1]
    pd.DataFrame(dict(month=dates.strftime('%Y-%m'), equal_grid_C=equal_monthly,
                      latitude_weighted_C=weighted_monthly, weighted_anomaly_C=monthly_anomaly)).to_csv(
                          tables / 'domain_monthly.csv', index=False)
    mean = np.average(annual, axis=0, weights=weights)
    equal = annual.mean(axis=0)
    baseline = annual[:, (years >= 1961) & (years <= 1990)].mean(axis=1)
    anomalies = annual - baseline[:, None]
    anomaly = np.average(anomalies, axis=0, weights=weights)
    x = years - years.mean()
    slope = (annual @ x) / (x @ x) * 10
    domain_slope = float(np.dot(mean, x) / (x @ x) * 10)
    pd.DataFrame(dict(year=years, equal_grid_C=equal, latitude_weighted_C=mean,
                      weighted_anomaly_C=anomaly)).to_csv(tables / 'domain_annual.csv', index=False)
    recent = annual[:, (years >= 1996) & (years <= 2025)].mean(axis=1)
    climatology = annual[:, (years >= 1991) & (years <= 2020)].mean(axis=1)
    pd.DataFrame(dict(latitude=coords[:, 0], longitude=coords[:, 1],
                      mean_1991_2020_C=climatology, change_1996_2025_vs_1961_1990_C=recent-baseline,
                      slope_C_per_decade=slope)).to_csv(tables / 'grid_summary.csv', index=False)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.facecolor': 'white', 'axes.titlesize': 13})

    def save(fig, name):
        fig.text(.01, -.025, 'Source: ERA5 daily 17:00 UTC samples; annual values are equal-month means. Domain includes land and ocean.',
                 fontsize=8, color='#536879')
        fig.savefig(figures / f'{name}.png', dpi=165, bbox_inches='tight')
        fig.savefig(figures / f'{name}.svg', bbox_inches='tight')
        plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), layout='constrained', sharex=True)
    axes[0].plot(years, mean, color='#166b8f', label='Latitude-weighted domain mean')
    axes[0].plot(years, equal, color='#b77923', alpha=.85, label='Equal-grid mean (original method)')
    axes[0].plot(years, mean.mean() + x * domain_slope / 10, '--', color='#bb3b44',
                 label=f'Weighted linear trend: {domain_slope:+.3f} °C/decade')
    axes[0].set(title='Annual 2 m air temperature across the supplied domain', ylabel='Temperature (°C)')
    axes[0].legend(fontsize=9)
    axes[1].bar(years, anomaly, color=np.where(anomaly >= 0, '#bb3b44', '#287fa1'), width=.9)
    axes[1].plot(years, pd.Series(anomaly).rolling(10, center=True, min_periods=10).mean(),
                 color='#222222', lw=2, label='Centered 10-year mean (complete windows)')
    axes[1].axhline(0, color='#333333', lw=.6)
    axes[1].set(ylabel='Anomaly (°C)', xlabel='Year', title='Latitude-weighted anomalies relative to 1961–1990')
    axes[1].legend(fontsize=9)
    for ax in axes:
        ax.grid(alpha=.15)
    save(fig, '01_domain_trends')

    lats = np.unique(coords[:, 0])
    lons = np.unique(coords[:, 1])
    order = np.lexsort((coords[:, 1], coords[:, 0]))
    boundaries = []
    for name in ['ne_110m_coastline', 'ne_110m_admin_0_boundary_lines_land']:
        with shapefile.Reader(str(root / 'data/boundaries' / name)) as reader:
            for shape in reader.shapes():
                ends = list(shape.parts) + [len(shape.points)]
                for first, last in zip(ends[:-1], ends[1:]):
                    points = np.array(shape.points[first:last])
                    if ((points[:, 0] >= -126) & (points[:, 0] <= -74) &
                        (points[:, 1] >= 9) & (points[:, 1] <= 61)).any():
                        boundaries.append(points.tolist())
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), layout='constrained')
    layers = [(climatology, '1991–2020 mean', 'Temperature (°C)', 'viridis'),
              (recent-baseline, '1996–2025 minus 1961–1990', 'Temperature difference (°C)', 'RdBu_r'),
              (slope, f'{years[0]}–{years[-1]} linear trend', 'Trend (°C/decade)', 'RdBu_r')]
    for ax, (layer, title, label, cmap) in zip(axes, layers):
        kwargs = {}
        if cmap == 'RdBu_r':
            lim = float(np.max(np.abs(layer)))
            kwargs['norm'] = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
        image = ax.pcolormesh(lons, lats, layer[order].reshape(len(lats), len(lons)),
                              shading='nearest', cmap=cmap, rasterized=True, **kwargs)
        ax.set(title=title, xlabel='Longitude (°E)', ylabel='Latitude (°N)')
        ax.set_aspect(1 / np.cos(np.deg2rad(35)))
        for points in boundaries:
            points = np.array(points)
            ax.plot(points[:, 0], points[:, 1], color='#333333', lw=.55)
        ax.set(xlim=(-125, -75), ylim=(10, 60))
        fig.colorbar(image, ax=ax, orientation='horizontal', pad=.1, label=label, shrink=.95)
    fig.suptitle('ERA5 regional coordinate maps • every supplied grid point, including ocean', fontsize=15)
    save(fig, '02_spatial_maps')

    hov = np.array([anomalies[coords[:, 0] == lat].mean(axis=0) for lat in lats])
    pd.DataFrame(hov, index=pd.Index(lats, name='latitude'), columns=years).to_csv(tables / 'latitude_year_anomalies.csv')
    fig, ax = plt.subplots(figsize=(11, 5), layout='constrained')
    lim = float(np.max(np.abs(hov)))
    image = ax.pcolormesh(years, lats, hov, shading='nearest', cmap='RdBu_r', vmin=-lim, vmax=lim, rasterized=True)
    ax.set(title='How temperature anomalies vary across latitude and time', xlabel='Year', ylabel='Latitude (°N)')
    fig.colorbar(image, ax=ax, label='Anomaly vs 1961–1990 (°C)')
    save(fig, '03_latitude_time')

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
    for start, end, color in [(1940, 1969, '#397d9d'), (1961, 1990, '#d59b39'), (1996, 2025, '#b83c4b')]:
        select = (dates.year >= start) & (dates.year <= end)
        cycle = [weighted_monthly[select & (dates.month == m)].mean() for m in range(1, 13)]
        axes[0].plot(range(1, 13), cycle, 'o-', color=color, label=f'{start}–{end}')
    axes[0].set(title='Seasonal cycle of domain mean temperature', xlabel='Calendar month', ylabel='Temperature (°C)', xticks=range(1, 13))
    axes[0].legend()
    annual_months = np.array([[monthly_anomaly[(dates.year == y) & (dates.month == m)][0]
                              for y in years] for m in range(1, 13)])
    lim = float(np.max(np.abs(annual_months)))
    image = axes[1].pcolormesh(years, range(1, 13), annual_months, shading='nearest', cmap='RdBu_r', vmin=-lim, vmax=lim, rasterized=True)
    axes[1].set(title='Calendar month × year anomalies', xlabel='Year', ylabel='Calendar month', yticks=range(1, 13))
    fig.colorbar(image, ax=axes[1], label='Anomaly (°C)')
    save(fig, '04_seasonality')

    # Match city coordinates to supplied grid, with distances and no interpolation.
    cities = {'Seattle': (47.6062, -122.3321), 'Los Angeles': (34.0522, -118.2437),
              'Denver': (39.7392, -104.9903), 'Chicago': (41.8781, -87.6298),
              'Houston': (29.7604, -95.3698), 'Miami': (25.7617, -80.1918)}
    matches = []
    fig, ax = plt.subplots(figsize=(11, 5), layout='constrained')
    for name, (lat, lon) in cities.items():
        a = np.sin(np.deg2rad(coords[:, 0]-lat)/2)**2 + np.cos(np.deg2rad(lat))*np.cos(np.deg2rad(coords[:, 0]))*np.sin(np.deg2rad(coords[:, 1]-lon)/2)**2
        distances = 6371 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
        i = int(distances.argmin())
        if distances[i] > 75:
            continue
        matches.append(dict(city=name, target_latitude=lat, target_longitude=lon,
                            grid_latitude=coords[i, 0], grid_longitude=coords[i, 1], distance_km=distances[i]))
        smooth = pd.Series(anomalies[i]).rolling(10, center=True, min_periods=10).mean()
        ax.plot(years, smooth, label=name, lw=1.8)
    ax.axhline(0, color='#444444', lw=.7)
    ax.set(title='Selected city-near grid points: centered 10-year temperature anomalies',
           xlabel='Year', ylabel='Anomaly vs 1961–1990 (°C)')
    ax.legend(ncol=3)
    ax.grid(alpha=.15)
    save(fig, '05_city_comparison')
    pd.DataFrame(matches).to_csv(tables / 'city_grid_matches.csv', index=False)

    # Self-contained HTML: all annual values, all locations; no CDN or server needed.
    template = (root / 'scripts/explorer_template.html').read_text()
    payload = dict(years=years.tolist(), lat=coords[:, 0].tolist(), lon=coords[:, 1].tolist(),
                   annual=np.round(annual, 2).tolist(), mean=np.round(mean, 4).tolist(),
                   slope=np.round(slope, 4).tolist(), climate=np.round(climatology, 3).tolist(),
                   change=np.round(recent-baseline, 3).tolist(), boundaries=boundaries)
    (root / 'explorer.html').write_text(template.replace('__DATA__', json.dumps(payload, separators=(',', ':'))))
    metadata = dict(locations=len(coords), monthly_columns=len(dates), monthly_start=str(dates[0].date()),
                    monthly_end=str(dates[-1].date()), complete_years=years.tolist(), missing_monthly_values=0,
                    latitude_range=[float(lats.min()), float(lats.max())], longitude_range=[float(lons.min()), float(lons.max())],
                    grid_spacing_degrees=.25, raw_sampling='Daily at 17:00 UTC, 1940-01-01 through 2026-10-21 (GRIB1 header audit)',
                    final_month_partial=True, weighted_trend_C_per_decade=domain_slope,
                    equal_grid_trend_C_per_decade=float(np.dot(equal, x)/(x@x)*10))
    (root / 'docs/data_summary.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    build(parser.parse_args().root.resolve())
