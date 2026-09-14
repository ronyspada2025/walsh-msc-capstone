# Current Raw-Source Refresh and Provenance Audit

Generated: `2026-09-14T02:22:24.317191+00:00`  
Audit script version: `6.1`  
Repository: `/Users/ronypedroso/Downloads/brazil-cloud-native-telecom-capstone`  
Local raw release: `/Users/ronypedroso/Downloads/brazil-cloud-native-telecom-capstone/data/raw/2026-09-13_refresh`

> **Interpretation rule:** These files are current official source refreshes. They are not automatically the byte-identical historical extracts used to create the frozen merged dataset. A byte-identical claim is made only where SHA-256 comparison with an existing local historical file succeeds.

| source_id | status | filename | size | sha256 | validation | historical_hash_match |
|---|---|---|---|---|---|---|
| anatel_mobile_accesses_smp | existing_valid | acessos_telefonia_movel.zip | 2.97 GB | 91c6230339238114d8edec4be3d4e5e25246c2d1910fbd1db76f496ab9bad69a | valid ZIP archive |  |
| anatel_licensed_stations | existing_valid | estacoes_licenciadas.zip | 211.52 MB | 1c32eea16487b3022c157d04861cdaad663e232bab69b184f28a380a75b20a4d | valid ZIP archive |  |
| anatel_meu_municipio | existing_valid | meu_municipio.zip | 18.23 MB | 21188c1aae5d7d4167c6c7e83bf37250a33d1027ae1ae20fff9c07902e293b57 | valid ZIP archive |  |
| anatel_private_networks_slp | existing_valid | redes_privativas.zip | 178.26 MB | 27db526b80cab22f93763d62e8c709985ec281e24938c36fccdaf5a5a2561688 | valid ZIP archive |  |
| anatel_mobile_speed_qoe | existing_valid | medidas_qoe_smp.zip | 954.48 MB | 0c21bbceaae27441cd01798589e0aa30cb719d3e8f9331bdbed82d2c4e2583aa | valid ZIP archive |  |
| anatel_mobile_download_map | existing_valid | mapa_download_smp.zip | 10.78 MB | 186dbaa66565b35ba664dad63e9b258f575a2d6c171dd96a5ddb602610b73e76 | valid ZIP archive |  |
| ibge_sidra_4714_census2022 | existing_valid | sidra_4714_2022.json | 3.08 MB | 818ab99e15b87408fd9e2240a9b73a510721498e4300b2ada61bf90b0ee77ade | valid JSON |  |
| ibge_sidra_6579_population2024 | existing_valid | sidra_6579_2024.json | 1010.77 KB | a2b62956c5a7070606e7d323208a9a305e8a3b37799150462fe8c5de639f386d | valid JSON |  |
| ibge_sidra_5938_pib2023 | existing_valid | sidra_5938_2023.json | 1.05 MB | 8d05b2a042b8c8d4eb4bf5a34f291166210f2742a066158a572e06e0d9321ff3 | valid JSON |  |

## Official source links

### anatel_mobile_accesses_smp

- Publisher: Anatel
- Role: LTE_ACCESS_PER_100 and NR_ACCESS_PER_100 source family
- Direct resource: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_telefonia_movel.zip
- Landing page: https://dados.gov.br/dados/conjuntos-dados/acessos-autorizadas-smp
- Refresh SHA-256: `91c6230339238114d8edec4be3d4e5e25246c2d1910fbd1db76f496ab9bad69a`
- Previous assurance class: B

### anatel_licensed_stations

- Publisher: Anatel
- Role: NR_STATION_CNT / NR_PER_100K_POP source family
- Direct resource: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_licenciadas.zip
- Landing page: https://dados.gov.br/dados/conjuntos-dados/outorga-e-licenciamento---estaes-licenciadas
- Refresh SHA-256: `1c32eea16487b3022c157d04861cdaad663e232bab69b184f28a380a75b20a4d`
- Previous assurance class: B

### anatel_meu_municipio

- Publisher: Anatel
- Role: FIBER_ACCESSES / FIBER_BACKHAUL source candidate
- Direct resource: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/meu_municipio/meu_municipio.zip
- Landing page: https://dados.gov.br/dados/conjuntos-dados/meu-municipio---acessos-e-cobertura-de-telecomunicacoes
- Refresh SHA-256: `21188c1aae5d7d4167c6c7e83bf37250a33d1027ae1ae20fff9c07902e293b57`
- Previous assurance class: B

### anatel_private_networks_slp

- Publisher: Anatel
- Role: SLP_STATION_CNT / PRIVATE_5G_LIC candidate source
- Direct resource: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/redes_privativas.zip
- Landing page: https://dados.gov.br/dados/conjuntos-dados/outorga-e-licenciamento---atos-de-radiofrequncia
- Refresh SHA-256: `27db526b80cab22f93763d62e8c709985ec281e24938c36fccdaf5a5a2561688`
- Previous assurance class: C

### anatel_mobile_speed_qoe

- Publisher: Anatel
- Role: AVG_DL_SPEED candidate source
- Direct resource: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/qualidade/medidas_qoe_smp.zip
- Landing page: https://dados.gov.br/dados/conjuntos-dados/qualidade---medidas-de-velocidade---telefonia-movel
- Refresh SHA-256: `0c21bbceaae27441cd01798589e0aa30cb719d3e8f9331bdbed82d2c4e2583aa`
- Previous assurance class: C

### anatel_mobile_download_map

- Publisher: Anatel
- Role: Alternative candidate for AVG_DL_SPEED
- Direct resource: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/qualidade/mapa_download_smp.zip
- Landing page: https://dados.gov.br/dados/conjuntos-dados/qualidade---mapa---download---telefonia-movel
- Refresh SHA-256: `186dbaa66565b35ba664dad63e9b258f575a2d6c171dd96a5ddb602610b73e76`
- Previous assurance class: C

### ibge_sidra_4714_census2022

- Publisher: IBGE/SIDRA
- Role: POP_CENSUS_2022 / AREA_KM2 / POP_DENSITY
- Direct resource: https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93,6318,614/p/2022?formato=json
- Landing page: https://sidra.ibge.gov.br/tabela/4714
- Refresh SHA-256: `818ab99e15b87408fd9e2240a9b73a510721498e4300b2ada61bf90b0ee77ade`
- Previous assurance class: A

### ibge_sidra_6579_population2024

- Publisher: IBGE/SIDRA
- Role: POP_2024 source family
- Direct resource: https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/all/p/2024?formato=json
- Landing page: https://sidra.ibge.gov.br/tabela/6579
- Refresh SHA-256: `a2b62956c5a7070606e7d323208a9a305e8a3b37799150462fe8c5de639f386d`
- Previous assurance class: A

### ibge_sidra_5938_pib2023

- Publisher: IBGE/SIDRA
- Role: PIB_MIL_REAIS / GDP_PER_CAP source family
- Direct resource: https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/all/p/2023?formato=json
- Landing page: https://sidra.ibge.gov.br/tabela/5938
- Refresh SHA-256: `8d05b2a042b8c8d4eb4bf5a34f291166210f2742a066158a572e06e0d9321ff3`
- Previous assurance class: B

