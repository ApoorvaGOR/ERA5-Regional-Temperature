# Processing and descriptive methods

## Raw GRIB to monthly values: preserved original code

`scripts/original/Data_Processing_Excel.py` opens `ERA5.grib` using xarray and
cfgrib, filtering short name `2t`. It identifies time/valid-time coordinates,
sorts them, and groups by calendar month. At every grid location it takes the
arithmetic mean over available timestamps, skipping missing source values.
It converts K to °C by subtracting 273.15, casts to float32, flattens latitude
then longitude, and writes four decimal places to the CSV.

No within-month coverage threshold is enforced. A separate standard-library
GRIB1 header audit found 31,706 messages, one per day at 17:00 UTC, from
1940-01-01 through 2026-10-21 inclusive, with every consecutive interval equal
to 24 hours. All records have parameter code 167, P1 = P2 = 0, and time-range
indicator 0 (instantaneous analysis at the reference time). This means the
monthly output averages daily 17:00 UTC samples, not all hours. October 2026
has only 21 days. The raw value-decoding step was not rerun for this
package because its decoding dependencies are not installed in the tested
environment. Its supplied code is retained; the output CSV is packaged losslessly.

Audit code: `scripts/inspect_grib1.py`. Results: `grib_header_audit.json`.
Header semantics follow the [ECMWF GRIB1 product definition](https://codes.ecmwf.int/grib/format/grib1/sections/1/)
and [time-range code table](https://codes.ecmwf.int/grib/format/grib1/ctable/5/).

## Monthly to annual: preserved original code and validated values

`scripts/original/Annual_1940_2025_data.py` selects January–December of each
year from 1940 through 2025. An annual value is the arithmetic mean of the
12 monthly values, only when all 12 are numeric. Months have equal weight;
this differs from a day-weighted annual mean. It exports and formats the
annual workbook. The delivered workbook is the supplied original, unchanged.
Because of the fixed-hour source sampling, these annual values characterize
17:00 UTC conditions, not full-day annual mean temperatures. A fixed UTC
hour also corresponds to different local solar times across longitude.

The descriptive pipeline applies the same equal-month rule and includes only
years containing all 12 month columns. Thus the extra January–October 2026
monthly values are retained in monthly data and summaries, but excluded from
annual maps, annual trends, city plots, and the explorer. The comparison
against every original Excel cell is recorded in `validation.json`.

## Spatial averages

The original scripts calculate an equal-grid average: each of the 40,401
points has weight 1. The new pipeline reports that average for comparability
and a latitude-weighted domain mean:

`mean(t) = sum_i cos(latitude_i) * temperature_i(t) / sum_i cos(latitude_i)`.

Cosine weighting approximates area weighting on a regular geographic grid.
Boundary points receive the same full-point rule as interior points. This is
not an exact clipped-cell area calculation. All points in the rectangle,
including ocean points and grid points outside any particular country, enter
the average. A land mask or administrative boundary is never applied.

## Baselines, changes, and trends

- Annual anomalies subtract each location's equal-month 1961–1990 annual mean.
- Monthly domain anomalies subtract the latitude-weighted 1961–1990 mean for
  the matching calendar month (January compared with January, and so on).
- The change map is the 1996–2025 mean minus the 1961–1990 mean. Both periods
  contain 30 complete years.
- The climatology map is the mean of annual temperatures in 1991–2020.
- Linear trends are ordinary least-squares slopes with an intercept over all
  annual values in 1940–2025. With centered years `x`, slope per decade is
  `10 * sum(x * temperature) / sum(x*x)`. These are descriptive summaries.
  No breakpoints, trend selection, significance tests, or forecasts are used.
- The black smoothing line in the anomaly figure is a centered 10-observation
  rolling annual mean requiring all 10 values. Because the window length is
  even, its label follows pandas' centered rolling convention. Edge windows
  without 10 observations are absent.

## Showing space, time, and season

`02_spatial_maps` retains latitude and longitude. Map axes are geographic
coordinates with a display aspect adjusted at 35°N, not a projected map
intended for distance measurements. Coastlines and country borders are
Natural Earth 1:110m context layers. The map is clipped to the data rectangle.

`03_latitude_time` averages the annual grid anomalies across longitude at
each latitude, preserving year and latitude. Longitude points within a given
latitude band receive equal weights.

`04_seasonality` compares the latitude-weighted monthly climatological cycles
of 1940–1969, 1961–1990, and 1996–2025, and shows a month-by-year anomaly
heatmap for complete years. The first and second cycle periods overlap.

`05_city_comparison` uses great-circle nearest-grid matching with Earth radius
6,371 km, records the chosen coordinates and distances, and only accepts
matches within 75 km. Six illustrative city targets inside this domain are
used. These curves are ERA5 grid estimates near cities, not city stations or
city-boundary averages. The plot shows centered complete 10-year anomaly means.

The offline explorer preserves every annual location series, rounded to
0.01 °C for compact display. Trend, change, and climatology layers come from
the unrounded analysis. Colors use fixed symmetric ranges across years and
saturate beyond their labeled endpoints. Numerical analysis should use the
workbook or derived tables, not values copied from the explorer.

## Differences from original plots

The untouched `Overall_average_trend.py` uses equal-grid monthly averages,
a 1961–1990 baseline, and a centered 120-month anomaly smoother accepting as
few as 60 observations at the ends. The original city script accepts annual
values with at least 10 monthly observations, uses its own nine target cities,
and allows 7-year availability in a 10-year smoother. Some of those targets
lie outside the supplied rectangle and may fail its distance threshold.

The newly generated figures consistently require 12 months for annual values,
use full 10-year smoothing windows, and explicitly label the spatial weighting.
The original scripts are included to document prior production, not as silent
substitutes for the new pipeline's methods.
