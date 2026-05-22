#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract AoS core rule PDFs to structured markdown files.
Idempotent: skips extraction if output .md already exists and is newer than PDF.
"""
import os
import sys
import io
import re
import json

# Force stdout/stderr to UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import pdfplumber
except ImportError:
    print("pdfplumber not found. Installing...")
    os.system(f"{sys.executable} -m pip install pdfplumber")
    import pdfplumber

DOWNLOADS = r"C:/Users/eep0x10/Downloads"
OUT_DIR = r"C:/Users/eep0x10/dev/waaahgame/scripts/cache/aos_rules_extract"

PDFS = {
    "core_rules": "eng_aos_core&key_the-rules_apr25-t7q3fbv0zb-bit50crc5k.pdf",
    "updates": "eng_29-04_aos_core&key_rules_updates-egx3vrebci-dh2agxidop.pdf",
    "battle_profiles": "eng_01-04_aos_core_rules_battle_profiles-exhcxlmuav-apakzbu4ms.pdf",
    "ghb": "eng_jun25_aos_tournament_organizer_pack-z339pkvuty-9ktwetzvfg.pdf",
}

# Known repeated header/footer patterns to strip
NOISE_PATTERNS = [
    r"^WARHAMMER AGE OF SIGMAR\s*$",
    r"^Age of Sigmar\s*$",
    r"^\d+\s*$",           # standalone page numbers
    r"^©\s*Games Workshop.*$",
    r"^TM\s*$",
    r"^\s*$",              # blank lines (collapsed later)
    r"^CORE RULES\s*$",
    r"^THE RULES\s*$",
    r"^RULES UPDATE\s*$",
    r"^TOURNAMENT ORGANIZER PACK\s*$",
    r"^GHB\s*\d{4}",
    r"^BATTLE PROFILES\s*$",
    r"^warhammer-community\.com\s*$",
]

NOISE_RE = re.compile("|".join(f"(?:{p})" for p in NOISE_PATTERNS), re.IGNORECASE)


def clean_line(line: str) -> str | None:
    stripped = line.strip()
    if NOISE_RE.fullmatch(stripped):
        return None
    return stripped


def extract_pdf(pdf_path: str, out_path: str):
    print(f"  Extracting: {os.path.basename(pdf_path)} → {os.path.basename(out_path)}")
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            if i % 20 == 0:
                print(f"    Page {i+1}/{total}...")
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if not text:
                continue
            lines.append(f"\n---\n<!-- page {i+1} -->\n")
            prev_blank = False
            for raw_line in text.split("\n"):
                cleaned = clean_line(raw_line)
                if cleaned is None:
                    continue
                if cleaned == "":
                    if not prev_blank:
                        lines.append("")
                    prev_blank = True
                else:
                    prev_blank = False
                    lines.append(cleaned)

    content = "\n".join(lines)
    # Collapse 3+ consecutive blank lines to 2
    content = re.sub(r"\n{3,}", "\n\n", content)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# {os.path.basename(pdf_path)}\n\n")
        f.write(f"Extracted {total} pages.\n\n")
        f.write(content)

    print(f"    Done. {len(content)} chars written.")
    return len(content)


def should_skip(pdf_path: str, out_path: str) -> bool:
    if not os.path.exists(out_path):
        return False
    return os.path.getmtime(out_path) >= os.path.getmtime(pdf_path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    results = {}

    for key, filename in PDFS.items():
        pdf_path = os.path.join(DOWNLOADS, filename)
        out_path = os.path.join(OUT_DIR, f"{key}.md")

        if not os.path.exists(pdf_path):
            print(f"[SKIP] PDF not found: {pdf_path}")
            results[key] = {"status": "not_found", "path": pdf_path}
            continue

        if should_skip(pdf_path, out_path):
            print(f"[SKIP] {key}.md is up to date.")
            results[key] = {"status": "skipped", "out": out_path}
            continue

        try:
            chars = extract_pdf(pdf_path, out_path)
            results[key] = {"status": "ok", "chars": chars, "out": out_path}
        except Exception as e:
            print(f"[ERROR] {key}: {e}")
            results[key] = {"status": "error", "error": str(e)}

    # Write summary
    summary_path = os.path.join(OUT_DIR, "_summary.json")
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\nSummary:")
    for k, v in results.items():
        print(f"  {k}: {v['status']}")


if __name__ == "__main__":
    main()
