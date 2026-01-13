from pathlib import Path
import sys

base_path = Path(__file__).resolve().parents[2]
sys.path.append(str(base_path / "code" / "experiment"))

from experiment_run_functions import run_experiment

trials_csv = base_path / "data" / "processed" / "stimulus_set.csv"
out_dir = base_path / "data" / "responses"

if __name__ == "__main__":
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = run_experiment(
        trials_csv=trials_csv,
        out_dir=out_dir,
        full_screen=True,      # set True for real runs
        window_size=(1200, 800),
        title="sustainability rating (salience)",
        n_blocks=4,
    )
    print("saved:", out_file)
