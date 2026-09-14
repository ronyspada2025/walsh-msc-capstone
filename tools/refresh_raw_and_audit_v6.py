#!/usr/bin/env python3
"""
Walsh QM640 Brazil 5G Capstone
Current-source refresh + provenance audit


Designed for users with limited CLI experience.


WHAT THIS SCRIPT DOES
---------------------
1. Finds the local brazil-cloud-native-telecom-capstone repository.
2. Downloads current official Anatel/IBGE source datasets into:
       ~/Downloads/Capstone_Raw_Refresh_YYYY-MM-DD/
3. Validates downloads (ZIP / JSON / blocking-page detection).
4. Copies valid files into:
       <repo>/data/raw/YYYY-MM-DD_refresh/
5. DOES NOT overwrite older raw files.
6. DOES NOT alter merged_municipal_dataset.csv.
7. DOES NOT rerun final_pipeline.py.
8. DOES NOT run git add / commit / push.
9. Calculates SHA-256 checksums.
10. Inspects ZIP members and candidate CSV headers.
11. Compares refreshed files with older local files having the same name.
12. Creates:
       reports/provenance/raw_source_inventory_v6.csv
       reports/provenance/raw_source_inventory_v6.md
       docs/DATA_PROVENANCE_REFRESH_<date>.md
       docs/data_provenance_manifest_refresh_<date>.csv
13. Ensures data/raw/ is ignored by Git.
14. Copies this script into:
       tools/refresh_raw_and_audit_v6.py


IMPORTANT
---------
A current official download is NOT automatically evidence that it is the
byte-identical historical extract used to create the frozen merged dataset.


If an existing local historical file has the SAME SHA-256 as the new
official download, the audit will explicitly flag that match.


No external Python packages are required.
"""


from __future__ import annotations


import csv
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import webbrowser
import zipfile


from datetime import date, datetime, timezone
from pathlib import Path




# ============================================================
# BASIC SETTINGS
# ============================================================


TODAY = date.today().isoformat()


HOME = Path.home()


DOWNLOADS = HOME / "Downloads"


STAGING_DIR = DOWNLOADS / f"Capstone_Raw_Refresh_{TODAY}"


RELEASE_NAME = f"{TODAY}_refresh"


SCRIPT_VERSION = "6.1"




# ============================================================
# OFFICIAL CURRENT SOURCES
# ============================================================
#
# These are current official source resources/source-family
# endpoints. They should NOT be described as the original
# historical August 2026 snapshot unless hashes demonstrate
# that they are identical to an existing historical local file.
# ============================================================


SOURCES = [


    # --------------------------------------------------------
    # ANATEL MOBILE ACCESSES / SMP
    # --------------------------------------------------------
    {
        "id": "anatel_mobile_accesses_smp",
        "publisher": "Anatel",
        "description": "Mobile accesses / SMP by technology",
        "filename": "acessos_telefonia_movel.zip",
        "direct_url":
            "https://www.anatel.gov.br/dadosabertos/"
            "paineis_de_dados/acessos/"
            "acessos_telefonia_movel.zip",
        "landing_url":
            "https://dados.gov.br/dados/conjuntos-dados/"
            "acessos-autorizadas-smp",
        "expected_type": "zip",
        "analysis_role":
            "LTE_ACCESS_PER_100 and NR_ACCESS_PER_100 source family",
        "assurance_before_refresh": "B",
    },


    # --------------------------------------------------------
    # ANATEL LICENSED STATIONS / ERB
    # --------------------------------------------------------
    {
        "id": "anatel_licensed_stations",
        "publisher": "Anatel",
        "description": "Licensed telecommunications stations / ERB",
        "filename": "estacoes_licenciadas.zip",
        "direct_url":
            "https://www.anatel.gov.br/dadosabertos/"
            "paineis_de_dados/outorga_e_licenciamento/"
            "estacoes_licenciadas.zip",
        "landing_url":
            "https://dados.gov.br/dados/conjuntos-dados/"
            "outorga-e-licenciamento---estaes-licenciadas",
        "expected_type": "zip",
        "analysis_role":
            "NR_STATION_CNT / NR_PER_100K_POP source family",
        "assurance_before_refresh": "B",
    },


    # --------------------------------------------------------
    # ANATEL MEU MUNICIPIO
    # --------------------------------------------------------
    {
        "id": "anatel_meu_municipio",
        "publisher": "Anatel",
        "description":
            "Meu Municipio municipal access/coverage infrastructure",
        "filename": "meu_municipio.zip",
        "direct_url":
            "https://www.anatel.gov.br/dadosabertos/"
            "paineis_de_dados/meu_municipio/"
            "meu_municipio.zip",
        "landing_url":
            "https://dados.gov.br/dados/conjuntos-dados/"
            "meu-municipio---acessos-e-cobertura-de-telecomunicacoes",
        "expected_type": "zip",
        "analysis_role":
            "FIBER_ACCESSES / FIBER_BACKHAUL source candidate",
        "assurance_before_refresh": "B",
    },


    # --------------------------------------------------------
    # ANATEL PRIVATE NETWORKS / SLP
    # --------------------------------------------------------
    {
        "id": "anatel_private_networks_slp",
        "publisher": "Anatel",
        "description":
            "Redes Privativas / SLP private-network source candidate",
        "filename": "redes_privativas.zip",
        "direct_url":
            "https://www.anatel.gov.br/dadosabertos/"
            "paineis_de_dados/outorga_e_licenciamento/"
            "redes_privativas.zip",
        "landing_url":
            "https://dados.gov.br/dados/conjuntos-dados/"
            "outorga-e-licenciamento---atos-de-radiofrequncia",
        "expected_type": "zip",
        "analysis_role":
            "SLP_STATION_CNT / PRIVATE_5G_LIC candidate source",
        "assurance_before_refresh": "C",
    },


    # --------------------------------------------------------
    # ANATEL MOBILE QUALITY / SPEED
    # --------------------------------------------------------
    {
        "id": "anatel_mobile_speed_qoe",
        "publisher": "Anatel",
        "description":
            "Measured mobile QoE / download-speed source candidate",
        "filename": "medidas_qoe_smp.zip",
        "direct_url":
            "https://www.anatel.gov.br/dadosabertos/"
            "paineis_de_dados/qualidade/"
            "medidas_qoe_smp.zip",
        "landing_url":
            "https://dados.gov.br/dados/conjuntos-dados/"
            "qualidade---medidas-de-velocidade---telefonia-movel",
        "expected_type": "zip",
        "analysis_role":
            "AVG_DL_SPEED candidate source",
        "assurance_before_refresh": "C",
    },


    # --------------------------------------------------------
    # ANATEL ALTERNATIVE DOWNLOAD MAP
    # --------------------------------------------------------
    {
        "id": "anatel_mobile_download_map",
        "publisher": "Anatel",
        "description":
            "Alternative Anatel mobile download-map source candidate",
        "filename": "mapa_download_smp.zip",
        "direct_url":
            "https://www.anatel.gov.br/dadosabertos/"
            "paineis_de_dados/qualidade/"
            "mapa_download_smp.zip",
        "landing_url":
            "https://dados.gov.br/dados/conjuntos-dados/"
            "qualidade---mapa---download---telefonia-movel",
        "expected_type": "zip",
        "analysis_role":
            "Alternative candidate for AVG_DL_SPEED",
        "assurance_before_refresh": "C",
    },


    # --------------------------------------------------------
    # IBGE CENSUS 2022 - TABLE 4714
    # --------------------------------------------------------
    {
        "id": "ibge_sidra_4714_census2022",
        "publisher": "IBGE/SIDRA",
        "description":
            "Census 2022 population, area and demographic density",
        "filename": "sidra_4714_2022.json",
        "direct_url":
            "https://apisidra.ibge.gov.br/values/"
            "t/4714/n6/all/v/93,6318,614/p/2022"
            "?formato=json",
        "landing_url":
            "https://sidra.ibge.gov.br/tabela/4714",
        "expected_type": "json",
        "analysis_role":
            "POP_CENSUS_2022 / AREA_KM2 / POP_DENSITY",
        "assurance_before_refresh": "A",
    },


    # --------------------------------------------------------
    # IBGE POPULATION ESTIMATE - TABLE 6579
    # --------------------------------------------------------
    {
        "id": "ibge_sidra_6579_population2024",
        "publisher": "IBGE/SIDRA",
        "description":
            "Estimated resident population by municipality, 2024",
        "filename": "sidra_6579_2024.json",
        "direct_url":
            "https://apisidra.ibge.gov.br/values/"
            "t/6579/n6/all/v/all/p/2024"
            "?formato=json",
        "landing_url":
            "https://sidra.ibge.gov.br/tabela/6579",
        "expected_type": "json",
        "analysis_role":
            "POP_2024 source family",
        "assurance_before_refresh": "A",
    },


    # --------------------------------------------------------
    # IBGE MUNICIPAL GDP - TABLE 5938
    # --------------------------------------------------------
    {
        "id": "ibge_sidra_5938_pib2023",
        "publisher": "IBGE/SIDRA",
        "description":
            "Municipal GDP / PIB dos Municipios, 2023 current release",
        "filename": "sidra_5938_2023.json",
        "direct_url":
            "https://apisidra.ibge.gov.br/values/"
            "t/5938/n6/all/v/all/p/2023"
            "?formato=json",
        "landing_url":
            "https://sidra.ibge.gov.br/tabela/5938",
        "expected_type": "json",
        "analysis_role":
            "PIB_MIL_REAIS / GDP_PER_CAP source family",
        "assurance_before_refresh": "B",
    },
]




# ============================================================
# DISPLAY HELPERS
# ============================================================


def line(char="=", width=76):
    print(char * width)




def heading(text):
    print()
    line("=")
    print(text)
    line("=")




def info(text):
    print(f"  {text}")




def warning(text):
    print(f"  WARNING: {text}")




def now_utc():
    return datetime.now(timezone.utc).isoformat()




# ============================================================
# REPOSITORY DISCOVERY
# ============================================================


def is_repo(path: Path) -> bool:
    """Check that this looks like the capstone repository."""
    if not path.exists() or not path.is_dir():
        return False


    expected = [
        path / "final_pipeline.py",
        path / "data",
        path / "docs",
    ]


    return all(p.exists() for p in expected)




def common_repo_candidates(script_path: Path):
    """Generate likely repository locations."""


    names = [
        HOME / "brazil-cloud-native-telecom-capstone",
        DOWNLOADS / "brazil-cloud-native-telecom-capstone",
        HOME / "Documents" / "brazil-cloud-native-telecom-capstone",
        HOME / "Desktop" / "brazil-cloud-native-telecom-capstone",
        script_path.parent / "brazil-cloud-native-telecom-capstone",
        Path.cwd() / "brazil-cloud-native-telecom-capstone",
        Path.cwd(),
    ]


    # Remove duplicates while preserving order.
    seen = set()


    for candidate in names:
        candidate = candidate.expanduser().resolve()


        if candidate not in seen:
            seen.add(candidate)
            yield candidate




def choose_repo_gui() -> Path | None:
    """
    If auto-detection fails, try to display a normal folder picker.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog


        root = tk.Tk()
        root.withdraw()


        folder = filedialog.askdirectory(
            title=(
                "Select the brazil-cloud-native-telecom-capstone folder"
            )
        )


        root.destroy()


        if folder:
            return Path(folder).expanduser().resolve()


    except Exception:
        pass


    return None




def locate_repository(script_path: Path) -> Path:
    heading("LOCATING YOUR CAPSTONE REPOSITORY")


    for candidate in common_repo_candidates(script_path):


        info(f"Checking: {candidate}")


        if is_repo(candidate):
            print()
            print(f"FOUND REPOSITORY:")
            print(f"  {candidate}")
            return candidate


    print()
    print(
        "The repository was not found automatically.\n"
        "A folder selection window will now be opened."
    )


    selected = choose_repo_gui()


    if selected and is_repo(selected):
        return selected


    print()
    print(
        "Please paste the full path to the repository folder.\n"
        "Example:\n"
        "  C:\\Users\\YourName\\brazil-cloud-native-telecom-capstone\n"
        "or\n"
        "  /Users/YourName/brazil-cloud-native-telecom-capstone"
    )


    while True:


        entered = input("\nRepository folder: ").strip().strip('"')


        if not entered:
            continue


        candidate = Path(entered).expanduser().resolve()


        if is_repo(candidate):
            return candidate


        print(
            "\nThat folder does not appear to be the repository because "
            "final_pipeline.py / data / docs were not found."
        )




# ============================================================
# GITIGNORE SAFETY
# ============================================================


def ensure_raw_is_gitignored(repo: Path):
    """
    Make sure raw source datasets do not accidentally get committed.
    """


    gitignore = repo / ".gitignore"


    existing = ""


    if gitignore.exists():
        existing = gitignore.read_text(
            encoding="utf-8",
            errors="replace"
        )


    normalized = {
        line.strip()
        for line in existing.splitlines()
    }


    candidates = {
        "data/raw/",
        "/data/raw/",
        "data/raw/*",
        "/data/raw/*",
    }


    if normalized.intersection(candidates):
        return False


    with gitignore.open("a", encoding="utf-8") as f:


        if existing and not existing.endswith("\n"):
            f.write("\n")


        f.write(
            "\n"
            "# Raw government datasets are intentionally local only.\n"
            "# Source URLs/checksums are documented separately.\n"
            "data/raw/\n"
        )


    return True




# ============================================================
# FILE / HASH UTILITIES
# ============================================================


def sha256_file(path: Path, chunk_size=1024 * 1024) -> str:


    h = hashlib.sha256()


    with path.open("rb") as f:


        while True:


            chunk = f.read(chunk_size)


            if not chunk:
                break


            h.update(chunk)


    return h.hexdigest()




def human_size(size: int) -> str:


    value = float(size)


    for unit in ["B", "KB", "MB", "GB", "TB"]:


        if value < 1024 or unit == "TB":
            return f"{value:.2f} {unit}"


        value /= 1024


    return str(size)




def first_bytes(path: Path, count=4096) -> bytes:


    with path.open("rb") as f:
        return f.read(count)




def looks_like_html(path: Path) -> bool:


    raw = first_bytes(path).lstrip().lower()


    return (
        raw.startswith(b"<!doctype html")
        or raw.startswith(b"<html")
        or b"<html" in raw[:2048]
        or b"opera" in raw[:2048] and b"bloque" in raw[:2048]
    )




# ============================================================
# DOWNLOAD VALIDATION
# ============================================================


def validate_file(path: Path, expected_type: str):


    if not path.exists():
        return False, "file does not exist"


    if path.stat().st_size == 0:
        return False, "file is empty"


    if looks_like_html(path):
        return (
            False,
            "server returned an HTML/security page instead of data"
        )


    if expected_type == "zip":


        if not zipfile.is_zipfile(path):
            return False, "file is not a valid ZIP archive"


        return True, "valid ZIP archive"


    if expected_type == "json":


        try:


            with path.open(
                "r",
                encoding="utf-8-sig"
            ) as f:


                data = json.load(f)


            if not isinstance(data, (list, dict)):
                return False, "JSON has unexpected top-level structure"


            return True, "valid JSON"


        except Exception as exc:


            return False, f"invalid JSON: {exc}"


    return True, "file validation passed"




# ============================================================
# DOWNLOAD
# ============================================================


def download_file(url: str, destination: Path):


    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    partial = destination.with_suffix(
        destination.suffix + ".part"
    )


    headers = {
        "User-Agent":
            "Mozilla/5.0 "
            "(compatible; Walsh-QM640-Provenance-Refresh/6.1)",
        "Accept": "*/*",
        "Accept-Encoding": "identity",
    }


    request = urllib.request.Request(
        url,
        headers=headers
    )


    last_error = None


    for attempt in range(1, 4):


        try:


            print(f"  Download attempt {attempt}/3 ...")


            with urllib.request.urlopen(
                request,
                timeout=180
            ) as response:


                content_type = response.headers.get(
                    "Content-Type",
                    ""
                )


                with partial.open("wb") as target:


                    while True:


                        block = response.read(
                            1024 * 1024
                        )


                        if not block:
                            break


                        target.write(block)


            partial.replace(destination)


            return True, "download completed", content_type


        except Exception as exc:


            last_error = exc


            if partial.exists():
                try:
                    partial.unlink()
                except Exception:
                    pass


            if attempt < 3:
                time.sleep(2 * attempt)


    return False, str(last_error), ""




# ============================================================
# ZIP INSPECTION
# ============================================================


def decode_text(raw: bytes):


    for encoding in [
        "utf-8-sig",
        "utf-8",
        "latin-1",
        "cp1252",
    ]:


        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass


    return ""




def inspect_zip(path: Path):


    result = {
        "member_count": 0,
        "member_preview": "",
        "candidate_header": "",
    }


    if not zipfile.is_zipfile(path):
        return result


    try:


        with zipfile.ZipFile(path) as archive:


            members = [
                name
                for name in archive.namelist()
                if not name.endswith("/")
            ]


            result["member_count"] = len(members)


            result["member_preview"] = " | ".join(
                members[:15]
            )


            candidates = [
                name
                for name in members
                if name.lower().endswith(
                    (".csv", ".txt", ".tsv")
                )
            ]


            if candidates:


                with archive.open(candidates[0]) as f:
                    raw = f.read(65536)


                text = decode_text(raw)


                if text:


                    lines = text.splitlines()


                    if lines:
                        result["candidate_header"] = (
                            lines[0][:2000]
                        )


    except Exception as exc:


        result["candidate_header"] = (
            f"ZIP inspection error: {exc}"
        )


    return result




# ============================================================
# JSON INSPECTION
# ============================================================


def inspect_json(path: Path):


    result = {
        "record_count": "",
        "keys_preview": "",
    }


    try:


        with path.open(
            "r",
            encoding="utf-8-sig"
        ) as f:


            data = json.load(f)


        if isinstance(data, list):


            result["record_count"] = len(data)


            if data and isinstance(data[0], dict):


                result["keys_preview"] = ", ".join(
                    list(data[0].keys())[:30]
                )


        elif isinstance(data, dict):


            result["record_count"] = 1


            result["keys_preview"] = ", ".join(
                list(data.keys())[:30]
            )


    except Exception as exc:


        result["keys_preview"] = (
            f"JSON inspection error: {exc}"
        )


    return result




# ============================================================
# HISTORICAL LOCAL FILE COMPARISON
# ============================================================


def same_name_historical_files(
    raw_root: Path,
    new_release: Path,
    filename: str,
):


    matches = []


    if not raw_root.exists():
        return matches


    for candidate in raw_root.rglob(filename):


        try:


            candidate = candidate.resolve()


            if new_release.resolve() in candidate.parents:
                continue


            if candidate.is_file():
                matches.append(candidate)


        except Exception:
            pass


    return matches




# ============================================================
# SAFE COPY
# ============================================================


def copy_to_release(
    source: Path,
    release_dir: Path,
):


    release_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    destination = (
        release_dir / source.name
    )


    if destination.exists():


        source_hash = sha256_file(source)
        dest_hash = sha256_file(destination)


        if source_hash == dest_hash:
            return destination, "already present; identical"


        stem = destination.stem
        suffix = destination.suffix


        counter = 2


        while True:


            alternate = (
                release_dir /
                f"{stem}_{counter}{suffix}"
            )


            if not alternate.exists():
                destination = alternate
                break


            counter += 1


    shutil.copy2(
        source,
        destination
    )


    return destination, "copied"




# ============================================================
# REPORT WRITERS
# ============================================================


def escape_md(value):


    return (
        str(value)
        .replace("|", "\\|")
        .replace("\n", " ")
    )




def write_csv_report(
    records,
    output_path: Path
):


    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    if not records:
        return


    fieldnames = list(
        records[0].keys()
    )


    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:


        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )


        writer.writeheader()
        writer.writerows(records)




def write_md_report(
    records,
    output_path: Path,
    repo: Path,
    release_dir: Path,
):


    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    with output_path.open(
        "w",
        encoding="utf-8"
    ) as f:


        f.write(
            "# Current Raw-Source Refresh and Provenance Audit\n\n"
        )


        f.write(
            f"Generated: `{now_utc()}`  \n"
        )


        f.write(
            f"Audit script version: `{SCRIPT_VERSION}`  \n"
        )


        f.write(
            f"Repository: `{repo}`  \n"
        )


        f.write(
            f"Local raw release: `{release_dir}`\n\n"
        )


        f.write(
            "> **Interpretation rule:** These files are current "
            "official source refreshes. They are not automatically "
            "the byte-identical historical extracts used to create "
            "the frozen merged dataset. A byte-identical claim is "
            "made only where SHA-256 comparison with an existing "
            "local historical file succeeds.\n\n"
        )


        columns = [
            "source_id",
            "status",
            "filename",
            "size",
            "sha256",
            "validation",
            "historical_hash_match",
        ]


        f.write(
            "| " +
            " | ".join(columns) +
            " |\n"
        )


        f.write(
            "|" +
            "|".join(
                ["---"] * len(columns)
            ) +
            "|\n"
        )


        for record in records:


            values = [
                escape_md(
                    record.get(col, "")
                )
                for col in columns
            ]


            f.write(
                "| " +
                " | ".join(values) +
                " |\n"
            )


        f.write(
            "\n## Official source links\n\n"
        )


        for record in records:


            f.write(
                f"### {record['source_id']}\n\n"
            )


            f.write(
                f"- Publisher: {record['publisher']}\n"
            )


            f.write(
                f"- Role: {record['analysis_role']}\n"
            )


            f.write(
                f"- Direct resource: {record['direct_url']}\n"
            )


            f.write(
                f"- Landing page: {record['landing_url']}\n"
            )


            f.write(
                f"- Refresh SHA-256: "
                f"`{record.get('sha256', '')}`\n"
            )


            f.write(
                f"- Previous assurance class: "
                f"{record['assurance_before_refresh']}\n\n"
            )




# ============================================================
# COPY SCRIPT INTO REPOSITORY
# ============================================================


def install_script_copy(
    script_path: Path,
    repo: Path,
):


    tools = repo / "tools"


    tools.mkdir(
        parents=True,
        exist_ok=True
    )


    destination = (
        tools /
        "refresh_raw_and_audit_v6.py"
    )


    try:


        if script_path.resolve() != destination.resolve():


            shutil.copy2(
                script_path,
                destination
            )


            return destination


    except Exception:
        pass


    return destination




# ============================================================
# MAIN PROGRAM
# ============================================================


def main():


    script_path = (
        Path(__file__).resolve()
    )


    heading(
        "WALSH QM640 CAPSTONE - RAW SOURCE REFRESH & PROVENANCE AUDIT"
    )


    print(
        "\nThis program will download CURRENT official source files,\n"
        "audit them, and copy verified files into your LOCAL repository.\n"
    )


    print(
        "It will NOT modify your frozen merged dataset,\n"
        "NOT rerun the dissertation analysis,\n"
        "and NOT commit or push anything to GitHub.\n"
    )


    repo = locate_repository(
        script_path
    )


    raw_root = (
        repo / "data" / "raw"
    )


    release_dir = (
        raw_root / RELEASE_NAME
    )


    provenance_dir = (
        repo /
        "reports" /
        "provenance"
    )


    docs_dir = (
        repo / "docs"
    )


    # --------------------------------------------------------
    # Make directories
    # --------------------------------------------------------


    DOWNLOADS.mkdir(
        parents=True,
        exist_ok=True
    )


    STAGING_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    raw_root.mkdir(
        parents=True,
        exist_ok=True
    )


    release_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    provenance_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    docs_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    heading("DIRECTORIES")


    info(
        f"Downloads staging folder:\n"
        f"    {STAGING_DIR}"
    )


    info(
        f"Repository:\n"
        f"    {repo}"
    )


    info(
        f"Local raw release:\n"
        f"    {release_dir}"
    )


    # --------------------------------------------------------
    # Git ignore
    # --------------------------------------------------------


    changed_gitignore = (
        ensure_raw_is_gitignored(repo)
    )


    if changed_gitignore:


        info(
            ".gitignore updated so data/raw/ "
            "cannot be committed accidentally."
        )


    else:


        info(
            "data/raw/ already appears to be Git-ignored."
        )


    # --------------------------------------------------------
    # Copy script to tools/
    # --------------------------------------------------------


    installed_script = (
        install_script_copy(
            script_path,
            repo,
        )
    )


    info(
        f"Audit script copied to:\n"
        f"    {installed_script}"
    )


    # --------------------------------------------------------
    # Process sources
    # --------------------------------------------------------


    records = []


    failed_sources = []


    heading("DOWNLOADING AND AUDITING CURRENT OFFICIAL SOURCES")


    total = len(SOURCES)


    for index, source in enumerate(
        SOURCES,
        start=1
    ):


        print()
        line("-")


        print(
            f"[{index}/{total}] "
            f"{source['description']}"
        )


        staging_file = (
            STAGING_DIR /
            source["filename"]
        )


        status = ""


        content_type = ""


        download_message = ""


        # ----------------------------------------------------
        # Reuse a valid current staging file if already there.
        # ----------------------------------------------------


        if staging_file.exists():


            valid, validation = (
                validate_file(
                    staging_file,
                    source["expected_type"],
                )
            )


            if valid:


                info(
                    "File already exists in Downloads and is valid."
                )


                status = "existing_valid"


            else:


                warning(
                    f"Existing staging file is invalid: {validation}"
                )


                try:
                    staging_file.unlink()
                except Exception:
                    pass


        # ----------------------------------------------------
        # Download if needed.
        # ----------------------------------------------------


        if not staging_file.exists():


            info(
                f"Downloading from:\n"
                f"    {source['direct_url']}"
            )


            ok, message, content_type = (
                download_file(
                    source["direct_url"],
                    staging_file,
                )
            )


            download_message = message


            if ok:
                status = "downloaded"
            else:
                status = "DOWNLOAD_FAILED"


        # ----------------------------------------------------
        # Validate.
        # ----------------------------------------------------


        if staging_file.exists():


            valid, validation = (
                validate_file(
                    staging_file,
                    source["expected_type"],
                )
            )


        else:


            valid = False
            validation = "file was not downloaded"


        # ----------------------------------------------------
        # Failure handling.
        # ----------------------------------------------------


        if not valid:


            warning(
                f"Could not validate source: {validation}"
            )


            failed_sources.append(source)


            records.append({
                "source_id": source["id"],
                "publisher": source["publisher"],
                "description": source["description"],
                "analysis_role": source["analysis_role"],
                "assurance_before_refresh":
                    source["assurance_before_refresh"],
                "filename": source["filename"],
                "direct_url": source["direct_url"],
                "landing_url": source["landing_url"],
                "status": status,
                "download_message": download_message,
                "validation": validation,
                "content_type": content_type,
                "size_bytes": "",
                "size": "",
                "sha256": "",
                "zip_member_count": "",
                "zip_members_preview": "",
                "candidate_header": "",
                "json_record_count": "",
                "json_keys_preview": "",
                "historical_same_name_files": "",
                "historical_hash_match": "",
                "repository_copy": "",
                "retrieved_at_utc": now_utc(),
            })


            continue


        # ----------------------------------------------------
        # Hash and inspect.
        # ----------------------------------------------------


        digest = sha256_file(
            staging_file
        )


        size_bytes = (
            staging_file.stat().st_size
        )


        size_display = (
            human_size(size_bytes)
        )


        zip_info = {
            "member_count": "",
            "member_preview": "",
            "candidate_header": "",
        }


        json_info = {
            "record_count": "",
            "keys_preview": "",
        }


        if source["expected_type"] == "zip":


            zip_info = inspect_zip(
                staging_file
            )


        elif source["expected_type"] == "json":


            json_info = inspect_json(
                staging_file
            )


        # ----------------------------------------------------
        # Compare to historical local copies with same name.
        # ----------------------------------------------------


        previous_files = (
            same_name_historical_files(
                raw_root,
                release_dir,
                source["filename"],
            )
        )


        previous_text = []


        exact_matches = []


        for previous in previous_files:


            try:


                previous_hash = (
                    sha256_file(previous)
                )


                previous_text.append(
                    f"{previous} [{previous_hash}]"
                )


                if previous_hash == digest:


                    exact_matches.append(
                        str(previous)
                    )


            except Exception as exc:


                previous_text.append(
                    f"{previous} [hash error: {exc}]"
                )


        # ----------------------------------------------------
        # Copy current source into dated local raw release.
        # ----------------------------------------------------


        repo_copy, copy_status = (
            copy_to_release(
                staging_file,
                release_dir,
            )
        )


        # ----------------------------------------------------
        # Console summary.
        # ----------------------------------------------------


        info(
            f"Validation: {validation}"
        )


        info(
            f"Size: {size_display}"
        )


        info(
            f"SHA-256:\n"
            f"    {digest}"
        )


        info(
            f"Repository copy:\n"
            f"    {repo_copy}"
        )


        if exact_matches:


            print()
            print(
                "  ***********************************************"
            )


            print(
                "  BYTE-IDENTICAL HISTORICAL LOCAL FILE FOUND"
            )


            print(
                "  ***********************************************"
            )


            for match in exact_matches:
                print(f"    {match}")


        records.append({
            "source_id": source["id"],
            "publisher": source["publisher"],
            "description": source["description"],
            "analysis_role": source["analysis_role"],
            "assurance_before_refresh":
                source["assurance_before_refresh"],
            "filename": source["filename"],
            "direct_url": source["direct_url"],
            "landing_url": source["landing_url"],
            "status": status,
            "download_message": download_message,
            "validation": validation,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "size": size_display,
            "sha256": digest,
            "zip_member_count":
                zip_info.get("member_count", ""),
            "zip_members_preview":
                zip_info.get("member_preview", ""),
            "candidate_header":
                zip_info.get("candidate_header", ""),
            "json_record_count":
                json_info.get("record_count", ""),
            "json_keys_preview":
                json_info.get("keys_preview", ""),
            "historical_same_name_files":
                " ; ".join(previous_text),
            "historical_hash_match":
                " ; ".join(exact_matches),
            "repository_copy": str(repo_copy),
            "retrieved_at_utc": now_utc(),
        })


    # ========================================================
    # WRITE AUDIT OUTPUTS
    # ========================================================


    heading("WRITING PROVENANCE REPORTS")


    csv_inventory = (
        provenance_dir /
        "raw_source_inventory_v6.csv"
    )


    md_inventory = (
        provenance_dir /
        "raw_source_inventory_v6.md"
    )


    docs_md = (
        docs_dir /
        f"DATA_PROVENANCE_REFRESH_{TODAY}.md"
    )


    docs_csv = (
        docs_dir /
        f"data_provenance_manifest_refresh_{TODAY}.csv"
    )


    write_csv_report(
        records,
        csv_inventory,
    )


    write_csv_report(
        records,
        docs_csv,
    )


    write_md_report(
        records,
        md_inventory,
        repo,
        release_dir,
    )


    write_md_report(
        records,
        docs_md,
        repo,
        release_dir,
    )


    # --------------------------------------------------------
    # Write easy-to-read file in Downloads too.
    # --------------------------------------------------------


    downloads_summary = (
        STAGING_DIR /
        "READ_ME_FIRST.txt"
    )


    with downloads_summary.open(
        "w",
        encoding="utf-8"
    ) as f:


        f.write(
            "Walsh QM640 Capstone - Current Raw Source Refresh\n"
        )


        f.write(
            "=" * 60 + "\n\n"
        )


        f.write(
            f"Generated: {now_utc()}\n\n"
        )


        f.write(
            f"Repository:\n{repo}\n\n"
        )


        f.write(
            f"Current downloads:\n{STAGING_DIR}\n\n"
        )


        f.write(
            f"Local repository raw release:\n{release_dir}\n\n"
        )


        f.write(
            "IMPORTANT:\n"
            "These are current official source downloads. "
            "They are not automatically the byte-identical "
            "historical files used to build the dissertation's "
            "frozen merged dataset.\n\n"
        )


        for record in records:


            f.write(
                f"{record['source_id']}\n"
            )


            f.write(
                f"Status: {record['status']}\n"
            )


            f.write(
                f"SHA-256: {record.get('sha256', '')}\n"
            )


            f.write(
                f"URL: {record['direct_url']}\n\n"
            )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================


    heading("FINISHED")


    print(
        "\nYour CURRENT downloaded source files are here:\n"
    )


    print(
        f"  {STAGING_DIR}\n"
    )


    print(
        "Verified copies were placed in the LOCAL repository here:\n"
    )


    print(
        f"  {release_dir}\n"
    )


    print(
        "Provenance audit files were created here:\n"
    )


    print(
        f"  {csv_inventory}\n"
        f"  {md_inventory}\n"
        f"  {docs_md}\n"
        f"  {docs_csv}\n"
    )


    print(
        "The reusable audit script is now also in:\n"
    )


    print(
        f"  {installed_script}\n"
    )


    print(
        "The frozen merged dataset was NOT changed."
    )


    print(
        "final_pipeline.py was NOT executed."
    )


    print(
        "Nothing was committed or pushed to GitHub."
    )


    # ========================================================
    # MANUAL DOWNLOAD FALLBACK
    # ========================================================


    if failed_sources:


        print()


        line("!")


        print(
            f"{len(failed_sources)} source(s) could not be "
            "downloaded automatically."
        )


        print(
            "\nThis is often caused by Anatel's automated-request "
            "security filter."
        )


        manual_file = (
            STAGING_DIR /
            "MANUAL_DOWNLOADS_REQUIRED.txt"
        )


        with manual_file.open(
            "w",
            encoding="utf-8"
        ) as f:


            f.write(
                "MANUAL DOWNLOADS REQUIRED\n"
            )


            f.write(
                "=" * 50 + "\n\n"
            )


            f.write(
                "Save each manually downloaded file into:\n"
            )


            f.write(
                f"{STAGING_DIR}\n\n"
            )


            for source in failed_sources:


                f.write(
                    f"{source['description']}\n"
                )


                f.write(
                    f"Expected filename: "
                    f"{source['filename']}\n"
                )


                f.write(
                    f"Direct URL: "
                    f"{source['direct_url']}\n"
                )


                f.write(
                    f"Official landing page: "
                    f"{source['landing_url']}\n\n"
                )


        print(
            "\nInstructions were written to:\n"
        )


        print(
            f"  {manual_file}\n"
        )


        answer = input(
            "Would you like me to open the official pages "
            "for the failed downloads in your browser now? "
            "(Y/N): "
        ).strip().lower()


        if answer in ("y", "yes"):


            for source in failed_sources:


                try:
                    webbrowser.open(
                        source["landing_url"]
                    )


                    time.sleep(1)


                except Exception:
                    pass


        print(
            "\nAfter manually saving the missing files into the "
            "Downloads refresh folder, simply run this same script "
            "again. Existing valid downloads will be reused."
        )


    print()
    line("=")


    print(
        "SAFE TO CLOSE."
    )


    line("=")


    # Keep the window visible for people who double-clicked it.
    try:
        input(
            "\nPress ENTER to close this window..."
        )
    except EOFError:
        pass




# ============================================================
# ENTRY POINT
# ============================================================


if __name__ == "__main__":


    try:
        main()


    except KeyboardInterrupt:


        print(
            "\n\nStopped by user. No historical files were deleted."
        )


    except Exception as exc:


        print()
        line("!")


        print(
            "AN UNEXPECTED ERROR OCCURRED"
        )


        line("!")


        print(
            f"\n{type(exc).__name__}: {exc}\n"
        )


        print(
            "Your frozen merged dataset was not intentionally "
            "modified by this script."
        )


        try:
            input(
                "\nPress ENTER to close..."
            )
        except EOFError:
            pass