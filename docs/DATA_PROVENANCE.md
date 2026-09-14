# Data Provenance — Source-to-Variable Lineage

This document reproduces Table 3 of the final report. It records, for each of the 25 columns of
`data/processed/merged_municipal_dataset.csv`, the publisher, the current official access point,
the derived variables built by `final_pipeline.py`, and the grain after aggregation.

## Reproducibility anchor

| Item | Value |
|---|---|
| Committed analysis input | `data/processed/merged_municipal_dataset.csv` (10,107 rows × 25 columns; 5,571 unique municipalities) |
| SHA-256 | `50fac84b16f63d66628741f36686cc076f43c90632a3befe53ca43ed9b316207` |
| Recorded by | `final_pipeline.py` writes `input_sha256` to `reports/tables/headline_results.json` on every run |
| Verify locally | `python src/data_loader.py --check` |

**Scope of reproducibility.** The executable analysis starts from the committed
municipal CSV and records its checksum, source hashes, software environment,
results, and diagnostics. Official source links document dataset-level lineage.
Original historical snapshots, complete acquisition periods, and the SLP registry
grain are not authenticated by rerunning the municipal analysis. Newly downloaded
data require a separately documented acquisition and validation process.

## Lineage table

| Source (publisher) | Access point | Columns supplied | Derived variables | Grain after aggregation | Reference period / publication cadence |
|---|---|---|---|---|---|
| IBGE Census 2022 (SIDRA) | https://servicodados.ibge.gov.br/api/docs/agregados — municipal Census table with variables V93, V6318, V614 | `V93_populacao residente`, `V6318_area da unidade terr`, `V614_densidade demografic` | `POP_CENSUS_2022`, `AREA_KM2`, `POP_DENSITY` | 1 row per municipality | Census 2022 (decennial); reference year 2022 |
| IBGE PIB dos Municípios and Estimativas da População (SIDRA) | https://servicodados.ibge.gov.br/api/docs/agregados ; https://cidades.ibge.gov.br | `PIB_MIL_REAIS`, `POP_2024`, `NOME`, `UF` | `GDP_PER_CAP` (= PIB_MIL_REAIS × 1,000 / POP_2024) | 1 row per municipality | PIB: annual, about two-year lag; latest release at acquisition (Dec 2025) covers 2022–2023; reference year of the extract not recorded. POP_2024: annual estimates, 2024 vintage |
| Anatel mobile accesses (SMP) | https://dados.gov.br/dados/conjuntos-dados/acessos-autorizadas-smp | `ACC_CDMA_IS_95`, `ACC_GSM`, `ACC_LTE`, `ACC_NR`, `ACC_WCDMA` | `LTE_ACCESS_PER_100`, `NR_ACCESS_PER_100` | Summed over providers; 1 row per municipality | Monthly (operators report the prior month by the 15th); reference month not recorded |
| Anatel licensed stations (ERB) | https://dados.gov.br/dados/conjuntos-dados/outorga-e-licenciamento---estaes-licenciadas | `ERB_CDMA`, `ERB_EDGE`, `ERB_GSM`, `ERB_LTE`, `ERB_NR`, `ERB_WCDMA` | `NR_STATION_CNT` (= ERB_NR), `NR_PER_100K_POP`, `HIGH_NR_P75` | Counted by technology; 1 row per municipality | Continuous licensing registry; snapshot at acquisition |
| Anatel SLP registry (Serviço Limitado Privado) | https://www.anatel.gov.br/dadosabertos/ (legacy catalog page decommissioned) | `SLP_STATION_CNT`, `PRIVATE_5G_LIC` | `SLP_PER_100K_POP`, `HIGH_SLP` | More than one record per municipality: 4,343 municipalities receive 2 rows differing only in `SLP_STATION_CNT`; summed by the pipeline | Continuous authorization registry; snapshot at acquisition |
| Anatel Meu Município panorama | https://informacoes.anatel.gov.br/paineis/ | `FIBER_ACCESSES`, `FIBER_BACKHAUL` | `FIBER_PER_100` | 1 row per municipality | Periodic panel; reference period not recorded |
| Anatel measured download speed | https://informacoes.anatel.gov.br/paineis/ — specific extract not recorded | `AVG_DL_SPEED` | `AVG_DL_SPEED` (EDA and RQ3 only) | 1 row per municipality | Periodic panel; reference period not recorded |

`MUNICIP_ID` (7-digit IBGE code, zero-padded string) is the join key. All 25 columns are accounted for.

**Lineage evidence.** The IBGE columns carry SIDRA variable codes in their names (V93, V6318, V614 co-occur in the
Census 2022 municipal table); the access and station columns carry Anatel's technology-generation categories;
the SLP registry is identifiable from its one-to-many join signature (within each duplicated municipality only
`SLP_STATION_CNT` differs). `AVG_DL_SPEED` is the one column without a recoverable fingerprint.

**Publication cadence.** IBGE's municipal GDP is annual with roughly a two-year lag (the 2022–2023 edition was released in December 2025 and, for those years, contains total GDP and GDP per capita only); population estimates are annual; the Census is decennial; Anatel mobile accesses are reported monthly (operators submit the prior month by the 15th); the licensed-station and SLP registries are continuously updated, so those columns are snapshots at acquisition. `GDP_PER_CAP` divides a PIB value of unrecorded reference year by the 2024 population estimate.

See `reports/figures/figure00b_source_merge.png` (Figure 2 of the final report) for the merge design.
