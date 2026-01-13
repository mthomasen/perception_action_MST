# perception\_action\_MST

\## Perception \& Action Exam Project — ØKO Badge Salience and Perceived Sustainability



This repository contains code and materials for a Perception \& Action exam project testing whether an organic badge (“ØKO”) inflates perceived sustainability of food products, and whether this effect is amplified by badge visual salience.



\## Research question

Do organic badges (“ØKO”) — especially when visually salient — inflate perceived sustainability of food products \*\*above and beyond\*\* an independent eco proxy derived from Open Food Facts (OFF)?



\## Hypotheses

\- \*\*H1 (Badge inflation):\*\* Products displayed with an organic badge (“ØKO”) receive higher sustainability ratings than products shown without the badge.

\- \*\*H2 (Salience amplification):\*\* The positive effect of the organic badge on sustainability ratings is larger when badge salience is \*\*high\*\* than when badge salience is \*\*low\*\*.



Controls:

\- `eco\_signal` (OFF eco grade A/B vs C/D/E)

\- `green\_words` (semantic “green” words in product names)



\## Experiment summary

\- \*\*Task:\*\* single-item rating task (not 2AFC).

\- \*\*Trial:\*\* product card shown → participant rates perceived sustainability on a \*\*1–7 scale\*\*.

\- \*\*DV:\*\* sustainability rating.

\- \*\*RT:\*\* recorded and used \*\*only\*\* for quality control trimming (not analyzed as an outcome).

\- \*\*Design:\*\* within-subject, balanced stimulus set crossing:

&nbsp; - `organic\_badge` ∈ {0,1}

&nbsp; - `salience` ∈ {low, high}

&nbsp; - `eco\_signal` ∈ {0,1} (OFF-derived benchmark control)

\- \*\*Stimuli:\*\* 160 items total (20 per cell in the 2×2×2 design).



\## Data source

Stimuli are sampled from \*\*Open Food Facts (OFF)\*\*, an open food product database:

\- OFF product dump is filtered to Denmark-relevant items.

\- Final stimuli restricted to items with Danish-language cues (`lang\\\_da == 1`) and valid eco grades (A–E).



\## Repository structure

\- `code/`

&nbsp; - `01\_clean\_data.py`

&nbsp;   Loads the Open Food Facts products export, filters for Denmark, cleans key fields, and writes a smaller dataset.

&nbsp; - `02\_engineer\_flags.py`

&nbsp;   Loads the cleaned DK dataset and engineers variables/flags (e.g., eco score/signal, organic badge, Danish-language indicator, “green” wording indicator, and category).

&nbsp; - `03a\_build\_stimulus\_set.py` 

&nbsp;   Builds a stimulus set from the engineered dataset.

  - `03b\_qc\_stimulus\_set.py` 

&nbsp;   Quality checks for the stimulus set.

  - `03c\_stimulus\_description.Rmd` 

&nbsp; - `04\_data\_inspection.Rmd`

&nbsp; - `05\_data\_cleanup.Rmd`

&nbsp; - `06\_descriptive.Rmd`

&nbsp; - `07\_analysis.Rmd`

&nbsp; - `src/` 

&nbsp;   - `functions.py`

&nbsp;     Shared helper functions used by the Python pipeline scripts.

&nbsp; - `experiment/`

&nbsp;   -`experiment\_run\_functions.py`

&nbsp;   -`experiment\_run\_script.py`

\- `data/`

&nbsp; - `processed/`

&nbsp;   - `off\_dk\_clean.csv`

&nbsp;   - `off\_flags\_dk.csv`

&nbsp;   - `stimulus\_set.csv`



\## Data availability

This project expects the Open Food Facts products export file : `data/raw/en.openfoodfacts.org.products.csv.gz`. This file is not included due to file size. 

The participants response files are not included due to privacy reasons.



\## Pipeline overview



\### 1) Clean OFF data

Reads OFF in chunks and filters to Denmark-relevant items. Coalesces product names (prefers Danish where available).



\*\*Output:\*\* `data/processed/off\_dk\_clean.csv`



\### 2) Engineer flags

Derives/engineers variables used for stimulus selection and controls:

\- `eco\_score` (A–E; others treated as missing)

\- `eco\_signal` (1 if `eco\_score` ∈ {A,B}, else 0)

\- `organic\_badge` (ØKO/bio tags)

\- `lang\_da`

\- `green\_words`

\- `category`



\*\*Output:\*\* `data/processed/off\_flags\_dk.csv`



\### 3) Build stimulus set

Creates a balanced set across `organic\_badge × eco\_signal`, assigns `salience` low/high evenly, shuffles order, and creates `item\_id`.



\*\*Output:\*\* `data/processed/stimulus\_set.csv`



\#### Name overrides (important for reproducibility)

Some product names were manually improved for clarity. These changes are \*\*hard-coded\*\* in the stimulus builder via a mapping like:



name\_overrides\_by\_item\_id = {

&nbsp;   20: "Tun på dåse",

&nbsp;   22: "Hvidløg",

&nbsp;   ...

}





\### 4) Running the experiment (PsychoPy)

Presents one product card per trial, the style of the ØKO badge depends on salience, the participants then responds with a 1-7 sustainability rating. One csv file is saved per participant containing item\_id, product\_name, organic\_badge, salience, eco\_signal, eco\_score,lang\_da, green\_words, category, labels\_tags, languages\_tags, countries\_tags, rating,rt, block\_shown, participant, age, gender, diet, consent



\### 5) Analysis

Data are inspected, then responses are merged with stimulus data while applying RT trimming for QC. Descriptive summaries and figures are constructed. 

Rating is analyzed using a linear mixed-effects model with random intercepts for participant and item:



rating ~ organic\_badge \* salience + eco\_signal + green\_words + (1 | participant) + (1 | item\_id)



RT is not analyzed as an outcome; it is used only for trimming implausible trials during cleanup/QC. 



\## Reproducibility

\### Software

* Python
* R (RStudio recommended for .Rmd)
* PsychoPy



\### Python dependencies

* pandas
* numpy



\### R dependencies

* tidyverse
* lme4
* lmerTest
* emmeans
* broom.mixed
* performance
* patchwork







