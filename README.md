# Municipal Correlates of Licensed 5G NR Infrastructure in Brazil

**Presence, Intensity, and Digital-Infrastructure Profiles**

Rony Anderson Spada Pedroso · Walsh College · MSc in AI and ML · QM640: Data Analytics Capstone

An end-to-end Python study of how municipal socioeconomic conditions and existing telecommunications infrastructure relate to licensed 5G New Radio deployment in Brazil.

[Abstract](#abstract) · [Introduction](#introduction) · [Research questions](#research-questions-and-methods) · [Run locally](#reproduce-and-run-locally) · [Google Colab](#google-colab-and-notebooks) · [Outputs](#generated-outputs)

## Abstract

Licensed 5G New Radio (NR) infrastructure is distributed unevenly across Brazil, raising questions about the municipal conditions associated with deployment. The purpose of this quantitative, nonexperimental, cross-sectional study was to use merged official municipal data to classify Brazilian municipalities by whether they have high licensed NR station counts; examine socioeconomic and infrastructure correlates of NR stations per 100,000 residents; identify digital-infrastructure profiles and their association with macro-region; and explore correlates of high Serviço Limitado Privado (SLP) station intensity as a supplementary analysis. Data from the National Telecommunications Agency (Anatel) and the Brazilian Institute of Geography and Statistics (IBGE) covered 5,571 municipalities, with 5,564 complete cases in the common modeling frame. The analysis combined random forest classification, a two-part hurdle framework, ridge regression, k-means clustering, regional association testing, and exploratory logistic models. Structural prediction excluded near-target indicators, and evaluation used held-out observations, repeated cross-validation, geographic sensitivity checks, and bootstrap uncertainty estimates. The high-count classifier achieved a held-out ROC-AUC of .927; discrimination declined to approximately .82 when the target was normalized by population. NR presence was moderately predictable, while continuous per-capita intensity prediction across the full municipal modeling frame remained limited. Population density, fiber infrastructure, and GDP per capita showed modest associations with NR intensity. Two stable infrastructure profiles were associated with macro-region, indicating marked geographic differences in municipal conditions. The supplementary SLP analysis linked higher station intensity to wealth and inherited infrastructure, with weaker predictive performance across states. These findings support a reproducible framework for municipal screening, comparison, and further investigation. They also indicate that public structural data alone provide limited support for forecasting deployment intensity across the national municipal frame. Licensed NR counts measure infrastructure presence rather than verified Standalone or cloud-native operation, and SLP remains an exploratory private-network-related proxy. The cross-sectional design, incomplete historical source provenance, and validation limitations constrain interpretation. Engineering and investment decisions therefore require additional evidence on local demand, spectrum, costs, operator strategy, and site feasibility; the study does not establish causal effects or regulatory compliance.

**Keywords:** 5G New Radio, licensed stations, Brazil, municipal infrastructure, Anatel, IBGE, machine learning, digital divide.

## Introduction

Brazilian municipalities differ substantially in population size, population density, income, and existing fiber and mobile infrastructure. These differences provide a practical starting point for examining the uneven geographic distribution of licensed 5G NR stations. Understanding their relationship with deployment can inform municipal comparisons and help researchers, public agencies, and telecommunications planners identify where more detailed investigation is needed.

This project asks how much municipal structure can explain about three connected outcomes: high NR station counts, station intensity per resident, and broader digital-infrastructure profiles. It combines predictive models with statistical inference and unsupervised learning, then examines sensitivity to population normalization and geographic validation. A supplementary analysis considers SLP station intensity as an exploratory indicator of private-network-related activity.

The repository provides the preserved municipal input, executable analysis, six notebooks, generated results, and verification tools. The workflow runs from data cleaning and feature engineering through model estimation, uncertainty assessment, and export of numerical and graphical outputs.

## Research questions and methods

| Question | Outcome | Methods |
| --- | --- | --- |
| **RQ1:** Can municipal characteristics identify high-count NR deployment, including when deployment is normalized by population? | NR station count above the 75th percentile; per-capita and threshold sensitivity targets | Random forest classification, training-set tuning, held-out evaluation, and state-grouped validation |
| **RQ2:** How are municipal characteristics associated with NR station intensity? | NR presence, stations per 100,000 residents, and station counts with population exposure | Logistic presence model, ridge regression, and negative-binomial count models with bootstrap uncertainty |
| **RQ3:** Which digital-infrastructure profiles emerge, and how are they associated with macro-region? | Municipal cluster membership and regional distribution | K-means, silhouette selection, bootstrap adjusted Rand index, chi-square, and Cramér's V |
| **RQ4, exploratory:** Which characteristics are associated with high SLP station intensity? | SLP stations per 100,000 residents above the 75th percentile | Logistic regression, state-grouped validation, and threshold and aggregation sensitivities |

Structural predictors are GDP per capita, population, population density, fiber accesses per 100 residents, LTE accesses per 100 residents, and macro-region. NR accesses and measured download speed are excluded from structural prediction because they are closely related to deployment outcomes; they are used in exploratory analysis and infrastructure profiling.

### Principal findings

| Analysis | Result |
| --- | --- |
| High NR station counts | Held-out random forest ROC-AUC **.927**; approximately **.82** with the per-capita classification target |
| NR presence | Held-out ROC-AUC **.849** |
| Continuous intensity across the full municipal modeling frame | Ridge R² **.02** on the raw scale and **.06** on the log scale; both 95% intervals include zero |
| Infrastructure profiles | **Two clusters**, silhouette **.305**, and Cramér's V **.21** for association with macro-region |
| Exploratory SLP intensity | Held-out ROC-AUC **.810**, with weaker performance across states |

These results support municipal screening and comparison. Continuous intensity prediction across the national municipal frame remains limited. Model-specific estimation and validation details are documented in the [analysis protocol](docs/REPRODUCTION_NOTES.md).

## Data

The analysis starts from [`data/processed/merged_municipal_dataset.csv`](data/processed/merged_municipal_dataset.csv), which combines municipal Anatel and IBGE variables.

| Stage | Scope |
| --- | --- |
| Preserved input | 10,107 rows, 25 columns, and 5,571 unique municipal identifiers |
| Cleaning | Remove 193 exact duplicate rows and collapse 4,343 additional municipal-key rows |
| Municipal frame | 5,571 municipalities, with one row per municipality |
| Common modeling frame | 5,564 complete cases |

The pipeline checks this input's SHA-256 before fitting models:

```text
50fac84b16f63d66628741f36686cc076f43c90632a3befe53ca43ed9b316207
```

Use the included CSV to reproduce the study. Public source datasets change over time, so a fresh download is a new input and will not reproduce this analysis automatically. The [data dictionary](docs/DATA_DICTIONARY.md) defines the variables, and [data provenance](docs/DATA_PROVENANCE.md) records official access points, source lineage, and limitations in the historical acquisition records.

## Reproduce and run locally

### 1. Prerequisites

Use **Python 3.12**, **Git**, and a **macOS or Linux** environment. A GPU is not required. The analysis dependencies are pinned in `requirements.txt`.

Check your installation:

```bash
python3.12 --version
git --version
```

On macOS with Homebrew, install Python 3.12 if needed:

```bash
brew install python@3.12
```

### 2. Clone and install

Run these commands from a directory where you want to create the project folder:

```bash
git clone https://github.com/ronyspada2025/walsh-msc-capstone.git &&
cd walsh-msc-capstone
```

From the repository root, create an isolated environment and install dependencies:

```bash
python3.12 -m venv .venv &&
.venv/bin/python -m pip install -r requirements.txt
```

Run all subsequent commands from this same repository folder. Environment activation is optional because the commands explicitly use `.venv/bin/python`.

### 3. Verify the included results

The repository includes outputs from a completed analysis. Validate them before starting a new model run:

```bash
.venv/bin/python scripts/verify_project.py
```

A successful check includes:

```text
FINAL REPORT: {'MATCH': 417, 'DIFFERS': 0, 'MISSING_OR_INVALID': 0}
FINAL REPORT VERIFIED: all declared metrics agree at the displayed precision.
```

This checks the stored computation; it does not train the models again.

### 4. Recompute the complete analysis

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LOKY_MAX_CPU_COUNT=4 \
  .venv/bin/python -u final_pipeline.py --jobs 4
```

The pipeline cleans the input, creates features, fits the models, evaluates results, and writes tables, figures, predictions, and execution records to `reports/`. It uses seed 42 for the primary analysis, 1,000 held-out bootstrap resamples per interval, 999 state-bootstrap draws, and repeated stratified five-fold cross-validation with five repeats. Runtime depends on the computer; the bootstrap and model-search stages can take several minutes or longer.

Success is reported as `COMPUTATION COMPLETE (full)` followed by a `REPORT CHECK` with 417 matches, zero differences, and zero missing or invalid values. A smaller `--state-bootstrap` value produces a diagnostic run and cannot satisfy full-analysis verification.

### 5. Verify the new outputs

```bash
.venv/bin/python scripts/verify_project.py &&
.venv/bin/python -m unittest discover -s tests -v
```

Verification checks input and analysis-source hashes, output integrity, execution completeness, train/test partitions, model convergence, and numerical agreement with the fixed reference in `scripts/final_report_reference.json`. The reference is evaluated after estimation and is not used to choose parameters or replace model outputs. The checks assess agreement at the declared precision; execution timestamps and platform metadata will vary between runs.

For a focused numerical comparison, which also validates computation integrity:

```bash
.venv/bin/python scripts/compare_headline_results.py
```

The verification scripts return **0** on success, **2** for numerical disagreement, and **1** for invalid or incomplete evidence. If validation fails, read the diagnostic message and check the Python version, installed dependencies, and input checksum. Do not change the numerical reference to make a failed run pass.

## Google Colab and notebooks

[Open the complete pipeline in Google Colab](https://colab.research.google.com/github/ronyspada2025/walsh-msc-capstone/blob/main/notebooks/06_final_report_pipeline_colab.ipynb).

Open the notebook in a fresh runtime and run the cells in order. It clones the repository, installs dependencies, runs `final_pipeline.py`, verifies the outputs, and displays selected results. Use a Python 3.12 runtime for the documented reproduction environment.

| Notebook | Purpose |
| --- | --- |
| [01 — Data cleaning](notebooks/01_data_cleaning_and_alignment.ipynb) | Inspect input integrity and restore the municipal frame |
| [02 — Feature engineering](notebooks/02_feature_engineering.ipynb) | Construct intensities, transformations, and targets |
| [03 — Exploratory analysis](notebooks/03_exploratory_data_analysis.ipynb) | Examine missingness, distributions, and geographic patterns |
| [04 — Statistical models](notebooks/04_statistical_tests_rq2_rq4.ipynb) | Inspect RQ2 and exploratory RQ4 analyses |
| [05 — Machine learning](notebooks/05_ml_pipelines_rq1_rq3.ipynb) | Examine classification, clustering, and evaluation outputs |
| [06 — Complete pipeline](notebooks/06_final_report_pipeline_colab.ipynb) | Run and verify the complete analysis |

Notebooks 01–05 use shared preparation functions or generated outputs. Run notebook 06 or the command-line pipeline to regenerate the complete analysis. For a local notebook interface, install `requirements-notebooks.txt` into the same environment.

## Generated outputs

| Path | Contents |
| --- | --- |
| `reports/tables/headline_results.json` | Canonical numerical results and execution metadata |
| `reports/tables/` | Descriptive and model tables, municipal predictions, split memberships, cross-validation scores, and bootstrap diagnostics |
| `reports/figures/` | Generated charts and diagrams |
| `reports/tables/report_artifact_map.json` | Mapping between numbered results and generated files |
| `reports/report_comparison.json` and `.md` | Individual numerical checks and their summary |
| `reports/run_manifest.json` | Input and generated-file checksums for the execution |

## Code organization

| Path | Responsibility |
| --- | --- |
| `final_pipeline.py` | Complete analysis entry point |
| `src/` | Shared data preparation, model analysis, output generation, and verification |
| `notebooks/` | Interactive analysis and full-pipeline execution |
| `scripts/` | Verification and supporting utilities |
| `tests/` | Automated checks of analysis and verification behavior |
| `docs/` | Data dictionary, provenance, and analysis protocol |
| `requirements.txt` | Pinned analysis dependencies |

Code licensing is described in [LICENSE](LICENSE). Consult the official data-source terms for reuse of Anatel and IBGE data.
