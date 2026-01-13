from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
# Desired *total* number of stimuli (will be adjusted downward
# if some cell has fewer available items).
target_total = 240
random_seed = 637

base_path = Path(__file__).resolve().parents[1]
in_csv  = base_path / "data" / "processed" / "off_flags_dk.csv"
out_csv = base_path / "data" / "processed" / "stimulus_set.csv"

# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------
if not in_csv.exists():
    raise SystemExit(f"[ERR] Flags file not found: {in_csv}")

print(f"[INFO] Loading flags data from: {in_csv}")
df = pd.read_csv(in_csv, low_memory=False)
print(f"[INFO] Loaded shape = {df.shape}")

# ---------------------------------------------------------------------
# Filter to usable items
# ---------------------------------------------------------------------
# 1) Keep only clearly Danish items
df = df[df["lang_da"] == 1].copy()
print(f"[INFO] After lang_da==1 filter: {df.shape[0]} rows")

# 2) Keep only items with a proper eco_score (A–E) so eco_signal is meaningful
df = df[df["eco_score"].notna()].copy()
print(f"[INFO] After eco_score notna filter: {df.shape[0]} rows")

# Make sure these are ints (0/1)
df["organic_badge"] = df["organic_badge"].astype(int)
df["eco_signal"] = df["eco_signal"].astype(int)

# ---------------------------------------------------------------------
# Define 4 cells: organic_badge (0/1) × eco_signal (0/1)
# ---------------------------------------------------------------------
df["cell"] = list(zip(df["organic_badge"], df["eco_signal"]))

cell_counts = df["cell"].value_counts().sort_index()
print("\n[INFO] Cell counts (organic_badge, eco_signal):")
for cell, n in cell_counts.items():
    print(f"  {cell}: {n}")

# We want to balance across the 4 cells. Determine how many we *can* take.
all_cells = [(0, 0), (0, 1), (1, 0), (1, 1)]
available_per_cell = {c: cell_counts.get(c, 0) for c in all_cells}

if any(n == 0 for n in available_per_cell.values()):
    print("\n[WARN] Some cells have zero items! Balancing will be impossible.")
    print("       Available per cell:", available_per_cell)

# Target per cell given desired total
target_per_cell = 20

# But we cannot exceed what's available in the smallest cell
n_per_cell = target_per_cell * 2

max_balanced_per_cell = min(available_per_cell.values())
if n_per_cell > max_balanced_per_cell:
    raise SystemExit(
        f"[ERR] Not enough items to allocate {target_per_cell} per 8-cell. "
        f"Need {n_per_cell} per 4-cell but smallest cell has {max_balanced_per_cell}. "
        f"Available per cell: {available_per_cell}"
    )

actual_total = n_per_cell * len(all_cells)
print(f"\n[INFO] Exact 8-cell target={target_per_cell} => "
      f"per 4-cell={n_per_cell}, actual_total={actual_total}")
# ---------------------------------------------------------------------
# Sample items from each cell
# ---------------------------------------------------------------------
rng = np.random.default_rng(random_seed)
samples = []

for cell in all_cells:
    sub = df[df["cell"] == cell].copy()
    if len(sub) < n_per_cell:
        # This should not happen because we bounded by max_balanced_per_cell,
        # but we guard just in case.
        print(f"[WARN] Cell {cell} only has {len(sub)} items, "
              f"but n_per_cell={n_per_cell}. Taking all available.")
        take = len(sub)
    else:
        take = n_per_cell

    # Random sample within this cell
    # Use a reproducible seed offset per cell
    seed_offset = hash(cell) % (2**32)
    sub_sampled = sub.sample(
        n=take,
        random_state=random_seed + seed_offset
    )
    samples.append(sub_sampled)

stim = pd.concat(samples, axis=0).reset_index(drop=True)

print(f"[INFO] Concatenated sampled set shape: {stim.shape}")

# ---------------------------------------------------------------------
# Assign salience ("low" / "high") evenly within each cell
# ---------------------------------------------------------------------
stim["salience"] = ""

for cell in all_cells:
    idx = stim.index[stim["cell"] == cell].to_list()
    n = len(idx)
    if n == 0:
        continue

    idx = np.array(idx)
    rng.shuffle(idx)
    half = n // 2

    low_idx = idx[:half]
    high_idx = idx[half:]

    stim.loc[low_idx, "salience"] = "low"
    stim.loc[high_idx, "salience"] = "high"

# Sanity check: no empty salience
if (stim["salience"] == "").any():
    n_empty = (stim["salience"] == "").sum()
    print(f"[WARN] Found {n_empty} rows with empty salience, filling with 'low'")
    stim.loc[stim["salience"] == "", "salience"] = "low"

# ---------------------------------------------------------------------
# Shuffle overall trial order and add item_id
# ---------------------------------------------------------------------
stim = stim.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
stim["item_id"] = np.arange(1, len(stim) + 1)

# ---------------------------------------------------------------------
# Select columns for PsychoPy
# ---------------------------------------------------------------------
cols_out = [
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

# Keep raw-ish tags as optional extras if present
for extra in ["labels_tags", "languages_tags", "countries_tags"]:
    if extra in stim.columns:
        cols_out.append(extra)

stim_out = stim[cols_out].copy()

# ---------------------------------------------------------------------
# Fix weird product names
# ---------------------------------------------------------------------
name_overrides_by_item_id = {
    20: "Tun på dåse",
    22: "Hvidløg",
    47: "Rustikki Bread Sticks Blå Birkes",
    54: "Skyr med frugt",
    61: "ØGO Hvedemel",
    68: "Økologisk kakao soya drik",
    76: "Yalla! Drikkeyoghurt, Jordbær & granatæble laktosefri",
    78: "Cocio classic chokolademælk",
    105: "Hvidløgsdressing",
    120: "Burger boller",
    150: "Frisk rødkål",
}

stim_out["product_name"] = stim_out["item_id"].map(name_overrides_by_item_id).fillna(stim_out["product_name"])

# ---------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------
stim_out.to_csv(out_csv, index=False, encoding="utf-8-sig")
print(f"\n[OK] Saved stimulus set to: {out_csv}")
print(f"[OK] Final stimulus shape: {stim_out.shape}")

print("\n[SUMMARY] cell × salience:")
print(stim_out.groupby(["organic_badge", "eco_signal", "salience"])["item_id"].count())
