from datetime import date
from glob import glob
from pathlib import Path
import numpy as np
import pandas as pd

from parse import parse


def filter_in(df, query: str) -> pd.DataFrame:
    found = df.query(query)
    print(f"removing {len(df) - len(found)}/{len(df)} rows")
    return found


def read_jsonl_files(path: str):
    DT_LEN = len("2024-12-12 18:34:25")
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

def read_dfs(glob_pattern: str):
    DT_LEN = len("2024-12-12 18:34:25")
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

def read_df(file_name: str | Path):
    file_path = Path(file_name) if not isinstance(file_name, Path) else file_name
    if file_path.suffix == ".jsonl":
        return pd.read_json(file_path, lines=True)
    elif file_path.suffix == ".json":
        return pd.read_json(file_path, lines=False)
    elif file_path.suffix == ".parquet":
        return pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")