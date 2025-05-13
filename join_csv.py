#!/usr/bin/env python3
import pandas as pd
import argparse
import re
import os
import requests
from collections import OrderedDict, defaultdict
from datetime import datetime


def is_year_column(col_name):
    """Check if column name is a year (like '2022')"""
    return bool(re.match(r'^20\d{2}$', str(col_name)))


def is_quarter_column(col_name):
    """Check if column name is a quarter (like '2022Q4')"""
    return bool(re.match(r'^20\d{2}Q[1-4]$', str(col_name)))


def is_half_year_column(col_name):
    """Check if column name is a half-year (like '2022H1')"""
    return bool(re.match(r'^20\d{2}H[1-2]$', str(col_name)))


def get_year_from_period(period_col):
    """Extract year from a period column name (e.g., '2022Q4' -> '2022')"""
    match = re.match(r'^(20\d{2})[QH][1-4]$', period_col)
    if match:
        return match.group(1)
    return None


def get_period_value(period_col):
    """
    Get a numeric value for sorting period columns chronologically
    For example: 
    - 2022Q1 -> (2022, 0.25)
    - 2022Q2 -> (2022, 0.5)
    - 2022H1 -> (2022, 0.55)
    - 2022Q3 -> (2022, 0.75)
    - 2022Q4 -> (2022, 0.9)
    - 2022H2 -> (2022, 0.95)
    - 2022 -> (2022, 1.0)
    """
    if is_year_column(period_col):
        return (int(period_col), 1.0)
    
    year_match = re.match(r'^(20\d{2})([QH])([1-4])$', period_col)
    if year_match:
        year = int(year_match.group(1))
        period_type = year_match.group(2)  # Q or H
        period_num = int(year_match.group(3))
        
        if period_type == 'Q':
            # Make Q4 come before the year
            if period_num == 4:
                return (year, 0.9)
            else:
                return (year, period_num * 0.25)
        elif period_type == 'H':
            if period_num == 1:
                return (year, 0.55)  # H1 between Q2 and Q3
            else:
                return (year, 0.95)  # H2 between Q4 and annual
    
    # Handle special case for LTM by giving it a very high value
    if period_col == 'LTM':
        return (9999, 1.0)
        
    return (0, 0)  # Default for unrecognized formats


def detect_and_convert_half_years(columns):
    """
    Detect when only Q2 and Q4 are present for a year and convert them to H1 and H2
    Returns a mapping of original column names to new column names
    """
    # Group columns by year
    year_quarters = defaultdict(list)
    for col in columns:
        if is_quarter_column(col):
            year = get_year_from_period(col)
            quarter = col[-1]
            year_quarters[year].append(quarter)
    
    # Create mapping for columns to rename
    col_mapping = {}
    for year, quarters in year_quarters.items():
        # If only Q2 and Q4 exist for this year, rename them to H1 and H2
        if sorted(quarters) == ['2', '4'] and len(quarters) == 2:
            col_mapping[f"{year}Q2"] = f"{year}H1"
            col_mapping[f"{year}Q4"] = f"{year}H2"
    
    return col_mapping


def clean_value(value):
    """Clean a value by removing spaces and replacing comma decimal separators with dots"""
    if isinstance(value, str):
        # First remove spaces
        value = value.replace(" ", "")
        
        # Then replace comma decimal separator with dot
        # We need to check if the string contains a comma followed by digits
        # to avoid replacing commas in non-numeric contexts
        if re.search(r'\d+,\d+', value):
            value = value.replace(",", ".")
        
        return value
    return value


def convert_date_format(date_str):
    """Convert date from dd.mm.yyyy to yyyy-mm-dd format"""
    if not isinstance(date_str, str):
        return date_str
    
    # Check if the string is a date in dd.mm.yyyy format
    date_pattern = re.compile(r'(\d{2})\.(\d{2})\.(\d{4})')
    match = date_pattern.match(date_str)
    
    if match:
        day, month, year = match.groups()
        try:
            # Parse and format the date
            return f"{year}-{month}-{day}"
        except ValueError:
            # Return original if it's not a valid date
            return date_str
    
    return date_str


def rename_metrics(df):
    """Rename specific metrics in the DataFrame index"""
    rename_map = {
        "Операционный денежный поток, млрд руб": "OCF, млрд руб",
        "Дивиденды/прибыль, %": "DPR, %",
        "Чистые активы, млрд руб": "Капитал, млрд руб",
        "Активы банка, млрд руб": "Активы, млрд руб",
        "Дивиденд, руб/акцию": "DPS, руб",
        "Дивиденд ап, руб/акцию": "P_DPS, руб",
        "Див доход, ао, %": "DY, %",
        "Див доход, ап, %": "P_DY, %",
        "Доходность FCF, %": "FCF/P, %",
        "Долг/EBITDA": "ND/EBITDA",
        "P/BV": "P/B"
    }
    
    # Create a new index with renamed metrics
    new_index = [rename_map.get(idx, idx) for idx in df.index]
    df.index = new_index
    
    return df


def download_data(ticker, standard="MSFO"):
    """
    Download annual and quarterly data for a given ticker
    
    Args:
        ticker (str): The ticker symbol to download data for
        standard (str): The reporting standard, either "MSFO" (IFRS) or "RSBU" (RAS)
    """
    # Validate and normalize the standard parameter
    if standard.upper() not in ["MSFO", "RSBU"]:
        raise ValueError("Standard must be either 'MSFO' or 'RSBU'")
    
    standard = standard.upper()
    
    annual_url = f"https://smart-lab.ru/q/{ticker}/f/y/{standard}/download/"
    quarterly_url = f"https://smart-lab.ru/q/{ticker}/f/q/{standard}/download/"
    
    print(f"Downloading {standard} annual data from {annual_url}")
    annual_response = requests.get(annual_url)
    if annual_response.status_code != 200:
        raise Exception(f"Failed to download annual data: HTTP {annual_response.status_code}")
    
    print(f"Downloading {standard} quarterly data from {quarterly_url}")
    quarterly_response = requests.get(quarterly_url)
    if quarterly_response.status_code != 200:
        raise Exception(f"Failed to download quarterly data: HTTP {quarterly_response.status_code}")
    
    # Save downloaded data to temporary files
    annual_path = f"{ticker}_{standard}_annual.csv"
    quarterly_path = f"{ticker}_{standard}_quarterly.csv"
    
    with open(annual_path, 'w', encoding='utf-8') as f:
        f.write(annual_response.text)
    
    with open(quarterly_path, 'w', encoding='utf-8') as f:
        f.write(quarterly_response.text)
    
    return annual_path, quarterly_path


def join_csv_files(annual_path, quarterly_path, output_path):
    """Join annual and quarterly CSV files according to requirements"""
    # Read CSV files
    annual_df = pd.read_csv(annual_path, sep=';', index_col=0)
    quarterly_df = pd.read_csv(quarterly_path, sep=';', index_col=0)
    
    # Detect half-years (when only Q2 and Q4 are present for a year)
    col_mapping = detect_and_convert_half_years(quarterly_df.columns)
    
    # Rename columns in quarterly_df if needed
    if col_mapping:
        quarterly_df = quarterly_df.rename(columns=col_mapping)
    
    # Preserve the order of metrics from both files
    all_metrics_ordered = OrderedDict()
    
    # First add all metrics from annual file in their original order
    for metric in annual_df.index:
        all_metrics_ordered[metric] = None
    
    # Then add any new metrics from quarterly file in their original order
    for metric in quarterly_df.index:
        if metric not in all_metrics_ordered:
            all_metrics_ordered[metric] = None
    
    # Create a new empty DataFrame with the combined metrics in order
    result_df = pd.DataFrame(index=list(all_metrics_ordered.keys()))
    
    # Get all columns from both dataframes
    all_columns = list(annual_df.columns) + list(quarterly_df.columns)
    
    # Create a dictionary of period values for sorting
    period_values = {col: get_period_value(col) for col in all_columns}
    
    # Sort columns chronologically
    ordered_columns = sorted(all_columns, key=lambda col: period_values[col])
    
    # Remove duplicates while preserving order
    ordered_columns = list(OrderedDict.fromkeys(ordered_columns))
    
    # Fill in the data from both DataFrames
    for col in ordered_columns:
        if col in annual_df.columns:
            # This is a year or LTM column from annual data
            result_df[col] = annual_df[col]
        elif col in quarterly_df.columns:
            # This is a quarter column from quarterly data
            result_df[col] = quarterly_df[col]
    
    # Clean values (remove spaces and replace comma decimal separators with dots)
    # Apply the cleaning function to each cell in the DataFrame
    for col in result_df.columns:
        result_df[col] = result_df[col].apply(clean_value)
    
    # Convert dates in "Дата отчета" row to yyyy-mm-dd format
    if "Дата отчета" in result_df.index:
        result_df.loc["Дата отчета"] = result_df.loc["Дата отчета"].apply(convert_date_format)
    
    # Rename specific metrics
    result_df = rename_metrics(result_df)
    
    # Save the result to a TSV file
    result_df.to_csv(output_path, sep='\t')
    print(f"Joined data saved to {output_path}")
    
    return result_df


def combine_standards(ticker, output_path):
    """
    Combine MSFO and RSBU data into a single TSV file
    with MSFO on top, RSBU on bottom, and 10 empty lines in between
    """
    # Download and process MSFO data
    print("Processing MSFO data...")
    msfo_annual_path, msfo_quarterly_path = download_data(ticker, "MSFO")
    msfo_df = join_csv_files(msfo_annual_path, msfo_quarterly_path, f"{ticker}_МСФО.tsv")
    
    # Download and process RSBU data
    print("Processing RSBU data...")
    rsbu_annual_path, rsbu_quarterly_path = download_data(ticker, "RSBU")
    rsbu_df = join_csv_files(rsbu_annual_path, rsbu_quarterly_path, f"{ticker}_РСБУ.tsv")
    
    # Combine columns from both standards, ensuring chronological order
    all_columns = list(msfo_df.columns) + list(rsbu_df.columns)
    period_values = {col: get_period_value(col) for col in all_columns}
    ordered_columns = sorted(all_columns, key=lambda col: period_values[col])
    ordered_columns = list(OrderedDict.fromkeys(ordered_columns))
    
    # Create empty dataframes with the combined columns
    msfo_combined = pd.DataFrame(index=msfo_df.index, columns=ordered_columns)
    rsbu_combined = pd.DataFrame(index=rsbu_df.index, columns=ordered_columns)
    
    # Fill in the data
    for col in ordered_columns:
        if col in msfo_df.columns:
            msfo_combined[col] = msfo_df[col]
        if col in rsbu_df.columns:
            rsbu_combined[col] = rsbu_df[col]
    
    # Create 10 empty lines
    empty_rows = pd.DataFrame(index=[f"empty_{i}" for i in range(10)], columns=ordered_columns)
    
    # Combine the dataframes (MSFO, empty lines, RSBU)
    combined_df = pd.concat([msfo_combined, empty_rows, rsbu_combined])
    
    # Save the combined result
    combined_df.to_csv(output_path, sep='\t')
    print(f"Combined data (MSFO + RSBU) saved to {output_path}")
    
    # Clean up temporary files
    cleanup_temp_files(msfo_annual_path, msfo_quarterly_path)
    cleanup_temp_files(rsbu_annual_path, rsbu_quarterly_path)


def cleanup_temp_files(annual_path, quarterly_path):
    """Clean up temporary downloaded files"""
    try:
        if os.path.exists(annual_path):
            os.remove(annual_path)
        if os.path.exists(quarterly_path):
            os.remove(quarterly_path)
    except Exception as e:
        print(f"Warning: Failed to clean up temporary files: {e}")


def main():
    parser = argparse.ArgumentParser(description='Join annual and quarterly financial metrics for a ticker.')
    parser.add_argument('ticker', help='Ticker symbol to download data for (e.g., MGKL)')
    parser.add_argument('--standard', choices=['МСФО', 'РСБУ', 'MSFO', 'RSBU', 'BOTH', 'ОБА'], default='BOTH',
                      help='Reporting standard to use: МСФО/MSFO (IFRS), РСБУ/RSBU (RAS), or BOTH/ОБА. Default is BOTH.')
    
    args = parser.parse_args()
    
    # Map both Cyrillic and Latin standard names to API parameter values
    standard_map = {
        'МСФО': 'MSFO',
        'РСБУ': 'RSBU',
        'MSFO': 'MSFO',
        'RSBU': 'RSBU',
        'BOTH': 'BOTH',
        'ОБА': 'BOTH'
    }
    
    # Display standard map for output filename
    display_standard_map = {
        'МСФО': 'МСФО',
        'РСБУ': 'РСБУ',
        'MSFO': 'МСФО',
        'RSBU': 'РСБУ',
        'BOTH': 'COMBINED',
        'ОБА': 'COMBINED'
    }
    
    # Get the API parameter value for the selected standard
    standard = standard_map[args.standard]
    
    # Use ticker and standard for output filename
    if standard == 'BOTH':
        output_path = f"{args.ticker}_COMBINED.tsv"
    else:
        output_path = f"{args.ticker}_{display_standard_map[args.standard]}.tsv"
    
    try:
        if standard == 'BOTH':
            # Combine both MSFO and RSBU data
            combine_standards(args.ticker, output_path)
        else:
            # Process single standard
            annual_path, quarterly_path = download_data(args.ticker, standard)
            join_csv_files(annual_path, quarterly_path, output_path)
            cleanup_temp_files(annual_path, quarterly_path)
            
    except Exception as e:
        print(f"Error: {e}")
        # Clean up any temporary files in case of error
        if standard != 'BOTH' and 'annual_path' in locals() and 'quarterly_path' in locals():
            cleanup_temp_files(annual_path, quarterly_path)
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main()) 