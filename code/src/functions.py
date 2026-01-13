from __future__ import annotations
from collections import defaultdict
from typing import Dict, Tuple, Optional
from collections import defaultdict
import re

import numpy as np
import pandas as pd

# 01_clean_data helpers 
def _norm_str(s) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    return "" if s.lower() == "nan" else s

def _as_lower(s) -> str:
    return _norm_str(s).lower()

def _derive_eco_score(df: pd.DataFrame) -> pd.Series:
    """
    Prefer ecoscore_grade (A–E). If empty, fall back to environmental_score_grade.
    If still missing, optionally map ecoscore_score (numeric) to A–E.

    Returns uppercase letters A–E or NA.
    """

    # 1) Start from ecoscore_grade if present, using _norm_str so "nan" -> ""
    if "ecoscore_grade" in df.columns:
        eco_a = df["ecoscore_grade"].map(_norm_str)
    else:
        eco_a = pd.Series("", index=df.index, dtype="string")

    # 2) Fallback: environmental_score_grade, also cleaned
    if "environmental_score_grade" in df.columns:
        eco_b = df["environmental_score_grade"].map(_norm_str)
    else:
        eco_b = pd.Series("", index=df.index, dtype="string")

    # Prefer ecoscore_grade when non-empty; otherwise env. grade
    eco = eco_a.fillna("").str.strip()
    eco = eco.where(eco != "", eco_b.fillna("").str.strip())

    # Normalise values
    eco = eco.str.lower()

    # Map special OFF grades and drop junk
    eco = eco.replace(
        {
            "": pd.NA,
            "unknown": pd.NA,
            "not-applicable": pd.NA,
            "a-plus": "a",   # reasonably treat A+ as A
        }
    )

    # Final: uppercase, keep only A–E
    eco = eco.str.upper()
    eco = eco.where(eco.isin(list("ABCDE")), other=pd.NA)

    # 3) Optional backup: ecoscore_score (if both grades useless)
    if eco.isna().all() and "ecoscore_score" in df.columns:
        sc = pd.to_numeric(df["ecoscore_score"], errors="coerce")
        bins   = [-1000, 19, 39, 59, 79, 1000]
        labels = ["E", "D", "C", "B", "A"]
        mapped = pd.cut(sc, bins=bins, labels=labels).astype("string")
        eco = mapped

    return eco


def _coalesce_columns(df: pd.DataFrame, name: str, fallbacks: list[str]) -> pd.Series:
    """
    Return the first non-empty among [name] + fallbacks.
    """
    cols = [c for c in [name] + fallbacks if c in df.columns]
    if not cols:
        return pd.Series([""] * len(df), index=df.index, dtype="string")

    out = df[cols[0]].astype("string")
    for c in cols[1:]:
        out = out.mask(out.fillna("").str.strip().eq(""), df[c].astype("string"))
    return out.fillna("")

# Keeping danish items 
danish_words = (
    "økologisk","økologi","økonomi", "danske","dansk","skyr","rugbrød","kartofler",
    "havre","smør","rød","grød","pålæg","remoulade","rug","knækbrød"
)
danish_chars = re.compile(r"[æøåÆØÅ]")

def _first_nonempty(*vals) -> str:
    for v in vals:
        s = ("" if v is None else str(v)).strip()
        if s and s.lower() != "nan":
            return s
    return ""

def looks_danish_text(name: str) -> bool:
    s = (name or "").strip()
    if not s:
        return False
    if danish_chars.search(s):
        return True
    low = s.lower()
    return any(w in low for w in danish_words)

def _series_or_empty(df: pd.DataFrame, col: str) -> pd.Series:
    if col in df.columns:
        return df[col].astype(str)
    return pd.Series([""] * len(df), index=df.index, dtype="string")

# Signals 
def derive_eco_signal(df: pd.DataFrame) -> pd.Series: 
    eco = _series_or_empty(df, "eco_score").str.strip().str.upper()
    return eco.isin(["A", "B"]).astype(int)

_ORG_REGEX = re.compile(
    r"(?:^|[,;:\s])(?:"
    r"en:organic|da:økologisk|da:okologisk|da:oekologisk|"
    r"organic|økologisk|okologisk|oekologisk|"
    r"bio|biologique|ecologico|ecológico|ökologisch|öko"
    r")(?:$|[,;:\s])",
    flags=re.IGNORECASE,
)

def derive_organic_label(df: pd.DataFrame) -> pd.Series:

    lab = _series_or_empty(df, "labels_tags").str.lower().fillna("")
    return lab.str.contains(_ORG_REGEX).astype(int)

#Preperation

def prepare_items(df: pd.DataFrame, strict_danish_only: bool = False) -> pd.DataFrame:
    df = df.copy()

    # Display name (prefer Danish if present)
    if "product_name_da" in df.columns:
        df["name_clean"] = [
            _first_nonempty(da, en)
            for da, en in zip(df["product_name_da"], df.get("product_name", ""))
        ]
    else:
        df["name_clean"] = df.get("product_name", "").astype(str)

    df["name_clean"] = (
        df["name_clean"].fillna("")
        .str.replace(r"^\s*nan\s*$", "", regex=True)
        .str.strip()
    )
    df = df[df["name_clean"] != ""].copy()

    # Danish flags
    lang_tags = _series_or_empty(df, "languages_tags").str.lower().fillna("")
    df["is_lang_da"] = lang_tags.str.contains(r"(?:^|[,;:])da(?:$|[,;:])", regex=True)
    if "lc" in df.columns:
        df["is_lang_da"] = df["is_lang_da"] | (df["lc"].astype(str).str.lower().eq("da"))

    ctags = _series_or_empty(df, "countries_tags").str.lower().fillna("")
    df["is_denmark_country"] = (
        ctags.str.contains(r"(?:^|,)\s*dk\s*(?:,|$)", regex=True)
        | ctags.str.contains("denmark")
        | ctags.str.contains("da:denmark")
    )
    df["is_danish_like"] = df["name_clean"].map(looks_danish_text)

    # Strict Danish filter (keep clear DK items)
    if strict_danish_only:
        if "product_name_da" in df.columns:
            has_da_name = df["product_name_da"].astype(str).fillna("").str.strip() != ""
        else:
            has_da_name = pd.Series(False, index=df.index)

        keep_mask = (
            has_da_name
            | df["is_lang_da"]
            | (df["is_danish_like"] & df["is_denmark_country"])
        )
        before = len(df)
        df = df[keep_mask].copy()
        after = len(df)
        print(f"[prepare_items] strict_danish_only=True kept {after}/{before} rows ({after/before:.1%})")

    # Category
    cat = df.get("main_category_en", df.get("main_category", None))
    if cat is None:
        cat = df["categories_tags"].fillna("").str.split(",").str[0]
        cat = cat.str.replace(r"^[a-z]{2}:", "", regex=True)
    df["category"] = cat.replace("", "unknown")

    # Signals
    df["eco_signal"] = derive_eco_signal(df)          # 1 if eco_score A/B
    df["organic_label"] = derive_organic_label(df)    # 1 if organic badge in labels_tags

    # 4-way cells: A(eco good) × L(label present)
    A  = df["eco_signal"].eq(1)
    NA = df["eco_signal"].eq(0)
    L  = df["organic_label"].eq(1)
    NL = df["organic_label"].eq(0)

    df["cell"] = np.select(
        [A & L, A & NL, NA & L, NA & NL],
        ["A_label", "A_nolabel", "NA_label", "NA_nolabel"],
        default="other",
    )
    df = df[df["cell"].isin(["A_label","A_nolabel","NA_label","NA_nolabel"])].copy()

    # Final minimal columns (product_name keeps cleaned name)
    df = df.rename(columns={"name_clean": "product_name"})
    keep = [
        "product_name",
        "category",
        "eco_score",      # keep the raw grade for reporting
        "eco_signal",
        "organic_label",
        "cell",
        "is_danish_like",
        "is_lang_da",
    ]
    for c in keep:
        if c not in df:
            df[c] = pd.NA
    return df[keep]

#pooling 
def build_pools(items: pd.DataFrame) -> Tuple[Dict[str, Dict[str, pd.DataFrame]], Dict[str, pd.DataFrame]]:
    cols = ["product_name","category","eco_score","eco_signal","organic_label","is_danish_like","is_lang_da"]
    pools_by_cat: Dict[str, Dict[str, pd.DataFrame]] = defaultdict(dict)
    for cat, g in items.groupby("category", dropna=False):
        for key in ["A_label","A_nolabel","NA_label","NA_nolabel"]:
            pools_by_cat[cat][key] = g[g["cell"] == key][cols].reset_index(drop=True)

    global_pools = {
        key: items[items["cell"] == key][cols].reset_index(drop=True)
        for key in ["A_label","A_nolabel","NA_label","NA_nolabel"]
    }
    return pools_by_cat, global_pools


# Trial construction

def sample_row(
    pool: pd.DataFrame,
    rng: np.random.Generator,
    name_counts: Dict[str, int],
    max_repeats: int
) -> Optional[dict]:
    if len(pool) == 0:
        return None

    idxs = rng.permutation(len(pool))

    # Pass 1: Danish AND under cap
    for i in idxs:
        rec = pool.iloc[int(i)].to_dict()
        name = str(rec.get("product_name", "")).strip()
        if not name:
            continue
        if name_counts.get(name, 0) >= max_repeats:
            continue
        if rec.get("is_lang_da") is True or rec.get("is_danish_like") is True:
            return rec

    # Pass 2: any under cap
    for i in idxs:
        rec = pool.iloc[int(i)].to_dict()
        name = str(rec.get("product_name", "")).strip()
        if name and name_counts.get(name, 0) < max_repeats:
            return rec

    return None

def make_trial(
    congruent: bool,
    left_is_A: bool,
    pools_by_cat: Dict[str, Dict[str, pd.DataFrame]],
    global_pools: Dict[str, pd.DataFrame],
    rng: np.random.Generator,
    name_counts: Dict[str, int],
    max_repeats: int
) -> Optional[dict]:

    # A = eco_signal==1 ; NA = eco_signal==0
    # L = organic_label==1 ; NL = 0
    a_need, na_need = ("A_label", "NA_nolabel") if congruent else ("A_nolabel", "NA_label")

    cats = list(pools_by_cat.keys())
    rng.shuffle(cats)
    chosen = None
    for c in cats:
        if len(pools_by_cat[c][a_need]) > 0 and len(pools_by_cat[c][na_need]) > 0:
            chosen = c
            break

    if chosen:
        pool_A  = pools_by_cat[chosen][a_need]
        pool_NA = pools_by_cat[chosen][na_need]
    else:
        pool_A  = global_pools[a_need]
        pool_NA = global_pools[na_need]

    a  = sample_row(pool_A, rng, name_counts, max_repeats)
    na = sample_row(pool_NA, rng, name_counts, max_repeats)
    if a is None or na is None:
        return None

    left, right = (a, na) if left_is_A else (na, a)
    return {
        "congruent": int(congruent),
        "left_is_A": int(left_is_A),

        "left_name":  str(left["product_name"]),
        "left_cat":   str(left["category"]),
        "left_label": int(bool(left["organic_label"])),
        "left_is_sust": int(bool(left["eco_signal"])),

        "right_name":  str(right["product_name"]),
        "right_cat":   str(right["category"]),
        "right_label": int(bool(right["organic_label"])),
        "right_is_sust": int(bool(right["eco_signal"])),
    }

def build_trials_flat(
    n_trials: int,
    pools_by_cat: Dict[str, Dict[str, pd.DataFrame]],
    global_pools: Dict[str, pd.DataFrame],
    seed: int = 123,
    max_repeats_per_name: int = 5,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # 8 balanced cells: (congruent∈{0,1}) × (left_is_A∈{0,1}) × (salience∈{low,high})
    cells: List[Tuple[int, int, str]] = [
        (c, l, s) for c in (0, 1) for l in (0, 1) for s in ("low", "high")
    ]

    per_cell = n_trials // 8
    remainder = n_trials - per_cell * 8

    cell_targets: Dict[Tuple[int,int,str], int] = { (c,l,s): per_cell for (c,l,s) in cells }
    for idx in rng.permutation(len(cells))[:remainder]:
        c, l, s = cells[idx]
        cell_targets[(c,l,s)] += 1

    cell_filled: Dict[Tuple[int,int,str], int] = { (c,l,s): 0 for (c,l,s) in cells }
    name_counts: Dict[str, int] = defaultdict(int)

    trials = []
    for c, l, s in rng.permutation(cells):
        need = cell_targets[(c,l,s)]
        while cell_filled[(c,l,s)] < need:
            tr = make_trial(
                congruent=bool(c),
                left_is_A=bool(l),
                pools_by_cat=pools_by_cat,
                global_pools=global_pools,
                rng=rng,
                name_counts=name_counts,
                max_repeats=max_repeats_per_name,
            )
            if tr is None:
                tries = 0
                while tr is None and tries < 15:
                    tr = make_trial(
                        bool(c), bool(l),
                        pools_by_cat, global_pools, rng,
                        name_counts=name_counts,
                        max_repeats=max_repeats_per_name,
                    )
                    tries += 1
                if tr is None:
                    break  # cannot fill more in this cell

            tr["salience"] = s

            ln = (tr.get("left_name") or "").strip()
            rn = (tr.get("right_name") or "").strip()
            if ln: name_counts[ln] = name_counts.get(ln, 0) + 1
            if rn: name_counts[rn] = name_counts.get(rn, 0) + 1

            trials.append(tr)
            cell_filled[(c,l,s)] += 1

    total = len(trials)
    if total < n_trials:
        short = {k: cell_targets[k] - cell_filled[k] for k in cell_targets if cell_filled[k] < cell_targets[k]}
        print(f"[WARN] built {total}/{n_trials}. Cell shortfalls: {short}")

    return pd.DataFrame(trials)

