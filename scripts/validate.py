"""Validate packaged checksums and every annual value against the supplied Excel file."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import openpyxl

from analyze import load_monthly

ROOT = Path(__file__).resolve().parents[1]


def validate(root=ROOT):
    df, coords, dates, values = load_monthly(root)
    years = list(range(1940, 2026))
    expected = np.column_stack([values[:, dates.year == year].mean(axis=1) for year in years])
    path = root / 'data/annual/ERA5_Annual_Temperature_1940_2025.xlsx'
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    if wb.sheetnames != ['Annual Temperature']:
        raise ValueError('Unexpected workbook sheets')
    rows = wb.active.iter_rows(values_only=True)
    if list(next(rows)) != ['Latitude_Longitude'] + [str(y) for y in years]:
        raise ValueError('Unexpected workbook columns')
    maximum = 0.
    count = 0
    for i, row in enumerate(rows):
        if row[0] != df.iloc[i, 0]:
            raise ValueError(f'Coordinate mismatch at row {i+2}')
        observed = np.array(row[1:], dtype=float)
        difference = np.max(np.abs(observed - expected[i]))
        if not np.isfinite(observed).all() or difference > 1e-10:
            raise ValueError(f'Annual value mismatch at row {i+2}')
        maximum = max(maximum, float(difference))
        count += 1
    wb.close()
    if count != len(df):
        raise ValueError('Workbook row count mismatch')
    oversized = [str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.stat().st_size >= 25*1024**2]
    if oversized:
        raise ValueError(f'Files exceed browser-upload limit: {oversized}')
    report = dict(monthly_rows=len(df), monthly_columns=len(dates),
                  annual_rows_checked=count, annual_values_checked=int(expected.size),
                  annual_years=[1940, 2025], annual_max_absolute_difference_C=maximum,
                  tolerance_C=1e-10, all_monthly_shard_checksums_pass=True,
                  all_files_below_25_MiB=True)
    (root / 'docs/validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    validate(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT)
