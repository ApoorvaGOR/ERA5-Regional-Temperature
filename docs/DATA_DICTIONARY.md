# Data dictionary

## Original annual workbook

File: `data/annual/ERA5_Annual_Temperature_1940_2025.xlsx`.
Sheet: `Annual Temperature`. One header row and 40,401 location rows.

| Field | Type | Meaning |
|---|---|---|
| `Latitude_Longitude` | String `(latitude, longitude)` | Grid coordinates in decimal degrees, four decimal places; north/east positive |
| `1940` … `2025` | Numeric, °C | Arithmetic mean of the corresponding 12 monthly values at that grid location |

Rows retain the original order. Coordinates are not city names or station IDs.
The original table runs latitude from 60°N down to 10°N and longitude from
125°W to 75°W within each latitude band. Both geographic endpoints are included.
Excel displays three decimal places; underlying values have greater precision.

## Original monthly table in `data/monthly/part-*.csv.gz`

Every shard has the same 1,043-column header: `Latitude_Longitude`, followed by
1,042 month columns (`1940-01` … `2026-10`). The shards partition location rows,
not time. They preserve original CSV bytes and four-decimal numeric strings.
Load and concatenate in the order given by `manifest.json`. The final shard
has 401 rows; all preceding shards have 2,500 rows.

Each value is a monthly arithmetic mean of the available daily 17:00 UTC
source samples at one grid location, in °C. The original code allows missing
source timestamps and does not validate full within-month coverage. The raw
header audit establishes consecutive daily records through October 21, 2026.
Thus October 2026 is partial, and no month represents a full diurnal mean.
There are no missing cells in the supplied monthly output.

`manifest.json` records original file size and SHA-256, each shard's SHA-256,
row count, and byte size. `source_sha256` applies to the restored CSV, not
the concatenation of compressed shard bytes.

## Derived files

| File | Grain | Fields and interpretation |
|---|---|---|
| `annual_temperature.csv.gz` | Location × annual column | Same layout and equal-month rule as Excel; years with all 12 monthly columns only |
| `domain_monthly.csv` | One month | `month`; `equal_grid_C`; `latitude_weighted_C`; `weighted_anomaly_C` relative to that calendar month's 1961–1990 mean |
| `domain_annual.csv` | One complete year | `year`; `equal_grid_C`; `latitude_weighted_C`; `weighted_anomaly_C` relative to annual 1961–1990 mean |
| `grid_summary.csv` | One grid point | `latitude`, `longitude`; `mean_1991_2020_C`; `change_1996_2025_vs_1961_1990_C`; `slope_C_per_decade` over 1940–2025 |
| `latitude_year_anomalies.csv` | Latitude × annual column | Longitude-mean anomaly at each latitude, relative to each location's 1961–1990 mean |
| `city_grid_matches.csv` | Selected city | City name, target coordinates, chosen grid coordinates, great-circle distance in km |

All derived tables are in `data/derived/`. Numeric fields use °C unless a
different unit appears in the field name. Anomaly and temperature difference
units are °C (numerically equivalent to K for differences).

## Multidimensional interpretation

The original monthly field is `temperature[time, latitude, longitude]` with
dimensions 1,042 × 201 × 201. Flattening the spatial axes gives 40,401 location
rows and 1,042 time columns. The annual field has dimensions 86 × 201 × 201.
One can transpose the annual wide table to 86 rows and 40,401 columns for
multivariate analysis. This does not create additional physical variables.

No uncertainty estimates, station counts, elevation, land mask, or country
classification are included. Boundaries are contextual Natural Earth layers,
not additional climate observations.
