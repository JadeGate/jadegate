---
name: csv-data-analysis
description: Read and analyze CSV files with column stats, filtering and sorting
---

# CSV Data Analysis

Read and analyze CSV files with column stats, filtering and sorting

## When to Use

- User wants to analyze csv
- User wants to csv analysis
- Keywords: csv, data, analysis, statistics

## Required Parameters

- **file_path** (string): Path to CSV file
- **operation** (string): Operation: summary, filter, sort

## Output

- **rows** (number): Total rows
- **columns** (array): Column names
- **result** (string): Analysis result

## Security

- Sandbox level: strict
- Max execution time: 30000ms
- JadeGate verified: Yes (5-layer security check passed)

## Execution Flow

Entry: `read_csv` -> 6 steps -> Exit: `ret_ok`, `ret_fail`
