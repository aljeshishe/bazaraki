from datetime import date
from glob import glob
from pathlib import Path
import numpy as np
import pandas as pd

from parse import parse


# A crawl holding less than this share of the rubrics it covers was cut short.
MIN_RUN_RATIO = 0.5


def filter_in(df, query: str) -> pd.DataFrame:
    found = df.query(query)
    print(f"removing {len(df) - len(found)}/{len(df)} rows")
    return found


def read_jsonl_files(path: str):
    merged = pd.DataFrame()
    for file_name in sorted(glob("output/*.jsonl")):
        print(f"Reading {file_name}")
        result = parse("output/{date} {time} {postfix}", file_name)
        if result is None:
            print(f"Failed to parse {file_name}")
            continue
        if result["postfix"].startswith("fast"):
            print(f"Skipping fast run")
            continue
        dt = date.fromisoformat(result["date"])
        
        newdf = pd.read_json(file_name, lines=True)
        assert newdf.ad_id.duplicated().sum() == 0, "Expected no duplicates"
        newdf.set_index("ad_id", inplace=True)
        if merged.empty:
            merged = newdf
            merged["delete_date"] = np.nan
            continue
        
        condition = ~merged.index.isin(newdf.index) & merged['delete_date'].isna()
        merged.loc[condition, 'delete_date'] = dt
        new_deleted_count = condition.sum()

        new = newdf.index.difference(merged.index)
        merged = pd.concat([merged, newdf.loc[new]])
        print(f"Total: {len(merged)} read: {len(newdf)} new: {len(new)} deleted: {new_deleted_count}")
    return merged

def read_last_df(glob_pattern: str):
    # Skip fast runs, same as read_dfs: they hold one page per rubric, not a full crawl.
    files = [f for f in sorted(glob(glob_pattern))
             if not Path(f).name.split(" ")[-1].startswith("fast")]
    if not files:
        raise ValueError(f"No files found for pattern: {glob_pattern}")
    last_file = files[-1]
    print(f"Reading last file: {last_file}")
    return read_df(last_file)

def read_dfs(glob_pattern: str):
    """Reads multiple files by glob_pattern.
    For deleted items sets delete_date
    """
    merged = pd.DataFrame()
    for file_name in sorted(glob(glob_pattern)):
        print(f"Reading {file_name}")
        result = parse("output/{date} {time} {postfix}", file_name)
        if result is None:
            print(f"Failed to parse {file_name}")
            continue
        if result["postfix"].startswith("fast"):
            print(f"Skipping fast run")
            continue
        dt = date.fromisoformat(result["date"])
        
        newdf = read_df(file_name)
        if "ad_id" not in newdf.columns:
            # A crawl that scraped nothing still writes a file; skip it rather than
            # treating every ad as deleted that day.
            print(f"Skipping empty run ({len(newdf)} rows)")
            continue
        # Some runs cover a single rubric (rent only), so judge completeness — and later
        # absence — against the rubrics this run actually crawled, never the whole market.
        covered = (merged.cat0.isin(newdf.cat0.dropna().unique())
                   if len(merged) and "cat0" in merged and "cat0" in newdf
                   else pd.Series(True, index=merged.index))
        if len(merged) and len(newdf) < covered.sum() * MIN_RUN_RATIO:
            # An interrupted crawl would otherwise mark most of the market as deleted
            # for that day, and delete_date drives the age/time-to-rent numbers.
            print(f"Skipping partial run ({len(newdf)} rows vs {covered.sum()} known in its rubrics)")
            continue
        assert newdf.ad_id.duplicated().sum() == 0, "Expected no duplicates"
        newdf.set_index("ad_id", inplace=True)
        if merged.empty:
            merged = newdf
            merged["delete_date"] = np.nan
            continue
        
        # if delete_date is set in merged, but ad is present in newdf, reset delete_date
        condition = merged.index.isin(newdf.index) & merged['delete_date'].notna()
        merged.loc[condition, 'delete_date'] = np.nan
        undeleted_count = condition.sum()
        
        # if delete_date is not set in merged, but ad is missing in newdf, set delete_date
        condition = ~merged.index.isin(newdf.index) & merged['delete_date'].isna() & covered
        merged.loc[condition, 'delete_date'] = dt
        new_deleted_count = condition.sum()

        new = newdf.index.difference(merged.index)
        merged = pd.concat([merged, newdf.loc[new]])
        valid = merged.delete_date.isna().sum()
        print(f"Total: {len(merged)} valid: {valid} read: {len(newdf)} new: {len(new)} deleted: {new_deleted_count} undeleted: {undeleted_count}")
    return merged

# In 2026 bazaraki rebuilt its frontend and renamed things: categories lost their
# "for sale"/"to rent" suffix and location switched its separator from "," to " — ".
# Crawls since then carry the new spelling, everything before it the old one, and
# read_dfs concatenates both — so normalise on read and keep one vocabulary.
LEGACY_CATEGORIES = {
    "Real Estate to rent": "Cyprus real estate to rent",
    "Real Estate for sale": "Cyprus real estate for sale",
}
# Only these two rubrics ever carried the suffix; "Plots of land", "Commercial property",
# "Short term" and friends never did.
SUFFIXED_RUBRICS = ["Apartments, flats", "Houses"]


def to_legacy_format(df):
    """Spell a crawl the way the pre-2026 ones were spelled.

    A no-op on older files, and idempotent, so it is safe to apply to anything.
    """
    if "location" in df:
        df["location"] = df.location.str.replace(" — ", ", ", regex=False)
    if "title" in df:
        df["title"] = df.title.str.strip()
    if "price" in df:
        df["price"] = df.price.astype(float)
    if "cat0" in df and "cat1" in df:
        df["cat0"] = df.cat0.map(LEGACY_CATEGORIES).fillna(df.cat0)
        suffix = np.where(df.cat0.str.endswith("to rent"), " to rent", " for sale")
        df["cat1"] = np.where(df.cat1.isin(SUFFIXED_RUBRICS), df.cat1 + suffix, df.cat1)
    return df


def read_df(file_name: str | Path):
    file_path = Path(file_name) if not isinstance(file_name, Path) else file_name
    if file_path.suffix == ".jsonl":
        df = pd.read_json(file_path, lines=True)
    elif file_path.suffix == ".json":
        df = pd.read_json(file_path, lines=False)
    elif file_path.suffix == ".parquet":
        df = pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")
    return to_legacy_format(df)
    
def add_city_disctrict_cols(df):
    # n=1: a district may itself contain a comma, the city never does.
    df[["city", "district"]] = df.location.str.split(",", n=1, expand=True)
    return df

def enrich(df):
    """Enrich data frame with additional columns.
    location -> city, district
    price / Property area - price_per_sqm
    """
    df[["city", "district"]] = df.location.str.split(",", expand=True)
    df["price_per_sqm"] = df.price / (df["Property area"]).round(2)
    return df
