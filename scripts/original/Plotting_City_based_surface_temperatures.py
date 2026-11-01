
from pathlib import Path
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("ERA5_monthly_t2m.csv")
OUTPUT_DIR = Path("ERA5_City_Plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Maximum acceptable distance from city to ERA5 grid point
MAX_DISTANCE_KM = 75

# Reference period for temperature anomalies
BASELINE_START = 1961
BASELINE_END = 1990

# Minimum number of available months for annual mean
MIN_MONTHS_PER_YEAR = 10

# The previous processing script exported Celsius.
# Change to "K" if your CSV contains Kelvin.
TEMPERATURE_UNIT = "C"

CITIES = {
    "East Coast": {
        "New York": (40.7128, -74.0060),
        "Boston": (42.3601, -71.0589),
        "Washington DC": (38.9072, -77.0369),
    },
    "Midwest": {
        "Chicago": (41.8781, -87.6298),
        "Detroit": (42.3314, -83.0458),
        "Minneapolis": (44.9778, -93.2650),
    },
    "West Coast": {
        "Los Angeles": (34.0522, -118.2437),
        "San Francisco": (37.7749, -122.4194),
        "Seattle": (47.6062, -122.3321),
    },
}

REGION_COLORS = {
    "East Coast": "#B33A3A",
    "Midwest": "#277DA1",
    "West Coast": "#31865B",
}

# ============================================================
# HELPERS
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance, supporting NumPy arrays."""

    radius = 6371.0

    p1 = np.radians(lat1)
    p2 = np.radians(lat2)

    dp = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)

    a = (
        np.sin(dp / 2) ** 2
        + np.cos(p1) * np.cos(p2)
        * np.sin(dl / 2) ** 2
    )

    return 2 * radius * np.arcsin(np.sqrt(a))


def save_figure(fig, filename):
    for extension in ["png", "pdf"]:
        path = OUTPUT_DIR / f"{filename}.{extension}"

        kwargs = {"bbox_inches": "tight"}

        if extension == "png":
            kwargs["dpi"] = 300

        fig.savefig(path, **kwargs)
        print(f"Saved: {path}")

    plt.close(fig)


def annual_means(series):
    """Annual means using years with sufficient observations."""

    grouped = series.groupby(series.index.year)

    means = grouped.mean()
    counts = grouped.count()

    return means.where(counts >= MIN_MONTHS_PER_YEAR).dropna()


def linear_trend(years, values):
    """Return fitted values and slope in Celsius per decade."""

    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)

    valid = np.isfinite(x) & np.isfinite(y)

    if valid.sum() < 3:
        return None, np.nan

    slope, intercept = np.polyfit(x[valid], y[valid], 1)

    return slope * x + intercept, slope * 10


# ============================================================
# 1. READ MONTHLY ERA5 DATA
# ============================================================

print("Loading ERA5 monthly temperature data...")

df = pd.read_csv(INPUT_FILE)

coordinate_column = df.columns[0]

# Extract latitude and longitude from "(lat, lon)"
coordinates = df[coordinate_column].astype(str).str.extract(
    r"\(\s*([-+]?\d+(?:\.\d+)?)\s*,\s*"
    r"([-+]?\d+(?:\.\d+)?)\s*\)"
)

if coordinates.isna().any().any():
    raise ValueError(
        "Could not parse latitude-longitude coordinates."
    )

grid_lat = coordinates[0].astype(float).to_numpy()
grid_lon = coordinates[1].astype(float).to_numpy()

# Identify YYYY-MM columns
month_columns = [
    col for col in df.columns
    if re.fullmatch(r"\d{4}-\d{2}", str(col))
]

month_columns = sorted(month_columns)

if not month_columns:
    raise ValueError("No monthly columns found.")

dates = pd.to_datetime(month_columns, format="%Y-%m")

print(f"Grid locations: {len(df):,}")
print(f"Monthly periods: {len(month_columns):,}")
print(f"Temporal horizon: {dates.min():%Y-%m} to {dates.max():%Y-%m}")

# ============================================================
# 2. SELECT NEAREST GRID LOCATION FOR EACH CITY
# ============================================================

city_series = {}
city_metadata = []

for region, cities in CITIES.items():

    city_series[region] = {}

    for city, (lat, lon) in cities.items():

        distances = haversine_km(
            lat, lon, grid_lat, grid_lon
        )

        nearest_idx = int(np.argmin(distances))
        nearest_distance = float(distances[nearest_idx])

        nearest_lat = grid_lat[nearest_idx]
        nearest_lon = grid_lon[nearest_idx]

        if nearest_distance > MAX_DISTANCE_KM:
            print(
                f"SKIPPING {city}: nearest grid point "
                f"is {nearest_distance:.1f} km away."
            )
            continue

        values = pd.to_numeric(
            df.loc[nearest_idx, month_columns],
            errors="coerce"
        ).to_numpy(dtype=float)

        if TEMPERATURE_UNIT.upper() == "K":
            values = values - 273.15

        series = pd.Series(
            values,
            index=dates,
            name=city
        ).sort_index()

        city_series[region][city] = series

        city_metadata.append({
            "region": region,
            "city": city,
            "city_lat": lat,
            "city_lon": lon,
            "grid_lat": nearest_lat,
            "grid_lon": nearest_lon,
            "distance_km": nearest_distance,
        })

        print(
            f"{city:18s} -> "
            f"({nearest_lat:.2f}, {nearest_lon:.2f}) "
            f"distance={nearest_distance:.1f} km"
        )

pd.DataFrame(city_metadata).to_csv(
    OUTPUT_DIR / "selected_city_gridpoints.csv",
    index=False
)

# ============================================================
# 3. FIGURE 1: RAW MONTHLY TEMPERATURES
# ============================================================

fig, axes = plt.subplots(
    3, 1, figsize=(15, 11),
    sharex=True, constrained_layout=True
)

for ax, (region, cities) in zip(axes, city_series.items()):

    for city, series in cities.items():
        ax.plot(
            series.index,
            series.values,
            linewidth=0.65,
            alpha=0.8,
            label=city
        )

    ax.set_title(region, fontsize=13, fontweight="bold")
    ax.set_ylabel("Temperature (°C)")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", ncol=3, fontsize=9)

axes[-1].set_xlabel("Year")

fig.suptitle(
    "ERA5: Monthly 2m Temperature at Selected US Cities",
    fontsize=17,
    fontweight="bold"
)

save_figure(fig, "01_raw_monthly_temperatures")

# ============================================================
# 4. FIGURE 2: ANNUAL MEANS AND LINEAR TRENDS
# ============================================================

fig, axes = plt.subplots(
    3, 1, figsize=(15, 11),
    sharex=True, constrained_layout=True
)

for ax, (region, cities) in zip(axes, city_series.items()):

    for city, series in cities.items():

        annual = annual_means(series)

        if len(annual) < 3:
            continue

        line, = ax.plot(
            annual.index,
            annual.values,
            linewidth=1.0,
            alpha=0.65,
            label=city
        )

        fitted, slope_decade = linear_trend(
            annual.index, annual.values
        )

        if fitted is not None:
            ax.plot(
                annual.index,
                fitted,
                linestyle="--",
                linewidth=2,
                color=line.get_color(),
                label=f"{city} trend: {slope_decade:+.2f} °C/decade"
            )

    ax.set_title(region, fontsize=13, fontweight="bold")
    ax.set_ylabel("Annual mean (°C)")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=8, ncol=2)

axes[-1].set_xlabel("Year")

fig.suptitle(
    "ERA5: Annual Mean Temperature and Linear Trends",
    fontsize=17,
    fontweight="bold"
)

save_figure(fig, "02_annual_temperature_trends")

# ============================================================
# 5. FIGURE 3: TEMPERATURE ANOMALIES
# ============================================================

fig, axes = plt.subplots(
    3, 1, figsize=(15, 11),
    sharex=True, constrained_layout=True
)

for ax, (region, cities) in zip(axes, city_series.items()):

    for city, series in cities.items():

        baseline = series[
            (series.index.year >= BASELINE_START)
            & (series.index.year <= BASELINE_END)
        ]

        if baseline.dropna().empty:
            print(f"No baseline data for {city}")
            continue

        # Calendar-month climatology: Jan vs Jan, etc.
        monthly_climatology = baseline.groupby(
            baseline.index.month
        ).mean()

        if monthly_climatology.count() < 12:
            print(f"Incomplete baseline for {city}")
            continue

        expected = np.array([
            monthly_climatology.loc[month]
            for month in series.index.month
        ])

        anomalies = pd.Series(
            series.to_numpy() - expected,
            index=series.index
        )

        annual = annual_means(anomalies)

        if len(annual) < 3:
            continue

        line, = ax.plot(
            annual.index,
            annual.values,
            linewidth=0.9,
            alpha=0.4,
            label=f"{city} annual"
        )

        # 10-year centered moving average
        smooth = annual.rolling(
            window=10,
            min_periods=7,
            center=True
        ).mean()

        ax.plot(
            smooth.index,
            smooth.values,
            linewidth=2.2,
            color=line.get_color(),
            label=f"{city} 10-year mean"
        )

    ax.axhline(
        0, color="black",
        linestyle="--",
        linewidth=0.8
    )

    ax.set_title(region, fontsize=13, fontweight="bold")
    ax.set_ylabel("Temperature anomaly (°C)")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=8, ncol=2)

axes[-1].set_xlabel("Year")

fig.suptitle(
    "ERA5: Temperature Anomalies Relative to 1961–1990",
    fontsize=17,
    fontweight="bold"
)

save_figure(fig, "03_temperature_anomalies")

print("\nAll plots completed.")
print(f"Output directory: {OUTPUT_DIR.resolve()}")
