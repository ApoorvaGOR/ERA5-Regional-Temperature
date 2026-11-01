
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

INPUT_FILE = Path("ERA5_monthly_t2m.csv")
OUTPUT_FILE = Path("ERA5_Annual_Temperature_1940_2025.xlsx")

START_YEAR = 1940
END_YEAR = 2025

# Read the existing monthly temperature data
df = pd.read_csv(INPUT_FILE)

coordinate_col = df.columns[0]
years = range(START_YEAR, END_YEAR + 1)

annual_df = pd.DataFrame()
annual_df[coordinate_col] = df[coordinate_col]

for year in years:
    months = [f"{year}-{month:02d}" for month in range(1, 13)]

    missing = [month for month in months if month not in df.columns]
    if missing:
        raise ValueError(
            f"Missing monthly columns for {year}: {missing}"
        )

    # Average all 12 monthly temperatures for each coordinate
    monthly_values = df[months].apply(
        pd.to_numeric, errors="coerce"
    )

    # Require all 12 monthly values
    annual_df[str(year)] = monthly_values.mean(
        axis=1
    ).where(monthly_values.notna().sum(axis=1) == 12)

# Export to Excel
annual_df.to_excel(
    OUTPUT_FILE,
    index=False,
    sheet_name="Annual Temperature"
)

# Basic formatting
wb = load_workbook(OUTPUT_FILE)
ws = wb.active

ws.freeze_panes = "B2"
ws.auto_filter.ref = ws.dimensions
ws.column_dimensions["A"].width = 26

for cell in ws[1]:
    cell.font = Font(color="FFFFFF", bold=True)
    cell.fill = PatternFill("solid", fgColor="17365D")
    cell.alignment = Alignment(horizontal="center")

for row in ws.iter_rows(
    min_row=2, min_col=2, max_col=ws.max_column
):
    for cell in row:
        cell.number_format = "0.000"

wb.save(OUTPUT_FILE)

print(f"Saved: {OUTPUT_FILE.resolve()}")
print(f"Number of locations: {len(annual_df):,}")
print(f"Number of annual columns: {len(years)}")
print(f"Time horizon: {START_YEAR}-{END_YEAR}")
print(f"Missing annual values: {annual_df.iloc[:, 1:].isna().sum().sum():,}")
