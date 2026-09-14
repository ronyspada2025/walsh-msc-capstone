# Version 6 Local Raw-Source Inventory

- Audit time (UTC): `2026-09-02T00:27:03.411783+00:00`
- Raw directory inspected: `data/raw`
- Raw directory exists: `no`
- Source families with at least one filename match: `0/10`
- Matching local files recorded: `0`

This inventory is evidence of local file presence and byte identity within the local workspace. It is **not** evidence that a local file is the same historical snapshot currently served by a publisher, and it does not establish record grain merely from a filename. Raw files remain outside Git.

| Source ID | Expected identifier | Status | Local file | SHA-256 | Remaining gate |
|---|---|---|---|---|---|
| IBGE_CENSUS_2022 | SIDRA Table 4714 / Census 2022 municipal export | NOT_FOUND |  |  | Confirm population, area, density variables and 7-digit municipal key; record the historical export date. |
| IBGE_POP_2024 | SIDRA Table 6579 / 2024 municipal population estimate | NOT_FOUND |  |  | Confirm the file is the 2024 municipal estimate and retains the IBGE municipal code. |
| IBGE_GDP_MUNICIPAL | SIDRA Table 5938 / PIB dos Municipios | NOT_FOUND |  |  | Recover the GDP reference year; compare the local schema with Table 5938 before assigning a vintage. |
| ANATEL_SMP | acessos_telefonia_movel.zip | NOT_FOUND |  |  | Confirm provider/month fields, reference month, technology columns, and municipality aggregation. |
| ANATEL_FIXED_BROADBAND_COMPARISON | acessos_banda_larga_fixa.zip (supplementary comparison; not automatically mapped to FIBER_PER_100) | NOT_FOUND |  |  | Treat as a comparison source only unless its columns are shown to be the source of the frozen fiber variables. |
| ANATEL_ERB | estacoes_licenciadas.zip | NOT_FOUND |  |  | Confirm NR technology coding, station-count rule, municipality key, and historical snapshot date. |
| ANATEL_FIBER | meu_municipio.zip | NOT_FOUND |  |  | Confirm FIBER_ACCESSES/FIBER_BACKHAUL fields, reference period, and one-row-per-municipality grain. |
| ANATEL_SLP | redes_privativas.zip | NOT_FOUND |  |  | MANDATORY MANUAL GATE: establish why municipalities have multiple records and whether sum/max/mean/first has a documented meaning. Do not promote RQ4 automatically. |
| ANATEL_SPEED_QOE | medidas_qoe_smp.zip | NOT_FOUND |  |  | Compare columns and aggregation fields with AVG_DL_SPEED; identify the reference period. |
| ANATEL_SPEED_MAP | mapa_download_smp.zip (alternative speed-schema candidate) | NOT_FOUND |  |  | Compare against the local speed schema; do not attribute AVG_DL_SPEED until the matching source is demonstrated. |

## Non-automatic SLP decision

The audit deliberately does not change the SLP assurance class or RQ4 status. Promotion requires a documented comparison of the local SLP schema, registry grain, and the meaning of multiple records per municipality.
