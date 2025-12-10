# NREL-Data-Extraction
**NREL NSRDB Bulk Downloader**

This repository contains a utility script for downloading large batches of NSRDB (NREL) time series solar data. It is intended for workflows where you need to pull data across a full grid, for example when mapping solar resources for Vietnam or other regions.

The script automates API calls, handles retries, avoids corrupt files, and lets you restart runs without losing progress.

**Why this script exists**

Downloading NSRDB data manually or with simple loops can be unreliable. The API rate limits, requests fail randomly, and partial files can be written if the process is interrupted.

**This tool aims to make bulk downloads reliable by providing:**

A configurable latitude and longitude grid

Support for multiple years in one run

Automatic retries with backoff

Atomic file writing using temporary .part files

The ability to stop and restart without re-downloading successful files

Simple error logs for debugging

**Features****:**

Downloads time series solar resource data for a full geographic grid

One CSV per combination of year, latitude, and longitude

Automatic retries if API errors occur, including HTTP 429

Writes files safely using .part files to prevent corruption

Skips valid existing files when restarting

Generates .err.txt files for points that fail to download

**Data source**

This tool uses the NSRDB PSM v3 time series endpoint:

https://developer.nrel.gov/api/nsrdb/v2/solar/psm3-download.csv

Check the NREL documentation for the attribute list and usage requirements.

**Repository layout:**
nsrdb_bulk_download.py        # main script
README.md
requirements.txt
dev-requirements.txt

env.txt                       # example environment variables
config.yaml.txt               # example config file
environment.yaml.txt          # optional template

**Requirements**

Python 3.10 or higher

A valid NREL API key and associated registration details

Python packages used in the script:

requests

PyYAML

tenacity

tqdm

python-dotenv

Install them with:

pip install requests pyyaml tenacity tqdm python-dotenv


Or install everything from a requirements file:

pip install -r requirements.txt

**Configuration:**

The script reads its settings from:

data_ingest/nsrdb_bulk/config.yaml


**Example configuration:**

out_dir: "data/nsrdb_vn"

years: [2019, 2020, 2021]

bbox:
  lat_min: 8.0
  lat_max: 24.5
  lon_min: 102.0
  lon_max: 110.0

grid_deg:
  dlat: 0.25
  dlon: 0.25

interval: 60
utc: true
leap_day: false

attributes:
  - ghi
  - dni
  - dhi
  - wind_speed
  - air_temperature

sleep_between_calls_seconds: 0.25

**Environment variables:**

**Place these in a .env file in the project root:**

NREL_API_KEY=your_api_key_here
NSRDB_EMAIL=you@example.com
NSRDB_FULL_NAME=Your Name
NSRDB_AFFILIATION=Your Org
NSRDB_REASON=Solar resource mapping


The script will load and validate them before running.

**How to run the downloader**

Run from the repository root:

python nsrdb_bulk_download.py


**The script will:**

Load environment variables

Read the YAML configuration

Build the list of coordinates and years

Download each point into the folder specified by out_dir

Output files follow the pattern:

<out_dir>/<year>/nsrdb_<year>_<lat>_<lon>.csv


**If a download fails, a file named:**

nsrdb_<year>_<lat>_<lon>.err.txt


will appear next to the CSV.

Runs can be interrupted safely. When restarted, the script skips any valid existing files.

Example output
data/nsrdb_vn/2019/nsrdb_2019_16.2500_107.5000.csv
data/nsrdb_vn/2020/nsrdb_2020_16.2500_107.5000.csv
data/nsrdb_vn/2019/nsrdb_2019_16.2500_107.5000.err.txt

**Notes and tips**

Increase sleep_between_calls_seconds if the API rate limits frequently

Smaller grid spacing will dramatically increase the number of requests

Check NREL docs for valid attribute names

Invalid or empty CSV files are discarded automatically so they can be retried

**Troubleshooting:**

If environment variables are missing, the script will print a message listing which ones need to be added

If a CSV is empty or malformed, the script removes it and logs the error

If paths are missing, make sure the directory data_ingest/nsrdb_bulk exists and contains config.yaml

**Planned improvements**

Command line switches for overriding the config path

A dry run mode for estimating the number of requests

More detailed logging

Support for additional regional solar datasets

**Acknowledgements**

Solar data is provided by the National Renewable Energy Laboratory NSRDB project. Please follow NREL usage guidelines.
