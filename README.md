# Municipal Correlates of Licensed 5G NR Infrastructure in Brazil

**Rony Anderson Spada Pedroso · Walsh College · MSc in AI and ML · QM640**

This study analyzes municipal socioeconomic and infrastructure correlates of licensed
5G New Radio (NR) deployment in Brazil. It addresses high station counts, per-capita
intensity, infrastructure profiles, and exploratory Serviço Limitado Privado (SLP)
station intensity using a preserved municipal Anatel/IBGE dataset.

## Final documents

- [Final report](docs/final_report.pdf)
- [Final presentation](docs/final_presentation.pdf)
- [Analysis protocol and interpretation](docs/REPRODUCTION_NOTES.md)
- [Data provenance](docs/DATA_PROVENANCE.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)

The report has a 330-word abstract. `docs/document_manifest.json` identifies the
documents and the analysis execution supporting the report.

## Findings

| Analysis | Result |
| --- | --- |
| High NR station counts | Structural random forest ROC-AUC .927; approximately .82 with a per-capita classification target |
| NR presence | ROC-AUC .849 |
| Full municipal-frame intensity | Ridge R² .02 for raw intensity and .06 for log intensity; both 95% intervals include zero |
| Infrastructure profiles | Two clusters; silhouette .305; Cramér's V .21 for macro-region association |
| Exploratory SLP intensity | ROC-AUC .810; weaker performance across states |

The findings support municipal screening and comparison. Continuous intensity
forecasting across the national municipal frame remains limited. Licensed station
counts do not identify Standalone or cloud-native operation, and the cross-sectional
associations do not establish causation, engineering feasibility, or compliance.
Complete results, including the analysis of NR-present municipalities, are in the
report's technical sections and generated tables.

## Run the analysis

Use Python 3.12 and Git on macOS or Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LOKY_MAX_CPU_COUNT=4 .venv/bin/python final_pipeline.py --jobs 4
.venv/bin/python scripts/verify_project.py
```

The full pipeline includes 999 state-bootstrap draws, 1,000 held-out bootstrap
resamples per interval, and repeated stratified five-fold CV with five repeats.
Runtime depends on the computer. A smaller `--state-bootstrap` value is diagnostic
and cannot pass the full-analysis verification gate.

To inspect the included executed results without training again, install the
requirements and run `scripts/verify_project.py` directly.

## Google Colab and notebooks

[Open the complete analysis in Colab](https://colab.research.google.com/github/ronyspada2025/walsh-msc-capstone/blob/main/notebooks/06_final_report_pipeline_colab.ipynb).

Notebook 06 runs `final_pipeline.py` and the verification gate. Notebooks 01-05
cover cleaning, feature engineering, exploration, inference, and predictive models.
They use the same preparation functions or verified outputs. Optional local notebook
UI dependencies are in `requirements-notebooks.txt`.

## Outputs and verification

`reports/tables/headline_results.json` is the canonical numerical result. The
pipeline also exports report-numbered tables, figures, held-out municipal predictions,
split memberships, cross-validation scores, and bootstrap coefficients and diagnostics.
`reports/tables/report_artifact_map.json` maps report numbering to generated files.

```bash
.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/compare_headline_results.py
.venv/bin/python -m unittest discover -s tests -v
```

Verification checks data and source hashes, output integrity, complete execution,
partitions, convergence, and agreement with the fixed numerical reference in
`scripts/final_report_reference.json`. This reference is used after estimation;
models do not use it to select parameters or replace predictions. Exit status **0**
means success, **2** means a numerical disagreement, and **1** means invalid or
incomplete evidence. `reports/report_comparison.json` retains all individual checks.

## Data scope

Input: `data/processed/merged_municipal_dataset.csv`.

SHA-256: `50fac84b16f63d66628741f36686cc076f43c90632a3befe53ca43ed9b316207`.

Cleaning removes 193 exact duplicate rows and aggregates 4,343 additional municipal-key
rows, producing 5,571 municipalities and 5,564 complete modeling rows. There are 42
columns before four targets are appended; classification models use nine structural
predictor columns. Official source links and unresolved historical acquisition fields
are documented separately.

## Repository updater

The downloadable `update_walsh_capstone_final.sh` contains the project files,
executed results, and final documents. It validates the package, creates a fresh folder
under Downloads, installs the pinned dependencies, and verifies the complete project.
Add `--push` to commit and publish to `main`; `--branch <name>` publishes a new branch.
Use `--recompute` to run every model locally before verification. The updater uses
ordinary Git pushes and retains the working folder if publication cannot complete.
