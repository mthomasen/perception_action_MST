## Perception & Action Exam Project — ØKO Badge Salience and Perceived Sustainability

This repository contains code and materials for a Perception & Action exam project testing whether an organic badge (rendered as “ØKO”) influences perceived sustainability ratings of food products, and whether this influence is amplified by increased badge visual salience.

### Research question

Do ØKO badges—especially when visually salient—influence perceived sustainability ratings of food products above and beyond an independent eco proxy derived from Open Food Facts (OFF) and semantic “green” wording in product names?

### Hypotheses

- **H1 (Badge effect):** Products displayed with an ØKO badge receive higher sustainability ratings than products shown without the badge.
- **H2 (Salience amplification):** The effect of the ØKO badge is larger when badge salience is **high** than when it is **low**.

### Experiment summary

- **Task:** single-item rating task (not 2AFC)
- **DV:** perceived sustainability rating (1–7)
- **RT:** recorded and used only for QC trimming (not analysed as an outcome)
- **Design:** within-subject; balanced stimulus set crossing:
  - `organic_badge` ∈ {0, 1}
  - `salience` ∈ {low, high}
  - `eco_signal` ∈ {0, 1}
- **Stimuli:** 160 items total (20 per cell in the 2 × 2 × 2 design)

### Data source

Stimuli are sampled from Open Food Facts (OFF), an open food product database:

- OFF product dump is filtered to Denmark-relevant items.
- Final stimuli restricted to items with Danish-language cues (`lang_da == 1`) and valid eco grades (A–E).

### Repository structure

- code/
  - 01_clean_data.py
  - 02_engineer_flags.py
  - 03a_build_stimulus_set.py
  - 03b_qc_stimulus_set.py
  - 03c_stimulus_description.Rmd
  - 04_data_inspection.Rmd
  - 05_data_cleanup.Rmd
  - 06_descriptive.Rmd
  - 07_analysis.Rmd
  - src/
    - functions.py
  - experiment/
    - experiment_run_functions.py
    - experiment_run_script.py

- data/
  - processed/
    - off_dk_clean.csv
    - off_flags_dk.csv
    - stimulus_set.csv

### Pipeline overview

**1. Clean OFF data (01_clean_data.py)**

- Reads OFF in chunks, filters Denmark-relevant items, cleans key fields, and coalesces 	product names (prefers Danish where available).
	Output: data/processed/off_dk_clean.csv

**2. Engineer flags (02_engineer_flags.py)**
- Derives variables used for sampling and analysis:
	- eco_score (A–E; non-informative values treated as missing)
	- co_signal (1 if eco_score ∈ {A,B}, else 0)
   	- organic_badge (OFF label tags indicating organic-related labeling)
    - lang_da
    - green_words
    - category
	Output: data/processed/off_flags_dk.csv

**3. Build stimulus set (03a_build_stimulus_set.py)**
- Samples a balanced set across organic_badge × eco_signal
- Assigns salience (low/high) evenly within each cell
- Shuffles order and creates item_id
	Output: data/processed/stimulus_set.csv

**Name overrides (reproducibility note):** A small number of product names are manually improved for readability via an 		item_id-based override map in the stimulus builder.

**4. Run experiment (PsychoPy)**
- Presents one product card per trial.
- When organic_badge == 1, a standardized “ØKO” badge is shown; badge styling depends on salience.
- Participants respond with a 1–7 sustainability rating.
- One CSV is saved per participant.
	- Participant CSV contains (e.g.): item_id, product_name, organic_badge, salience, eco_signal, eco_score, lang_da, green_words, category, rating, rt, block_shown, participant, age, gender, diet, consent

**5. Analysis (R)**
- Responses are merged with stimulus data, QC trimming is applied, and ratings are 	analysed with a linear mixed-effects model.

**QC trimming**
- RT plausibility window: 0.15–15 seconds (used only for exclusion)

**Primary analysis model**
- Because salience only changes the display when a badge is present, analyses use a 3-level factor:
	- badge_salience ∈ {no_badge, badge_low, badge_high}

- Model: *rating ~ badge_salience + eco_signal + green_words + (1 | participant) + (1 | item_id)*

- Planned contrasts on estimated marginal means:
	- H1: badge present (avg of badge_low & badge_high) vs no_badge
 	- H2: badge_high vs badge_low


### Reproducibility

**Software**
- Python
- R (RStudio recommended for .Rmd)
- PsychoPy

**Python dependencies**
- pandas
- numpy

**R dependencies**
- tidyverse
- lme4
- lmerTest
- emmeans
- broom.mixed
- performance
- patchwork







