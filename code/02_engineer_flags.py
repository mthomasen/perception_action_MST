from __future__ import annotations
from pathlib import Path
import re
import pandas as pd

from src.functions import (
    _norm_str,
    _as_lower,
    _derive_eco_score,
    derive_eco_signal,
    derive_organic_label,
    looks_danish_text,
    _series_or_empty,
)

base_path = Path(__file__).resolve().parents[1]
in_csv  = base_path / "data" / "processed" / "off_dk_clean.csv"
out_csv = base_path / "data" / "processed" / "off_flags_dk.csv"

if not in_csv.exists():
    raise SystemExit(f"[ERR] Clean DK file not found: {in_csv}")

print(f"[INFO] Loading clean DK data from: {in_csv}")
df = pd.read_csv(in_csv, low_memory=False)
print(f"[INFO] Loaded shape = {df.shape}")

# ----------------------------------------------------------------------
# Re-normalise key string columns to avoid literal "nan" strings
# ----------------------------------------------------------------------
for col in ["product_name", "product_name_da"]:
    if col in df.columns:
        df[col] = df[col].map(_norm_str)

for col in ["labels_tags", "languages_tags", "countries_tags", "categories_tags"]:
    if col in df.columns:
        df[col] = df[col].map(_as_lower)

if "lc" in df.columns:
    df["lc"] = df["lc"].map(_as_lower)

# ----------------------------------------------------------------------
# eco_score + eco_signal
# ----------------------------------------------------------------------
df["eco_score"] = _derive_eco_score(df)
df["eco_signal"] = derive_eco_signal(df)

# ----------------------------------------------------------------------
# organic_badge
# ----------------------------------------------------------------------
df["organic_badge"] = derive_organic_label(df)

# ----------------------------------------------------------------------
# lang_da
# ----------------------------------------------------------------------
lang_tags = _series_or_empty(df, "languages_tags").str.lower().fillna("")
lc = df.get("lc", "").astype(str).str.lower().fillna("")

name_da = df.get("product_name_da", "").map(_norm_str)
name_any = df.get("product_name", "").map(_norm_str)

is_lang_da = lang_tags.str.contains(r"(?:^|[,;:])da(?:$|[,;:])", regex=True)
is_lc_da = lc.eq("da")
has_da_name = name_da != ""
looks_dk_name = name_da.map(looks_danish_text) | name_any.map(looks_danish_text)

df["lang_da"] = (is_lang_da | is_lc_da | has_da_name | looks_dk_name).astype(int)

# ----------------------------------------------------------------------
# green_words
# ----------------------------------------------------------------------
GREEN_REGEX = re.compile(
    r"(?:økologisk|økologi|organic|bio|plante|plant[-\s]?based|"
    r"vegansk|vegan|vegetar|bæredygtig|klima|eco|green|natural)",
    flags=re.IGNORECASE,
)

# Prefer Danish name if present; otherwise fallback to any product name
display_name = name_da.where(name_da != "", name_any)
df["product_name"] = display_name  # this time, cleaned (no literal "nan")

df["green_words"] = display_name.str.contains(GREEN_REGEX, regex=True).astype(int)

# ----------------------------------------------------------------------
# category
# ----------------------------------------------------------------------
cat = df.get("main_category_en")
if cat is None or cat.isna().all():
    cat = df.get("main_category")
if cat is None:
    cat = df["categories_tags"].fillna("").astype(str).str.split(",").str[0]
    cat = cat.str.replace(r"^[a-z]{2}:", "", regex=True)

cat = cat.fillna("").astype(str).str.strip()
cat = cat.replace("", "unknown")
df["category"] = cat

# ----------------------------------------------------------------------
# drop empty names and save
# ----------------------------------------------------------------------
df = df[df["product_name"].str.strip() != ""].copy()

keep = [
    "product_name",
    "eco_score",
    "eco_signal",
    "organic_badge",
    "lang_da",
    "green_words",
    "category",
    "labels_tags",
    "languages_tags",
    "countries_tags",
]
df_out = df[keep].copy()

df_out.to_csv(out_csv, index=False)
print(f"[OK] Saved flags file: {out_csv}  shape={df_out.shape}")

print("\n[SUMMARY] eco_score:")
print(df_out["eco_score"].value_counts(dropna=False))

print("\n[SUMMARY] organic_badge (0/1):")
print(df_out["organic_badge"].value_counts(dropna=False))

print("\n[SUMMARY] eco_signal (0/1):")
print(df_out["eco_signal"].value_counts(dropna=False))

print("\n[SUMMARY] lang_da (0/1):")
print(df_out["lang_da"].value_counts(dropna=False))

print("\n[SUMMARY] green_words (0/1):")
print(df_out["green_words"].value_counts(dropna=False))

print("\n[DONE] 02_engineer_flags complete.")
