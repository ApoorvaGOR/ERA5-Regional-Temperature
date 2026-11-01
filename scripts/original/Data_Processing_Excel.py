
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("ERA5.grib")
OUTPUT_FILE = Path("ERA5_monthly_t2m.csv")

# ERA5 temperature is stored in Kelvin.
# Set True to export Celsius.
CONVERT_TO_CELSIUS = True

# ============================================================
# 1. OPEN GRIB FILE
# ============================================================

print("Opening ERA5 GRIB file...")

ds = xr.open_dataset(
    INPUT_FILE,
    engine="cfgrib",
    backend_kwargs={
        "filter_by_keys": {"shortName": "2t"},
        "indexpath": ""
    },
    chunks=None
)

print("\nDataset information:")
print(ds)

# ============================================================
# 2. IDENTIFY TEMPERATURE VARIABLE
# ============================================================

if "t2m" in ds.data_vars:
    var_name = "t2m"
elif "2t" in ds.data_vars:
    var_name = "2t"
else:
    raise ValueError(
        f"Cannot identify 2m temperature. "
        f"Available variables: {list(ds.data_vars)}"
    )

da = ds[var_name]

# ============================================================
# 3. IDENTIFY TEMPORAL COORDINATE
# ============================================================

# ERA5 GRIB typically has 'time', while some files
# use 'valid_time'.

if "valid_time" in da.coords and "step" in da.dims:
    da = da.stack(observation=("time", "step"))
    da = da.assign_coords(
        observation=(
            "observation",
            pd.to_datetime(
                da["valid_time"].values.reshape(-1)
            )
        )
    )
    da = da.rename({"observation": "time_obs"})

elif "valid_time" in da.coords and "time" in da.dims:
    da = da.assign_coords(
        time=pd.to_datetime(da["valid_time"].values)
    )
    da = da.rename({"time": "time_obs"})

elif "time" in da.dims:
    da = da.rename({"time": "time_obs"})

else:
    raise ValueError("Cannot identify temporal dimension.")

times = pd.DatetimeIndex(
    pd.to_datetime(da["time_obs"].values)
)

# Sort chronologically.
order = np.argsort(times.values)
times = times[order]
da = da.isel(time_obs=order)

# ============================================================
# 4. PRINT TEMPORAL HORIZON
# ============================================================

print("\n" + "=" * 65)
print("ERA5 TEMPORAL HORIZON")
print("=" * 65)

print(f"First observation : {times.min()}")
print(f"Last observation  : {times.max()}")
print(f"Total timestamps  : {len(times):,}")
print(f"First month       : {times.min():%Y-%m}")
print(f"Last month        : {times.max():%Y-%m}")
print(f"Unique months     : {len(times.to_period('M').unique()):,}")

print("=" * 65)

# ============================================================
# 5. IDENTIFY SPATIAL GRID
# ============================================================

lat_name = (
    "latitude" if "latitude" in da.coords else "lat"
)
lon_name = (
    "longitude" if "longitude" in da.coords else "lon"
)

latitudes = da[lat_name].values
longitudes = da[lon_name].values

if latitudes.ndim != 1 or longitudes.ndim != 1:
    raise ValueError("Expected a regular latitude-longitude grid.")

n_lat = len(latitudes)
n_lon = len(longitudes)
n_locations = n_lat * n_lon

print("\nSPATIAL GRID")
print(f"Latitude range  : {latitudes.min()} to {latitudes.max()}")
print(f"Longitude range : {longitudes.min()} to {longitudes.max()}")
print(f"Latitude points : {n_lat:,}")
print(f"Longitude points: {n_lon:,}")
print(f"Total locations : {n_locations:,}")

# Create latitude-longitude labels.
lat_grid, lon_grid = np.meshgrid(
    latitudes,
    longitudes,
    indexing="ij"
)

locations = [
    f"({lat:.4f}, {lon:.4f})"
    for lat, lon in zip(
        lat_grid.ravel(),
        lon_grid.ravel()
    )
]

# ============================================================
# 6. MONTHLY AVERAGING
# ============================================================

monthly_periods = times.to_period("M")
unique_months = monthly_periods.unique().sort_values()

print("\nComputing monthly averages...")

monthly_columns = {}

for i, month in enumerate(unique_months, start=1):

    # Indices of all available observations in this month.
    indices = np.flatnonzero(monthly_periods == month)

    # Select observations for this month only.
    monthly_data = da.isel(time_obs=indices)

    # Average over available timestamps.
    monthly_mean = monthly_data.mean(
        dim="time_obs",
        skipna=True
    )

    # Ensure spatial dimension order is latitude, longitude.
    monthly_mean = monthly_mean.transpose(
        lat_name,
        lon_name
    )

    values = monthly_mean.values.reshape(-1)

    # Kelvin -> Celsius.
    if CONVERT_TO_CELSIUS:
        values = values - 273.15

    month_label = str(month)

    monthly_columns[month_label] = values.astype(
        np.float32
    )

    first_time = times[indices].min()
    last_time = times[indices].max()

    print(
        f"[{i}/{len(unique_months)}] "
        f"{month_label}: "
        f"{len(indices)} timestamps | "
        f"{first_time} to {last_time}"
    )

# ============================================================
# 7. CONSTRUCT FINAL TABLE
# ============================================================

print("\nConstructing output table...")

result = pd.DataFrame(
    monthly_columns,
    index=pd.Index(
        locations,
        name="Latitude_Longitude"
    )
)

# ============================================================
# 8. SAVE CSV
# ============================================================

result.to_csv(
    OUTPUT_FILE,
    index=True,
    float_format="%.4f"
)

print("\n" + "=" * 65)
print("PROCESSING COMPLETED")
print("=" * 65)

print(f"Output file : {OUTPUT_FILE.resolve()}")
print(f"Rows        : {result.shape[0]:,}")
print(f"Columns     : {result.shape[1] + 1:,}")
print(f"Months      : {result.shape[1]:,}")
print(f"Units       : {'Celsius' if CONVERT_TO_CELSIUS else 'Kelvin'}")

print("\nFirst 5 rows:")
print(result.iloc[:5, :5])

print("\nLast 5 month labels:")
print(result.columns[-5:].tolist())

print("=" * 65)

ds.close()
