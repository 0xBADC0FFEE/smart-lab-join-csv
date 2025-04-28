#!/usr/bin/env python3
import pandas as pd
import argparse
import re
from collections import OrderedDict


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
    
    # Save the result to a TSV file
    result_df.to_csv(output_path, sep='\t')
    print(f"Joined data saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Join annual and quarterly CSV files.')
    parser.add_argument('annual', help='Path to the annual CSV file')
    parser.add_argument('quarterly', help='Path to the quarterly CSV file')
    parser.add_argument('output', help='Path to the output TSV file')
    
    args = parser.parse_args()
    
    join_csv_files(args.annual, args.quarterly, args.output)


if __name__ == '__main__':
    main() 