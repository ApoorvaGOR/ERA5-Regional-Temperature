# ERA5 regional temperature data and maps

An Excel dataset, reproducible processing scripts, descriptive maps, and an
offline explorer for **2 m air temperature** across a regular regional grid.

| Property | Supplied data |
|---|---|
| Grid | 201 latitudes × 201 longitudes = **40,401 locations** |
| Extent | **10–60°N, 125–75°W**, including land and ocean |
| Grid spacing | 0.25° latitude and longitude |
| Monthly table | **1,042 months**, January 1940–October 2026 |
| Annual Excel | **86 years**, 1940–2025; 40,401 rows × 87 columns |
| Variable and units | ERA5 2 m air temperature, converted from K to °C |
| Source sampling | Once daily at **17:00 UTC**, January 1, 1940–October 21, 2026 |
| Missing cells | None in the supplied monthly temperature table |

**Interpretation:** these are monthly averages of once-daily 17:00 UTC
samples, followed by equal-month annual averages. They are not full-diurnal
monthly or annual air-temperature means. The GRIB header audit found 31,706
consecutive daily records at 17:00 UTC. **October 2026 ends on October 21 and
is partial.** See [the header audit](docs/grib_header_audit.json).

This is a regional rectangle, not a country or land-only average. The eastern
boundary is 75°W. The original download request was not supplied.
All annual comparisons and maps stop at the last complete calendar year, 2025.

## Start with the data

- [Original annual Excel workbook](data/annual/ERA5_Annual_Temperature_1940_2025.xlsx)
  is preserved byte for byte.
- [Monthly CSV shards](data/monthly/) contain the complete original monthly
  table, losslessly split into gzip files that are individually small enough
  for GitHub's browser upload. Each shard repeats the same column header.
- [Annual CSV](data/derived/annual_temperature.csv.gz) is a machine-readable
  alternative calculated from those monthly values.
- [Derived summaries](data/derived/) contain the plotted averages, anomalies,
  grid trends, latitude-by-year values, and city-to-grid matches.
- [Data dictionary](docs/DATA_DICTIONARY.md), [methods](docs/METHODOLOGY.md),
  and [provenance](docs/PROVENANCE.md) explain units, transformations, and limits.

## Visualizations

![Annual domain averages and anomalies](figures/01_domain_trends.png)

The original equal-grid spatial average is shown alongside a cosine-latitude
weighted average. Both use the supplied rectangle and include ocean cells.

![Spatial means, changes, and trends](figures/02_spatial_maps.png)

These maps show 1991–2020 mean temperature, a change between two 30-year
periods, and a linear slope at every grid location. Natural Earth outlines
provide geographic context. All maps retain the full supplied domain.

![Latitude and year temperature anomalies](figures/03_latitude_time.png)

The latitude-by-year diagram exposes spatial differences hidden by an overall
average. Additional figures show [seasonality](figures/04_seasonality.png) and
[selected city-near locations](figures/05_city_comparison.png). Every figure
is supplied as PNG and SVG.

**Interactive:** download this folder and open [explorer.html](explorer.html)
in a browser. Choose a year and map layer, then click a location or enter its
coordinates. All 40,401 annual location series are embedded. No internet or
server is needed. GitHub's repository file view displays HTML source; open
the downloaded file locally to interact with it.

The dataset has one temperature variable with three coordinates: latitude,
longitude, and time. Flattening the 201 × 201 grid produces a multivariate
annual matrix with 86 observations and 40,401 location variables when
transposed. These locations are spatially correlated, not independent
measurements of 40,401 different physical quantities.

## Reproduce the descriptive outputs

Python 3.11 or 3.12 is recommended. From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/analyze.py
python scripts/validate.py
python scripts/checksums.py
```

Windows activation: `.venv\Scripts\activate`.

`analyze.py` verifies shard checksums and regenerates derived tables, five
figure pairs, `explorer.html`, and `docs/data_summary.json`. It preserves the
supplied Excel file. `validate.py` independently compares every annual Excel
value with a 12-month mean from the monthly table and records its results.
See [the validation report](docs/validation.json) and
[the tested environment](docs/TESTED_ENVIRONMENT.md).
`checksums.py` verifies the delivered file inventory. After intentionally
regenerating or editing files, use `python scripts/checksums.py --write` to
record the new versions.

### Recover the original monthly CSV

```bash
python scripts/package_monthly.py restore data/monthly work/ERA5_monthly_t2m.csv
```

The restored file's SHA-256 must match `data/monthly/manifest.json`. This is
a byte-for-byte reconstruction, including original numeric formatting and
row order. For normal analysis there is no need to restore it first.

### Original processing and plotting code

The four original data scripts are preserved under [scripts/original](scripts/original/).
They expect input files in the current working directory:

```bash
mkdir -p work
python scripts/package_monthly.py restore data/monthly work/ERA5_monthly_t2m.csv
cd work
python ../scripts/original/Annual_1940_2025_data.py
python ../scripts/original/Overall_average_trend.py
python ../scripts/original/Plotting_City_based_surface_temperatures.py
```

The first command recreates the annual workbook in `work/`. It requires all
12 months per annual value. The original plotting scripts have different
averaging and completeness settings from the new figures; see methods.

For the earlier GRIB → monthly CSV step, place the original `ERA5.grib` in
`work/`, install `requirements-grib.txt`, and from `work/` run:

```bash
python ../scripts/original/Data_Processing_Excel.py
```

The 2.57 GB raw GRIB is deliberately outside this upload folder. Its size,
hash, and acquisition limitations are documented in provenance. The packaged
monthly table is sufficient to regenerate all included descriptive outputs.

## Upload to GitHub

1. Create an empty repository with a name such as `era5-regional-temperature`.
2. Upload **the contents of this folder**, keeping subfolders intact. Upload
   in batches if needed. The accompanying ZIP is for transport: unzip it
   before uploading, so the README and figures display normally.
3. The Excel workbook is just under GitHub's 25 MiB browser-upload limit.
   Every packaged file is checked against that limit. The uncompressed
   monthly CSV and raw GRIB are excluded from normal Git tracking.

Git users can instead run:

```bash
git init
git add .
git commit -m "Add ERA5 regional data, processing code, and descriptive maps"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

GitHub documents its [file-size limits here](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).
No repository URL or publication is assumed by this package.

## Source and licensing

Source: ECMWF / Copernicus Climate Change Service (C3S), ERA5. Official
[ERA5 documentation](https://confluence.ecmwf.int/pages/viewpage.action?pageId=414588701)
and the [CDS hourly single-level catalogue](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview).
The exact original retrieval request remains unverified; the supplied GRIB's
daily 17:00 UTC sampling is established by its headers.

Code and documentation: [MIT](LICENSE). ERA5-derived data and figures:
[CC BY 4.0 with source attribution](DATA_LICENSE.md). Natural Earth map layers:
public domain. See [citation guidance](docs/CITATION.md) for source references.
