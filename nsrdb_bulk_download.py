import os
import time
import csv
import pathlib
import requests
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm import tqdm
from dotenv import load_dotenv

"""
Bulk-download NSRDB time series over a lat/lon grid for Vietnam.
One CSV per (year, lat, lon). Safe to stop/resume.

Endpoint (PSM v3 time-series):
  https://developer.nrel.gov/api/nsrdb/v2/solar/psm3-download.csv
Docs: one POINT(lon lat) per request; loop over grid.
"""

def load_config(path="data_ingest/nsrdb_bulk/config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)

class ApiError(Exception):
    pass

@retry(
    reraise=True,
    retry=retry_if_exception_type(ApiError),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(6),
)
def fetch_csv(url, params, out_path: pathlib.Path):
    resp = requests.get(url, params=params, timeout=120, stream=True)
    if resp.status_code == 429:
        raise ApiError("Rate limited (429). Retrying...")
    if resp.status_code >= 400:
        raise ApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    tmp = out_path.with_suffix(".part")
    with open(tmp, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 14):
            if chunk:
                f.write(chunk)
    tmp.replace(out_path)

def frange(start, stop, step):
    x = start
    while x <= stop + 1e-9:
        yield x
        x += step

def generate_points(bbox, dlon, dlat):
    lons = list(frange(bbox["lon_min"], bbox["lon_max"], dlon))
    lats = list(frange(bbox["lat_min"], bbox["lat_max"], dlat))
    for lat in lats:
        for lon in lons:
            yield round(lat, 6), round(lon, 6)

def build_params(year, lat, lon, cfg, env):
    attrs = ",".join(cfg["attributes"])
    return {
        "wkt": f"POINT({lon} {lat})",
        "names": str(year),
        "interval": int(cfg["interval"]),
        "utc": str(cfg["utc"]).lower(),
        "leap_day": str(cfg["leap_day"]).lower(),
        "attributes": attrs,
        "email": env["NSRDB_EMAIL"],
        "full_name": env["NSRDB_FULL_NAME"],
        "affiliation": env["NSRDB_AFFILIATION"],
        "reason": env["NSRDB_REASON"],
        "mailing_list": "false",
        "api_key": env["NREL_API_KEY"],
    }

def looks_like_valid_csv(path: pathlib.Path) -> bool:
    try:
        with open(path, newline="", encoding="utf-8", errors="ignore") as f:
            r = csv.reader(f)
            header = next(r, None)
            return bool(header) and any(("GHI" in h.upper()) for h in header)
    except Exception:
        return False

def main():
    load_dotenv()
    needed = ["NREL_API_KEY","NSRDB_EMAIL","NSRDB_FULL_NAME","NSRDB_AFFILIATION","NSRDB_REASON"]
    missing = [k for k in needed if not os.getenv(k)]
    if missing:
        raise SystemExit(f"Missing env vars: {missing}. Fill them in .env")

    env = {k: os.getenv(k) for k in needed}
    cfg = load_config()

    base_url = "https://developer.nrel.gov/api/nsrdb/v2/solar/psm3-download.csv"
    out_root = pathlib.Path(cfg["out_dir"])
    ensure_dir(out_root)

    years = cfg["years"]
    bbox = cfg["bbox"]
    dlon = float(cfg["grid_deg"]["dlon"])
    dlat = float(cfg["grid_deg"]["dlat"])
    sleep_s = float(cfg.get("sleep_between_calls_seconds", 0.25))

    points = list(generate_points(bbox, dlon, dlat))
    print(f"Planned requests: {len(points) * len(years)} "
          f"({len(points)} points × {len(years)} years)")

    for year in years:
        year_dir = out_root / f"{year}"
        ensure_dir(year_dir)
        for lat, lon in tqdm(points, desc=f"Year {year}"):
            fname = f"nsrdb_{year}_{lat:.4f}_{lon:.4f}.csv"
            out_path = year_dir / fname

            if out_path.exists() and looks_like_valid_csv(out_path):
                continue

            params = build_params(year, lat, lon, cfg, env)
            try:
                fetch_csv(base_url, params, out_path)
                if not looks_like_valid_csv(out_path):
                    out_path.unlink(missing_ok=True)
                    raise ApiError("Downloaded file didn’t look like NSRDB CSV; will retry later.")
            except Exception as e:
                with open(out_path.with_suffix(".err.txt"), "w", encoding="utf-8") as ef:
                    ef.write(str(e))
            time.sleep(sleep_s)

    print("Done.")

if __name__ == "__main__":
    main()
