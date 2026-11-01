# Provenance and reproducibility boundaries

## Supplied evidence

This package was assembled on 2026-11-01 from the supplied local data folder.
Only the temperature data, its four original processing/plotting scripts,
and the coastline/country-boundary context layers were selected.

- `ERA5_Annual_Temperature_1940_2025.xlsx`: preserved as supplied, not regenerated.
- `ERA5_monthly_t2m.csv`: losslessly packaged into ordered gzip shards. The
  duplicate `_copy.csv` was not included.
- `ERA5.grib`: 2,565,332,460 bytes; retained in the original source location,
  outside this upload folder. Its SHA-256 is recorded in `source_inventory.json`.
- Four Python source files: preserved unchanged under `scripts/original/`.
- Natural Earth coastline and country boundaries: copied from supplied map
  resources. Their accompanying VERSION files are retained.

`source_inventory.json` records hashes of the selected original files.
`data/monthly/manifest.json` records the complete original monthly CSV hash
and the integrity metadata for each shard. `checksums.sha256` inventories the
delivered repository files (excluding itself and ignored runtime files).

The monthly-to-annual calculation and every Excel data value are validated
against the supplied monthly table. The original GRIB-to-monthly processing
step has not been rerun. The packaged data can reproduce the included maps
and summaries without accessing the GRIB or the internet.

## Source attribution

ERA5 is produced by ECMWF for the Copernicus Climate Change Service (C3S).
The original code identifies the variable as `2t` / `t2m`, temperature of air
at 2 m above the surface. This is not skin temperature or a direct station
observation series.

Official references, checked when assembling the package:

- [ERA5 documentation](https://confluence.ecmwf.int/pages/viewpage.action?pageId=414588701)
- [ECMWF parameter 167: 2 metre temperature](https://codes.ecmwf.int/grib/param-db/?id=167)
- [CDS monthly single-level catalogue](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-monthly-means?tab=overview)
- [CDS hourly single-level catalogue](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview)

The catalogues are source references, not proof of which retrieval generated
the supplied GRIB. The header audit verifies daily 17:00 UTC instantaneous
samples (parameter 167, zero forecast offset and time-range indicator 0),
rather than a precomputed full-diurnal monthly product. No original CDS request JSON, download log, exact download
date, or license acceptance record was supplied. Consequently no purported
exact download script or invented product DOI is assigned to this extract.
If retrieving a replacement, record the CDS dataset, product type, time
selection, variable, area, dates, and request JSON. A new download can change
because of data revisions and need not be byte-identical to this extract.

## Coverage limits

The CSV has complete numeric cells and contiguous monthly labels. The raw
GRIB1 header scan additionally verifies 31,706 consecutive daily records at
17:00 UTC, from January 1, 1940 to October 21, 2026. All consecutive reference
times differ by exactly 24 hours. The original GRIB conversion averages
these available samples. October 2026 has 21 days and is partial. No month
is a full-diurnal mean. Header results are in `grib_header_audit.json`; they
establish temporal sampling but do not independently validate decoded data values.

The domain is regional, includes ocean cells, and stops at 75°W. It cannot
support global, full-country, land-only, or station-level claims without
additional selection and metadata. Descriptive linear slopes do not imply
independent residuals, statistical significance, or causal attribution.
