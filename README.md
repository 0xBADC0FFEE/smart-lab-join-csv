# Financial CSV-TSV Joiner

A CLI utility to join annual and quarterly financial metrics CSV files and output as TSV.

## Description

This utility joins two CSV files containing financial metrics into a single TSV file:
- `annual.csv`: Contains annual financial data with column headers as years (e.g., 2022)
- `quarterly.csv`: Contains quarterly financial data with column headers in format YYYYQN (e.g., 2022Q4)

The utility merges metrics from both files, adding empty cells where data is missing. The output file arranges columns chronologically, with each year column placed after its corresponding Q4 column. LTM (Last Twelve Months) column is added at the end. The original row order from the source files is preserved.

## Special Handling Rules

- If quarterly.csv contains only a Q4 column for a particular year (no Q1-Q3), and that same year exists in annual.csv, the Q4 column will be removed, and only the year column from annual.csv will be used.
- Q1, Q2, Q3 quarters are always preserved.
- If a year has multiple quarters (e.g., Q1, Q2, Q3, and Q4), all quarters including Q4 are preserved.
- Spaces are automatically removed from all data values, but headers and row names are preserved as-is.
- Comma decimal separators in numeric values (e.g., "0,08") are replaced with dots (e.g., "0.08").

## Requirements

- Python 3.6+
- pandas

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```
   - On Windows:
     ```
     venv\Scripts\activate
     ```
4. Install dependencies:
   ```
   pip install pandas
   ```

## Usage

```
python join_csv.py annual.csv quarterly.csv output.tsv
```

Where:
- `annual.csv`: Path to the CSV file with annual data
- `quarterly.csv`: Path to the CSV file with quarterly data
- `output.tsv`: Path where the joined TSV file will be saved

## Input CSV Format

Both input files should use semicolon (`;`) as the delimiter.

### annual.csv
- Row indices are metric names
- Column headers are years (e.g., 2017, 2018, etc.)
- May contain an LTM column

### quarterly.csv
- Row indices are metric names
- Column headers are in format YYYYQN (e.g., 2022Q4), where YYYY is the year and N is the quarter number

## Output Format

The output TSV file will:
- Use tab (`\t`) as the delimiter
- Contain all metrics from both input files
- Preserve the original row order from the source files (first all rows from annual.csv, then any new rows from quarterly.csv)
- Order columns chronologically, with year columns placed after Q4 columns
- Skip Q4 columns when they are the only quarter for a year in quarterly.csv and that year exists in annual.csv
- Remove all spaces from data values while preserving column headers and row names
- Convert decimal commas to decimal dots in numeric values
- End with the LTM column if it exists in the annual data 