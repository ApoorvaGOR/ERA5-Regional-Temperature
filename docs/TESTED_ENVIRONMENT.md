# Tested environment

Validated on macOS using Python 3.11.4, NumPy 2.3.5, pandas 2.3.3,
Matplotlib 3.11.2, openpyxl 3.1.5, and pyshp 3.1.6.

The dependency ranges in `requirements.txt` describe the supported intended
environment. These exact versions record the environment used for the
included figures and validation; other versions can change file formatting
or rendering without changing the underlying calculations.

Checks performed for the delivered package:

- Every monthly shard hash and row count checked on load.
- All 3,474,486 annual temperature cells compared with independently
  recalculated 12-month averages from the monthly data. Maximum absolute
  difference is recorded in `validation.json` (floating-point tolerance
  1e-10 °C).
- Coordinate order, column labels, finite numeric values, contiguous month
  sequence, and rectangular grid checked.
- Original annual workbook preserved with matching SHA-256.
- Original monthly CSV restored and its full SHA-256 compared with the source.
- All 31,706 raw GRIB1 message headers inspected for reference times and
  parameter/time-range codes, without decoding temperature fields.
- Descriptive processing pipeline run successfully; generated figures
  visually reviewed. Browser interaction checks are recorded separately in
  `browser_validation.json`.
- All delivered repository files checked to remain below 25 MiB individually.

Not executed: GRIB temperature decoding via xarray/cfgrib, a new CDS download,
or GitHub publication. The supplied GRIB-to-monthly source script is retained
but the original raw-to-CSV transformation has not been independently verified.

Reproduce the raw header audit (requires access to the original external GRIB):

```bash
python scripts/inspect_grib1.py /path/to/ERA5.grib docs/grib_header_audit.json
```

The new analysis code rejects missing monthly output values rather than
silently changing its spatial denominator. Current files contain none.
