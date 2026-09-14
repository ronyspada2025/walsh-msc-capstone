# QM640 Data Analytics Capstone

## Municipal Correlates of Licensed 5G NR Infrastructure in Brazil

### Presence, Intensity, and Digital-Infrastructure Profiles

**Author:** Rony Anderson Spada Pedroso
**Institution:** Walsh College
**Course:** QM640: Data Analytics Capstone
**Mentor:** Dr. Sridhar Srinivas
**Term:** August 2026
**Current report version:** Final Report, Revised (September 13, 2026)

> **Construct note.** Licensed NR station counts are an observable radio-infrastructure footprint and are **not** evidence of 5G Standalone core, cloud-native, or virtualized RAN operation, and SLP intensity is a broad private-network-related proxy, **not** verified private 5G adoption.

## Project Overview

This repository supports a data analytics capstone that analyzes where licensed 5G New Radio (NR) infrastructure appears across all 5,571 Brazilian municipalities and how intensive deployment becomes after arrival, using open public data from the National Telecommunications Agency (Anatel) and the Brazilian Institute of Geography and Statistics (IBGE).

## Research Questions

- **RQ1 — High-count NR rollout classification.** Can structural municipal (socioeconomic and infrastructure) characteristics predict whether a municipality is a high-count licensed 5G NR rollout site, and does the result hold when the target is redefined on a per-capita basis?
- **RQ2 — Structural correlates of NR station intensity.** To what extent are structural characteristics associated with population-normalized NR station intensity, and which characteristics carry statistically significant associations? (Two-part hurdle framework: presence logistic + zero-truncated negative binomial with population offset.)
- **RQ3 — Digital-infrastructure profile segmentation.** How do municipalities cluster on digital-infrastructure profile indicators, and how strongly is cluster membership associated with macro-region?
- **RQ4 — Correlates of SLP station intensity (exploratory, supplementary).** Which characteristics are associated with high private-network-related SLP station intensity, and does the association generalize across states?

## Headline Results (Final Report, Tables 11–14)

Primary final estimates are repeated stratified 5×5 cross-validation on the full modeling frame (N = 5,564), confirmed once on an independent seed-2026 holdout; the seed-42 development split is retained as the transparent development comparison.

| RQ | Model | Development split (seed 42) | Repeated 5×5 CV | Fresh split (seed 2026) |
| --- | --- | --- | --- | --- |
| RQ1 | Random forest, count target (leakage-free, tuned) | ROC-AUC .927 [.906, .945]; F1 .808 | .920 ± .009 | .919 [.899, .938]; F1 .773 |
| RQ1 | Random forest, per-capita target (re-tuned) | ROC-AUC .817 [.790, .845]; F1 .593 | .824 ± .017 | .825 [.801, .851]; F1 .590 |
| RQ2 | Hurdle part 1: presence logistic | ROC-AUC .849 [.826, .870] | .849 ± .014 | .844 [.821, .864] |
| RQ2 | Hurdle part 2: zero-truncated NB (n = 2,192 NR-present; population offset) | α = 0.66; McFadden pseudo-R² = .017; γ = −.14 (sub-proportional); rate ratios: density 1.25, fiber 1.14, GDP/cap 1.11 (state-clustered t(26) CIs) | — | — |
| RQ2 | Ridge (predictive complement) | Held-out R² = .02 [−.08, .09] raw; .06 [−.15, .18] log1p (CIs include 0) | — | — |
| RQ3 | K-means (k = 2) + chi-square | Silhouette .305; bootstrap ARI .99 ± .01; χ²(4) = 254.1, p < .001; Cramér's V = .21 | — | — |
| RQ4 | Balanced logistic (exploratory) | ROC-AUC .810 [.786, .836]; PR-AUC .623 | .798 ± .010 | .780 [.749, .806] |

State-grouped (GroupKFold by 27 UFs) validation: RQ1 count .909 ± .023; RQ2 presence .839 ± .035; RQ4 .758 ± .067. A naive RQ1 specification including near-target variables reaches .965 and is reported only as a leakage demonstration. The supplementary **unconditional** negative binomial (full frame; α = 4.42; γ = +.19) mixes the presence and intensity margins and is not a hurdle component.

## Reproduction

```
pip install -r requirements.txt
python final_pipeline.py
```

`requirements.txt` pins `scikit-learn==1.8.0`. On Linux x86-64 every value regenerates exactly; on Apple Silicon macOS random-forest metrics shift by at most ±.001 with no change in any conclusion. The pipeline regenerates every number, table, and figure of the final report (Figures 1–11) from the committed analysis input with fixed seeds, writing to `reports/figures` and `reports/tables` (including machine-readable `headline_results.json`). `notebooks/06_final_report_pipeline_colab.ipynb` runs the identical pipeline in Google Colab.

## Data Provenance and Reproducibility Scope

Provenance is reported at two levels (Final Report, Table 3 and Appendix B):

- **Computational reproducibility from the committed merge is exact.** The committed analysis input `data/processed/merged_municipal_dataset.csv` has SHA-256 `50fac84b16f63d66628741f36686cc076f43c90632a3befe53ca43ed9b316207`; `final_pipeline.py` recomputes and records it in `headline_results.json`, and `python src/data_loader.py --check` verifies columns and checksum.
- **Upstream acquisition reproducibility is dataset-level.** Each source family is mapped to its official landing page and current direct resource or SIDRA table, with vintage, grain, and unresolved fields stated explicitly, under assurance classes A/B/C. The historical raw snapshot bytes were not archived, so byte-identical historical reproduction is not claimed. The machine-readable manifest is committed at `docs/data_provenance_manifest_v6.csv` and mirrored in `docs/DATA_PROVENANCE.md` (Appendix B of the final report).

| Source family | Official access | Assurance |
| --- | --- | --- |
| IBGE Census 2022 (pop., area, density) | https://sidra.ibge.gov.br/tabela/4714 | A |
| IBGE population estimate 2024 | https://sidra.ibge.gov.br/tabela/6579 | A |
| IBGE municipal GDP (PIB dos Municípios) | https://sidra.ibge.gov.br/tabela/5938 | B |
| Anatel mobile accesses (SMP) | https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_telefonia_movel.zip | B |
| Anatel licensed stations | https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_licenciadas.zip | B |
| Anatel Meu Município (fiber/backhaul) | https://informacoes.anatel.gov.br/paineis/ (`meu_municipio.zip`) | B |
| Anatel SLP / Redes Privativas | https://www.gov.br/anatel/pt-br/regulado/radiofrequencia/redes-privativas | C |
| Anatel measured mobile speed | https://informacoes.anatel.gov.br/paineis/ (`medidas_qoe_smp.zip` candidate) | C |

## Repository Structure

```
.
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
├── final_pipeline.py            (authoritative reproduction path)
├── data/
│   ├── raw/                     (git-ignored; downloaded locally)
│   └── processed/
│       └── merged_municipal_dataset.csv   (committed analysis input, 1.8 MB)
├── docs/
│   ├── DATA_DICTIONARY.md
│   ├── DATA_PROVENANCE.md       (Table 3 / Appendix B: source-to-variable lineage)
│   └── data_provenance_manifest_v6.csv    (machine-readable Appendix B manifest)
├── notebooks/
│   ├── 01_data_cleaning_and_alignment.ipynb   (scaffold: acquisition design)
│   ├── 02_feature_engineering.ipynb
│   ├── 03_exploratory_data_analysis.ipynb
│   ├── 04_statistical_tests_rq2_rq4.ipynb
│   ├── 05_ml_pipelines_rq1_rq3_rq5_rq6.ipynb  (legacy filename from synopsis-era RQ numbering)
│   └── 06_final_report_pipeline_colab.ipynb   (Colab mirror of final_pipeline.py)
├── reports/
│   ├── figures/                 (Figures 1–11 of the final report)
│   └── tables/                  (result tables + headline_results.json)
└── src/
    ├── __init__.py
    ├── data_loader.py
    ├── feature_engineering.py
    ├── model_evaluation.py
    └── visualization_utils.py
```

## Data Notes

- The supplied merge contains 10,107 rows × 25 columns with exactly 5,571 unique municipalities; the pipeline drops 193 exact duplicates and collapses 4,343 duplicate municipal keys (first non-null for stable variables; **sum** for `SLP_STATION_CNT`, with max/mean/first tested as RQ4 sensitivity; max for `PRIVATE_5G_LIC`), yielding 5,571 × 42 after feature engineering. The sum rule preserves both supplied SLP counts without asserting it reconstructs the unarchived historical registry grain; RQ4 therefore remains exploratory.
- The binary fiber flag is saturated (100% of non-missing values = 1); `FIBER_PER_100` is the substantive fiber measure.
- `NR_ACCESS_PER_100` and `AVG_DL_SPEED` are excluded from RQ1/RQ2 predictor sets as near-target (leakage) variables; they are used only in EDA and RQ3.
- Raw Anatel/IBGE extracts are excluded from version control because of size; acquisition is documented in `src/data_loader.py` and `docs/DATA_PROVENANCE.md`. Source landing pages verified July 23, 2026; raw extracts acquired August 2026; original snapshot bytes not archived (stated limitation).

## License

MIT — see `LICENSE`.
