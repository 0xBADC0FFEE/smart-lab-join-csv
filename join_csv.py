#!/usr/bin/env python3
import pandas as pd
import argparse
import re
import os
import requests
from collections import OrderedDict
from datetime import datetime


def is_year_column(col_name):
    """Check if column name is a year (like '2022')"""
    return bool(re.match(r'^20\d{2}$', str(col_name)))


def is_quarter_column(col_name):
    """Check if column name is a quarter (like '2022Q4')"""
    return bool(re.match(r'^20\d{2}Q[1-4]$', str(col_name)))


def get_year_from_quarter(quarter_col):
    """Extract year from a quarter column name (e.g., '2022Q4' -> '2022')"""
    match = re.match(r'^(20\d{2})Q[1-4]$', quarter_col)
    if match:
        return match.group(1)
    return None


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
    
    # Group columns by year and quarter
    year_columns = {}  # year -> column name
    quarter_columns = {}  # (year, quarter) -> column name
    
    # Get all year columns from annual data
    for col in annual_df.columns:
        if is_year_column(col):
            year_columns[col] = col
    
    # Get all quarter columns from quarterly data
    for col in quarterly_df.columns:
        if is_quarter_column(col):
            year = get_year_from_quarter(col)
            quarter = col[-1]  # Get the quarter number (1-4)
            quarter_columns[(year, quarter)] = col
    
    # Sort years to ensure chronological order
    sorted_years = sorted(year_columns.keys())
    
    # Create ordered list of columns for the result DataFrame
    ordered_columns = []
    
    # Add quarters and corresponding years
    for year in sorted_years:
        # Add Q1-Q3 for this year if they exist
        for quarter in ['1', '2', '3']:
            if (year, quarter) in quarter_columns:
                ordered_columns.append(quarter_columns[(year, quarter)])
        
        # Only add Q4 if it exists AND the corresponding year is not in annual data
        # Otherwise, we'll use the annual year data
        if (year, '4') in quarter_columns:
            # If quarterly.csv contains only Q4 quarter of a year and annual.csv has the same year,
            # skip the Q4 quarter and use only the year column from annual.csv
            
            # Check if this year has only Q4 quarter in quarterly data
            has_other_quarters = any((year, q) in quarter_columns for q in ['1', '2', '3'])
            
            # If there are no other quarters for this year and the year exists in annual data,
            # skip the Q4 column. Otherwise add it.
            if has_other_quarters or year not in year_columns:
                ordered_columns.append(quarter_columns[(year, '4')])
        
        # Add the year column after Q4
        if year in year_columns:
            ordered_columns.append(year)
    
    # Add LTM column at the end
    if 'LTM' in annual_df.columns:
        ordered_columns.append('LTM')
    
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
    parser.add_argument('--standard', choices=['МСФО', 'РСБУ', 'MSFO', 'RSBU'], default='МСФО',
                      help='Reporting standard to use: МСФО/MSFO (IFRS) or РСБУ/RSBU (RAS). Default is МСФО.')
    
    args = parser.parse_args()
    
    # Map both Cyrillic and Latin standard names to API parameter values
    standard_map = {
        'МСФО': 'MSFO',
        'РСБУ': 'RSBU',
        'MSFO': 'MSFO',
        'RSBU': 'RSBU'
    }
    
    # Display standard map for output filename
    display_standard_map = {
        'МСФО': 'МСФО',
        'РСБУ': 'РСБУ',
        'MSFO': 'МСФО',
        'RSBU': 'РСБУ'
    }
    
    # Get the API parameter value for the selected standard
    standard = standard_map[args.standard]
    
    # Use ticker and standard for output filename (use display format for the filename)
    output_path = f"{args.ticker}_{display_standard_map[args.standard]}.tsv"
    
    try:
        # Download data from the internet
        annual_path, quarterly_path = download_data(args.ticker, standard)
        
        # Process the files
        join_csv_files(annual_path, quarterly_path, output_path)
        
        # Clean up temporary files
        cleanup_temp_files(annual_path, quarterly_path)
            
    except Exception as e:
        print(f"Error: {e}")
        # Clean up any temporary files in case of error
        if 'annual_path' in locals() and 'quarterly_path' in locals():
            cleanup_temp_files(annual_path, quarterly_path)
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main()) 