from __future__ import annotations
from pathlib import Path
import argparse
import sys
import pandas as pd
import numpy as np

base_path = Path(__file__).resolve().parents[1]
default_in = base_path / "data" / "processed" / "stimulus_set.csv"

required_cols = [
    "item_id",
    "product_name",
    "organic_badge",
    "salience",
    "eco_signal",
    "eco_score",
    "lang_da",
    "green_words",
    "category",
]

valid_salience = {"low", "high"}
valid_eco_scores = {"a", "b", "c", "d", "e"}


def fail(msg: str) -> None:
    print(f"[qc fail] {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"[qc warn] {msg}")


def ok(msg: str) -> None:
    print(f"[qc ok] {msg}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inpath", default=str(default_in))
    ap.add_argument("--n_trials", type=int, default=160)
    ap.add_argument(
        "--max_name_dups",
        type=int,
        default=10,
        help="max allowed number of duplicated product_name rows",
    )
    args = ap.parse_args()

    in_path = Path(args.inpath)
    if not in_path.exists():
        fail(f"stimulus file not found: {in_path}")

    df = pd.read_csv(in_path, low_memory=False)
    n = len(df)
    print(f"[info] loaded {in_path} with {n} rows")

    # required columns
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        fail(f"missing required columns: {missing}")
    ok("all required columns present")

    if n != args.n_trials:
        warn(f"n_trials != expected ({n} vs {args.n_trials})")

    # item_id checks
    try:
        item_id = pd.to_numeric(df["item_id"], errors="raise").astype(int)
    except Exception:
        fail("item_id not fully numeric / int-convertible")

    if item_id.duplicated().any():
        ex = df.loc[item_id.duplicated(keep=False), ["item_id", "product_name"]].head(10)
        fail("duplicate item_id values found:\n" + ex.to_string(index=False))
    ok("item_id unique")

    # product_name checks
    name = df["product_name"].astype(str).fillna("").str.strip()
    if (name == "").any():
        fail("some rows have empty product_name")
    ok("product_name non-empty")

    dup_rows = int(name.duplicated().sum())
    if dup_rows > 0:
        msg = f"found {dup_rows} duplicated product_name rows"
        if dup_rows > args.max_name_dups:
            fail(msg + f" (max_name_dups={args.max_name_dups})")
        else:
            warn(msg + f" (allowed up to {args.max_name_dups})")
    else:
        ok("no duplicated product_name")

    # binary columns
    for col in ["organic_badge", "eco_signal", "lang_da", "green_words"]:
        vals = set(pd.to_numeric(df[col], errors="coerce").dropna().unique().tolist())
        if not vals.issubset({0, 1}):
            fail(f"{col} has values outside 0/1: {sorted(vals)}")
    ok("binary columns valid")

    # salience
    sal = df["salience"].astype(str).str.strip().str.lower()
    if not set(sal.unique()).issubset(valid_salience):
        bad = df.loc[~sal.isin(valid_salience), ["item_id", "salience"]].head(10)
        fail("invalid salience values:\n" + bad.to_string(index=False))
    ok("salience valid")

    # eco_score
    eco = df["eco_score"].astype(str).str.strip().str.lower()
    if not set(eco.unique()).issubset(valid_eco_scores):
        bad = df.loc[~eco.isin(valid_eco_scores), ["item_id", "eco_score"]].head(10)
        fail("invalid eco_score values:\n" + bad.to_string(index=False))
    ok("eco_score valid")

    # eco_signal consistency
    implied = eco.isin({"a", "b"}).astype(int)
    eco_sig = pd.to_numeric(df["eco_signal"], errors="coerce").fillna(-1).astype(int)
    mismatch = implied.ne(eco_sig)
    if mismatch.any():
        bad = df.loc[mismatch, ["item_id", "eco_score", "eco_signal"]].head(10)
        fail("eco_signal inconsistent with eco_score:\n" + bad.to_string(index=False))
    ok("eco_signal consistent with eco_score")

    # balance checks
    org = pd.to_numeric(df["organic_badge"], errors="coerce").astype(int)
    eco_s = pd.to_numeric(df["eco_signal"], errors="coerce").astype(int)

    cell_counts = df.groupby([org, eco_s]).size().sort_index()
    print("\n[info] cell counts (organic_badge × eco_signal):")
    print(cell_counts.to_string())

    expected_cells = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for c in expected_cells:
        if c not in cell_counts.index:
            fail(f"missing cell {c}")

    if cell_counts.max() != cell_counts.min():
        warn("4-cell balance not perfectly equal")
    else:
        ok("4-cell balance perfect")

    cell_sal = df.groupby([org, eco_s, sal]).size().sort_index()
    print("\n[info] cell × salience counts:")
    print(cell_sal.to_string())

    for c in expected_cells:
        low = int(cell_sal.get((c[0], c[1], "low"), 0))
        high = int(cell_sal.get((c[0], c[1], "high"), 0))
        if low != high:
            warn(f"cell {c} salience imbalance (low={low}, high={high})")

    ok("qc completed successfully")


if __name__ == "__main__":
    main()
