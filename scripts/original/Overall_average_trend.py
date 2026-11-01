
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("ERA5_monthly_t2m.csv")
OUTPUT_DIR = Path("ERA5_Spatial_Average_Plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASELINE_START = 1961
BASELINE_END = 1990

# Minimum number of months required for annual averages
MIN_MONTHS_PER_YEAR = 12

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
})

# ============================================================
# HELPERS
# ============================================================

def save_plot(fig, filename):
    for extension in ["png", "pdf"]:
        output_path = OUTPUT_DIR / f"{filename}.{extension}"
        fig.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight"
        )
        print(f"Saved: {output_path}")
    plt.close(fig)


def format_axis(ax):
    ax.grid(alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ============================================================
# 1. LOAD DATA
# ============================================================

print("Loading ERA5 monthly dataset...")

df = pd.read_csv(INPUT_FILE)

# First column contains latitude-longitude coordinates.
month_columns = [
    col for col in df.columns[1:]
    if pd.notna(pd.to_datetime(col, format="%Y-%m", errors="coerce"))
]

month_columns = sorted(month_columns)

dates = pd.to_datetime(month_columns, format="%Y-%m")

print(f"Number of spatial locations: {len(df):,}")
print(f"Number of months: {len(month_columns):,}")
print(f"Temporal horizon: {dates.min()} to {dates.max()}")

# ============================================================
# 2. COMPUTE SPATIAL AVERAGE
# ============================================================

# Each column represents a month.
# Average across all spatial locations.

spatial_mean = df[month_columns].mean(
    axis=0,
    skipna=True
)

temperature = pd.Series(
    spatial_mean.to_numpy(dtype=float),
    index=dates,
    name="Spatial mean temperature"
).sort_index()

print("\nSpatially averaged temperature:")
print(temperature.describe())

# Save underlying data.
temperature.to_frame().to_csv(
    OUTPUT_DIR / "spatial_average_monthly.csv",
    index_label="Month"
)

# ============================================================
# 3. PLOT 1: RAW MONTHLY SPATIAL AVERAGE
# ============================================================

fig, ax = plt.subplots(figsize=(15, 5))

ax.plot(
    temperature.index,
    temperature.values,
    color="#277DA1",
    linewidth=0.9,
    alpha=0.85
)

ax.set_title(
    "ERA5: Monthly Mean Temperature Across All Locations",
    fontweight="bold"
)

ax.set_xlabel("Year")
ax.set_ylabel("Temperature (°C)")

format_axis(ax)

save_plot(fig, "01_raw_monthly_spatial_average")

# ============================================================
# 4. COMPUTE ANNUAL AVERAGES
# ============================================================

annual_group = temperature.groupby(temperature.index.year)

annual_mean = annual_group.mean()
annual_count = annual_group.count()

# Exclude incomplete years from annual trend analysis.
annual_mean = annual_mean[
    annual_count >= MIN_MONTHS_PER_YEAR
]

print("\nAnnual averaging horizon:")
print(f"{annual_mean.index.min()} to {annual_mean.index.max()}")

# ============================================================
# 5. PLOT 2: ANNUAL MEAN + LINEAR TREND
# ============================================================

years = annual_mean.index.to_numpy(dtype=float)
values = annual_mean.to_numpy(dtype=float)

slope, intercept = np.polyfit(years, values, 1)

trend = slope * years + intercept
slope_per_decade = slope * 10

fig, ax = plt.subplots(figsize=(15, 5))

ax.plot(
    years,
    values,
    color="#277DA1",
    linewidth=1.4,
    label="Annual mean temperature"
)

ax.plot(
    years,
    trend,
    color="#B33A3A",
    linewidth=2.5,
    linestyle="--",
    label=f"Linear trend: {slope_per_decade:+.3f} °C/decade"
)

ax.set_title(
    "ERA5: Annual Mean Temperature and Long-Term Trend",
    fontweight="bold"
)

ax.set_xlabel("Year")
ax.set_ylabel("Temperature (°C)")

ax.legend()
format_axis(ax)

save_plot(fig, "02_annual_spatial_average_trend")

print(f"\nLinear trend: {slope_per_decade:+.4f} °C/decade")

# ============================================================
# 6. COMPUTE MONTHLY TEMPERATURE ANOMALIES
# ============================================================

baseline = temperature[
    (temperature.index.year >= BASELINE_START)
    & (temperature.index.year <= BASELINE_END)
]

# Mean temperature for each calendar month in baseline.
monthly_climatology = baseline.groupby(
    baseline.index.month
).mean()

if monthly_climatology.count() != 12:
    raise ValueError("Incomplete climatology baseline.")

expected_temperature = np.array([
    monthly_climatology.loc[month]
    for month in temperature.index.month
])

anomalies = pd.Series(
    temperature.to_numpy() - expected_temperature,
    index=temperature.index,
    name="Temperature anomaly"
)

# 120-month rolling mean (10 years).
rolling_anomaly = anomalies.rolling(
    window=120,
    center=True,
    min_periods=60
).mean()

# ============================================================
# 7. PLOT 3: TEMPERATURE ANOMALIES
# ============================================================

fig, ax = plt.subplots(figsize=(15, 5))

ax.plot(
    anomalies.index,
    anomalies.values,
    color="#9E9E9E",
    linewidth=0.7,
    alpha=0.65,
    label="Monthly anomaly"
)

ax.plot(
    rolling_anomaly.index,
    rolling_anomaly.values,
    color="#B33A3A",
    linewidth=2.5,
    label="10-year rolling mean"
)

ax.axhline(
    0,
    color="black",
    linestyle="--",
    linewidth=0.9
)

ax.set_title(
    "ERA5: Spatial Mean Temperature Anomalies (1961–1990 Baseline)",
    fontweight="bold"
)

ax.set_xlabel("Year")
ax.set_ylabel("Temperature anomaly (°C)")

ax.legend()
format_axis(ax)

save_plot(fig, "03_spatial_average_temperature_anomalies")

# ============================================================
# 8. SAVE COMPLETE RESULTS
# ============================================================

results = pd.DataFrame({
    "Month": temperature.index,
    "Spatial_Mean_C": temperature.values,
    "Anomaly_C": anomalies.values,
    "Rolling_10yr_Anomaly_C": rolling_anomaly.values
})

results.to_csv(
    OUTPUT_DIR / "ERA5_spatial_average_results.csv",
    index=False
)

print("\n" + "=" * 60)
print("PROCESSING COMPLETE")
print("=" * 60)
print(f"Spatial locations: {len(df):,}")
print(f"Months: {len(temperature):,}")
print(f"First month: {temperature.index.min():%Y-%m}")
print(f"Last month: {temperature.index.max():%Y-%m}")
print(f"Linear trend: {slope_per_decade:+.4f} °C/decade")
print(f"Output directory: {OUTPUT_DIR.resolve()}")
print("=" * 60)
