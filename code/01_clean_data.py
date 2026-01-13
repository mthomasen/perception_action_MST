# code/01_clean_data.py
from __future__ import annotations
from pathlib import Path
from collections import Counter
import pandas as pd

from src.functions import _norm_str, _as_lower, _coalesce_columns

base_path = Path(__file__).resolve().parents[1]
in_csv = base_path / "data" / "raw" / "en.openfoodfacts.org.products.csv.gz"
out_dir = base_path / "data" / "processed"
out_dir.mkdir(parents=True, exist_ok=True)

out_csv = out_dir / "off_dk_clean.csv"

if not in_csv.exists():
    raise SystemExit(f"[ERR] Raw OFF file not found: {in_csv}")

chunk_Size = 200_000

preferred_cols = [
    "product_name", "product_name_en", "product_name_da",
    "brands",
    "categories_tags",
    "main_category", "main_category_en",
    "labels_tags",
    "languages_tags",
    "countries_tags",
    "lc",
    "ecoscore_grade",
    "environmental_score_grade",
    "ecoscore_score",
]

def looks_dk(countries: pd.Series) -> pd.Series:
    s = countries.fillna("").str.lower()
    return (
        s.str.contains(r"(?:^|,)\s*dk\s*(?:,|$)", regex=True)
        | s.str.contains("denmark")
        | s.str.contains("da:denmark")
    )

print(f"[INFO] Reading in chunks of {chunk_Size:,} rows from: {in_csv}")

n_rows_raw_total = 0
n_rows_kept_total = 0
first_chunk = True

reader = pd.read_csv(
    in_csv,
    sep="\t",
    compression="infer",
    low_memory=False,
    chunksize=chunk_Size,
    on_bad_lines="skip",
    dtype=str,
)

for i, df in enumerate(reader, start=1):
    n_chunk_raw = len(df)
    n_rows_raw_total += n_chunk_raw

    # ensure all preferred columns exist
    for c in preferred_cols:
        if c not in df.columns:
            df[c] = pd.NA

    # core names
    df["product_name"] = _coalesce_columns(
        df, "product_name", ["product_name_da", "product_name_en"]
    ).map(_norm_str)

    if "product_name_da" in df.columns:
        df["product_name_da"] = df["product_name_da"].map(_norm_str)
    else:
        df["product_name_da"] = ""

    # tag-ish fields
    for col in ["labels_tags", "languages_tags", "countries_tags", "categories_tags"]:
        df[col] = df[col].map(_as_lower)

    # main_category_en
    if "main_category_en" in df.columns:
        df["main_category_en"] = df["main_category_en"].map(_norm_str)
    elif "main_category" in df.columns:
        df["main_category_en"] = df["main_category"].map(_norm_str)
    else:
        df["main_category_en"] = ""

    # lc
    if "lc" in df.columns:
        df["lc"] = df["lc"].map(_as_lower)
    else:
        df["lc"] = ""

    # DK filter
    dk_mask = looks_dk(df["countries_tags"])
    df = df[dk_mask].copy()

    # drop empty names
    before = len(df)
    df = df[df["product_name"].str.strip() != ""].copy()
    after = len(df)
    dropped = n_chunk_raw - after
    n_rows_kept_total += after

    keep = [
        "product_name",
        "product_name_da",
        "brands",
        "categories_tags",
        "main_category",
        "main_category_en",
        "labels_tags",
        "languages_tags",
        "countries_tags",
        "lc",
        "ecoscore_grade",
        "environmental_score_grade",
        "ecoscore_score",
    ]
    present = [c for c in keep if c in df.columns]
    df_out = df[present].copy()

    mode = "w" if first_chunk else "a"
    header = first_chunk
    df_out.to_csv(out_csv, index=False, mode=mode, header=header)
    first_chunk = False

    print(
        f"[CHUNK {i:3d}] raw={n_chunk_raw:6d}  kept={after:6d}  "
        f"dropped={dropped:6d}"
    )

print(f"[DONE] Raw rows total:   {n_rows_raw_total:,}")
print(f"[DONE] Kept rows total:  {n_rows_kept_total:,}")
print(f"[OK] Final clean DK file: {out_csv}")
