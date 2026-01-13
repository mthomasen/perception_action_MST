from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Iterable, List

import random
import numpy as np
import pandas as pd

try:
    from psychopy import visual, core, event, gui
except ImportError as e:
    raise SystemExit(
        "psychopy not found. open this from the psychopy app or install psychopy in your environment."
    ) from e


# ======================
# participant + window
# ======================
def get_participant_info(title: str = "sustainability rating (salience)") -> Dict[str, Any]:
    dlg = gui.Dlg(title=title)
    dlg.addText("deltageroplysninger")
    dlg.addField("deltager-id:", "")
    dlg.addField("alder (år):", "")
    dlg.addField(
        "køn:",
        choices=["female", "male", "non-binary", "prefer not to say", "other"],
        initial=3,
    )
    dlg.addField(
        "kostpræference:",
        choices=["none", "vegetarian", "vegan", "pescatarian", "other"],
        initial=0,
    )

    ok_pressed = dlg.show()
    if not ok_pressed:
        core.quit()

    pid, age, gender, diet = dlg.data

    try:
        age = int(age)
    except Exception:
        age = None
    if age is not None and not (10 <= age <= 100):
        age = None

    return {
        "participant": (str(pid).strip() or "anon"),
        "age": age,
        "gender": gender,
        "diet": diet,
    }


def make_window(fullscr: bool = False, size=(1200, 800)):
    return visual.Window(fullscr=fullscr, color="white", units="pix", size=size)


def close_window(win):
    try:
        win.close()
    except Exception:
        pass

def show_consent(win) -> None:
    text = (
        "samtykke\n\n"
        "du er ved at deltage i et forskningsstudie om vurdering af fødevarers bæredygtighed.\n\n"
        "deltagelse er frivillig. du kan til enhver tid afbryde uden konsekvenser.\n"
        "dine svar gemmes og analyseres i anonymiseret form.\n\n"
        "tryk 'y' for at give samtykke og fortsætte.\n"
        "tryk 'n' for ikke at give samtykke (eksperimentet afsluttes).\n"
    )
    stim = visual.TextStim(win, text=text, color="black", height=24, wrapWidth=1050)
    stim.draw()
    win.flip()

    keys = event.waitKeys(keyList=["y", "n", "escape"])
    if keys and keys[0] in ["n", "escape"]:
        raise KeyboardInterrupt

# ======================
# basic screens
# ======================
def show_text(win, text: str, height: int = 28, wait_for_key: bool = True):
    stim = visual.TextStim(win, text=text, color="black", height=height, wrapWidth=1000)
    stim.draw()
    win.flip()
    if wait_for_key:
        keys = event.waitKeys()
        if keys and "escape" in keys:
            raise KeyboardInterrupt


def show_instructions(win):
    show_text(
        win,
        "opgave: hvor bæredygtigt virker produktet?\n\n"
        "du ser ét produkt ad gangen.\n"
        "vurdér hvor bæredygtigt det virker på en skala fra 1 til 7.\n\n"
        "taster:\n"
        "1 = slet ikke bæredygtigt\n"
        "7 = meget bæredygtigt\n\n"
        "tryk en vilkårlig tast for at starte.",
    )


def show_block_header(win, shown_block_num: int, n_blocks: int):
    extra = "\n\n(sidste blok)" if shown_block_num == n_blocks else ""
    show_text(
        win,
        f"blok {shown_block_num} / {n_blocks}{extra}\n\ntryk en tast for at fortsætte."
    )


def show_fixation(win, ms: int = 300):
    visual.TextStim(win, text="+", color="black", height=44).draw()
    win.flip()
    core.wait(ms / 1000)


# ======================
# drawing
# ======================
def draw_card_single(
    win,
    name: str,
    has_badge: bool,
    salience: str,
):
    # card
    visual.Rect(
        win,
        width=700,
        height=380,
        pos=(0, 0),
        fillColor="white",
        lineColor="black",
        lineWidth=2,
    ).draw()

    # product name
    visual.TextStim(
        win,
        text=str(name),
        color="black",
        height=30,
        pos=(0, 60),
        wrapWidth=640,
    ).draw()

    # rating prompt (persistent on the same card)
    visual.TextStim(
        win,
        text="hvor bæredygtigt virker dette produkt? (1-7)",
        color="black",
        height=22,
        pos=(0, -110),
        wrapWidth=640,
    ).draw()

    # anchor labels (optional but helps participants)
    visual.TextStim(
        win,
        text="1: ikke bæredygtigt",
        color="black",
        height=18,
        pos=(-240, -160),
        wrapWidth=320,
    ).draw()
    visual.TextStim(
        win,
        text="7: meget bæredygtigt",
        color="black",
        height=18,
        pos=(240, -160),
        wrapWidth=320,
    ).draw()

    # øko badge
    if has_badge:
        if str(salience).lower().strip() == "low":
            badge_height = 22
            badge_color = "darkgrey"
            badge_bold = False
        else:
            badge_height = 34
            badge_color = "green"
            badge_bold = True

        visual.TextStim(
            win,
            text="ØKO",
            color=badge_color,
            height=badge_height,
            pos=(0, -10),
            bold=badge_bold,
        ).draw()


# ======================
# trials
# ======================
def run_trial(
    win,
    row: pd.Series,
    stim_ms: int | None = None,
    iti_ms: int = 400,
) -> Dict[str, Any]:
    show_fixation(win, 300)

    clock = core.Clock()
    event.clearEvents()

    draw_card_single(
        win=win,
        name=row["product_name"],
        has_badge=bool(int(row["organic_badge"])),
        salience=str(row["salience"]),
    )
    win.flip()
    clock.reset()

    key_list = ["1", "2", "3", "4", "5", "6", "7", "escape"]

    if stim_ms is None:
        keys = event.waitKeys(keyList=key_list, timeStamped=clock)
    else:
        keys = event.waitKeys(maxWait=stim_ms / 1000, keyList=key_list, timeStamped=clock)

    key, rt = keys[0]
    if key == "escape":
        raise KeyboardInterrupt

    rating = int(key)

    win.flip()
    core.wait(iti_ms / 1000)

    return {"rating": rating, "rt": rt}



def run_block(
    win,
    block_df: pd.DataFrame,
    shown_block_num: int,
    n_blocks: int,
) -> List[Dict[str, Any]]:
    show_block_header(win, shown_block_num, n_blocks)

    records: List[Dict[str, Any]] = []
    for _, row in block_df.iterrows():
        res = run_trial(win=win, row=row)

        rec = {k: row.get(k) for k in block_df.columns}
        rec.update(res)
        rec["block_shown"] = int(shown_block_num)
        records.append(rec)

    return records


# ======================
# block building
# ======================
def build_blocks_from_items(
    df: pd.DataFrame,
    n_blocks: int = 4,
    rng_seed: int | None = None,
) -> List[pd.DataFrame]:
    """
    split into balanced blocks, stratified over (organic_badge, eco_signal, salience).
    """
    rng = np.random.default_rng(rng_seed)
    df = df.copy()

    df["_cell"] = list(
        zip(
            df["organic_badge"].astype(int),
            df["eco_signal"].astype(int),
            df["salience"].astype(str).str.lower().str.strip(),
        )
    )

    blocks: List[List[int]] = [[] for _ in range(n_blocks)]
    for _, g in df.groupby("_cell"):
        idx = list(g.index)
        rng.shuffle(idx)
        for k, i in enumerate(idx):
            blocks[k % n_blocks].append(i)

    out: List[pd.DataFrame] = []
    for idxs in blocks:
        bdf = (
            df.loc[idxs]
            .drop(columns=["_cell"])
            .sample(frac=1.0, random_state=None)
            .reset_index(drop=True)
        )
        out.append(bdf)

    return out


# ======================
# saving
# ======================
def save_records(records: Iterable[Dict[str, Any]], out_dir: Path, participant: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(list(records))
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = out_dir / f"{participant}_{ts}.csv"
    df.to_csv(out_file, index=False, encoding="utf-8-sig")
    return out_file


# ======================
# main runner
# ======================
def run_experiment(
    trials_csv: Path,
    out_dir: Path,
    full_screen: bool = False,
    window_size=(1200, 800),
    title: str = "sustainability rating (salience)",
    n_blocks: int = 4,
) -> Path:
    info = get_participant_info(title)
    info["consent"] = 0  # will flip to 1 after consent
    participant = info["participant"]

    items = pd.read_csv(trials_csv, low_memory=False)

    # build balanced blocks (then randomize the order they are shown)
    block_dfs = build_blocks_from_items(items, n_blocks=n_blocks, rng_seed=None)
    block_indices = list(range(len(block_dfs)))
    random.shuffle(block_indices)

    win = make_window(fullscr=full_screen, size=window_size)

    all_records: List[Dict[str, Any]] = []
    try:
        # consent must happen before instructions
        show_consent(win)
        info["consent"] = 1

        show_instructions(win)

        # show blocks in randomized order, but display progress as 1..n_blocks
        for progress_num, block_i in enumerate(block_indices, start=1):
            block_df = block_dfs[block_i]
            block_records = run_block(
                win=win,
                block_df=block_df,
                shown_block_num=progress_num,
                n_blocks=len(block_dfs),
            )
            for r in block_records:
                r.update(info)
            all_records.extend(block_records)

        show_text(win, "færdig! tusind tak 🙌\n\ntryk en tast for at afslutte.")
        close_window(win)
        out_file = save_records(all_records, out_dir, participant)
        return out_file

    except KeyboardInterrupt:
        close_window(win)

        # if they quit before consent, do not save anything
        if info.get("consent", 0) != 1:
            raise SystemExit("aborted before consent; no data saved.")

        out_file = save_records(all_records, out_dir, participant)
        print("aborted by user (escape). partial data saved:", out_file)
        return out_file
