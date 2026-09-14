#!/usr/bin/env python3
"""
verify_links.py — Appendix B source-link verifier for the Walsh MSc Capstone.

Reads docs/data_provenance_manifest_v6.csv (or the copy next to this script),
issues an HTTP request to every official landing page and every fully-qualified
direct resource URL, and writes docs/link_check_log.csv with:
    url, http_status, content_type, content_length, checked_at_utc

Direct ZIP endpoints are checked with a ranged/streamed GET (first bytes only),
so nothing large is downloaded. Run this before each dated re-acquisition and
commit the log, satisfying the "verification gate" column of the manifest.

Usage:
    python verify_links.py
"""
import csv
import datetime
import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
CANDIDATES = [
    HERE / "docs" / "data_provenance_manifest_v6.csv",
    HERE / "data_provenance_manifest_v6.csv",
]
OUT = HERE / ("docs/link_check_log.csv" if (HERE / "docs").is_dir() else "link_check_log.csv")

HEADERS = {"User-Agent": "Mozilla/5.0 (capstone-link-check)"}


def check(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=0-1023"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {
                "url": url,
                "http_status": resp.status,
                "content_type": resp.headers.get("Content-Type", ""),
                "content_length": resp.headers.get("Content-Length", ""),
                "error": "",
            }
    except Exception as exc:  # noqa: BLE001 — record every failure mode
        return {"url": url, "http_status": "", "content_type": "",
                "content_length": "", "error": repr(exc)}


def main() -> int:
    manifest = next((p for p in CANDIDATES if p.exists()), None)
    if manifest is None:
        print("ERROR: data_provenance_manifest_v6.csv not found.", file=sys.stderr)
        return 1

    urls: list[str] = []
    with open(manifest, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for col in ("official_landing_page", "current_direct_resource_or_table_id"):
                val = (row.get(col) or "").strip()
                # Only fully-qualified URLs; bare filenames (e.g. meu_municipio.zip)
                # are resource *candidates*, flagged in the manifest limitations.
                for part in val.replace(";", " ").split():
                    if part.startswith("http") and part not in urls:
                        urls.append(part)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    results = []
    for url in urls:
        r = check(url)
        r["checked_at_utc"] = now
        status = r["http_status"] or f"FAIL ({r['error'][:60]})"
        print(f"[{status}] {url}")
        results.append(r)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["url", "http_status", "content_type",
                                                "content_length", "error", "checked_at_utc"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nWrote {OUT} ({len(results)} URLs).")

    failures = [r for r in results if str(r["http_status"]) not in ("200", "206")]
    if failures:
        print(f"WARNING: {len(failures)} URL(s) did not return 200/206 — "
              "update the manifest or record the change in Appendix B.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
