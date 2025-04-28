# Financial CSV-TSV Joiner

A CLI utility to join annual and quarterly financial metrics for a ticker symbol and output as TSV.

## Description

This utility downloads financial metrics data for a specific ticker from smart-lab.ru, combines the annual and quarterly data, and outputs a single TSV file. The output file is automatically named after the ticker (e.g., MGKL.tsv).

The utility merges metrics from both sources, adding empty cells where data is missing. The output file arranges columns chronologically, with each year column placed after its corresponding Q4 column. LTM (Last Twelve Months) column is added at the end. The original row order from the source files is preserved.

## Special Handling Rules

- If quarterly data contains only a Q4 column for a particular year (no Q1-Q3), and that same year exists in annual data, the Q4 column will be removed, and only the year column from annual data will be used.
- Q1, Q2, Q3 quarters are always preserved.
- If a year has multiple quarters (e.g., Q1, Q2, Q3, and Q4), all quarters including Q4 are preserved.
- Spaces are automatically removed from all data values, but headers and row names are preserved as-is.
- Comma decimal separators in numeric values (e.g., "0,08") are replaced with dots (e.g., "0.08").
- Certain metric names are shortened or standardized for clarity (see Metric Name Changes below).

## Metric Name Changes

The following metric names are transformed in the output:

| Original Metric Name | New Metric Name |
|----------------------|----------------|
| Операционный денежный поток, млрд руб | OCF, млрд руб |
| Дивиденды/прибыль, % | DPR, % |
| Чистые активы, млрд руб | Капитал, млрд руб |
| Активы банка, млрд руб | Активы, млрд руб |
| Дивиденд, руб/акцию | DPS, руб |
| Див доход, ао, % | DY, % |
| Див доход, ап, % | P_DY, % |
| Доходность FCF, % | FCF/P, % |
| Долг/EBITDA | ND/EBITDA |
| P/BV | P/B |

## Requirements

- Python 3.6+
- pandas
- requests

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
   pip install -r requirements.txt
   ```

## Usage

```
python join_csv.py TICKER
```

Where `TICKER` is the ticker symbol (e.g., MGKL).

The utility will:
1. Download annual data from https://smart-lab.ru/q/TICKER/f/y/MSFO/download/
2. Download quarterly data from https://smart-lab.ru/q/TICKER/f/q/MSFO/download/
3. Process and join the data
4. Output the result to `TICKER.tsv`
5. Clean up temporary files

## Data Source

Data is downloaded from:
- Annual data: https://smart-lab.ru/q/TICKER/f/y/MSFO/download/
- Quarterly data: https://smart-lab.ru/q/TICKER/f/q/MSFO/download/

## Output Format

The output TSV file will:
- Use tab (`\t`) as the delimiter
- Contain all metrics from both input sources
- Preserve the original row order from the source files (first all rows from annual data, then any new rows from quarterly data)
- Order columns chronologically, with year columns placed after Q4 columns
- Skip Q4 columns when they are the only quarter for a year in quarterly data and that year exists in annual data
- Remove all spaces from data values while preserving column headers and row names
- Convert decimal commas to decimal dots in numeric values
- Rename certain metrics according to the mapping table above
- End with the LTM column if it exists in the annual data 