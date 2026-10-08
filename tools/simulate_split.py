"""Offline Python port of PDF/ProcessSourcePdf.xaml + the manifest/idempotency logic in Main.xaml.

It lets you check the parsing rules against a PDF without UiPath Studio. It mirrors the
workflow: read page by page, buffer pages until "END OF TRANSACTION", parse the originator
Company Name and Amount with the same regular expressions, sanitize the name for Windows,
and extract the page range to "{Index:000} - {Company} - {Amount}.pdf" in a yyyy-MM-dd folder.
Text extraction uses pypdf, so whitespace can differ slightly from UiPath's Read PDF Text.

Usage:
    pip install pypdf
    python tools/simulate_split.py "samples/input/ACH_Remittance_Report 20260831.pdf" --out samples/output
    (run it twice: the second run skips the report because its SHA-256 is already in the manifest)
"""
import argparse
import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter

COMPANY_RE = re.compile(
    r"ORIGINATOR INFORMATION.*?Company Name\s*:\s*(.+?)(?=(?:\s+Company Name\s*:\s*|\s+Identification\s*:))",
    re.I | re.M | re.S,
)
AMOUNT_RE = re.compile(r"^\s*Amount\s*:\s*(\$[\d,]+\.\d{2})\s*(?:CR|DB|DR)?", re.I | re.M)
AMOUNT_FALLBACK_RE = re.compile(r"Amount\s*:\s*(\$[\d,]+\.\d{2})")
END_MARKER = "END OF TRANSACTION"
INVALID_FILENAME_CHARS = set('"<>|:*?\\/') | {chr(i) for i in range(32)}
NAME_FORMAT = "{Index:000} - {Company} - {Amount}.pdf"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def report_date(path: Path) -> datetime:
    m = re.search(r"(?<!\d)(\d{8})(?!\d)", path.stem)
    if not m:
        raise ValueError(f"Unable to determine the report date from source filename: {path.stem}")
    return datetime.strptime(m.group(1), "%Y%m%d")


def parse(text: str, start: int, end: int) -> tuple[str, str]:
    cm = COMPANY_RE.search(text)
    if not cm:
        raise ValueError(f"Unable to parse originator Company Name from transaction pages {start}-{end}.")
    am = AMOUNT_RE.search(text) or AMOUNT_FALLBACK_RE.search(text)
    if not am:
        raise ValueError(f"Unable to parse Amount from transaction pages {start}-{end}.")
    company = re.sub(r"\s+", " ", cm.group(1)).strip()
    company = "".join(" " if ch in INVALID_FILENAME_CHARS else ch for ch in company)
    company = re.sub(r"\s+", " ", company).strip().strip(".") or "Unknown Company"
    return company[:80].strip(), am.group(1).strip()


def split(pdf: Path, out_root: Path) -> list[str]:
    folder = out_root / report_date(pdf).strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(pdf))
    created, buffer, start, index = [], "", 1, 1
    for page_no in range(1, len(reader.pages) + 1):
        if not buffer.strip():
            start = page_no
        buffer += "\n" + (reader.pages[page_no - 1].extract_text() or "")
        if END_MARKER in buffer:
            company, amount = parse(buffer, start, page_no)
            name = (NAME_FORMAT.replace("{Index:000}", f"{index:03d}")
                    .replace("{Company}", company).replace("{Amount}", amount))
            writer = PdfWriter()
            for p in range(start, page_no + 1):
                writer.add_page(reader.pages[p - 1])
            with open(folder / name, "wb") as fh:
                writer.write(fh)
            pages = str(start) if start == page_no else f"{start}-{page_no}"
            created.append(f"{name}  (pages {pages})")
            buffer, index = "", index + 1
    if buffer.strip():
        raise ValueError(f"The PDF ended with an incomplete transaction starting at page {start}.")
    if not created:
        raise ValueError(f"No transactions were created from {pdf.name}.")
    return created


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", type=Path, default=Path("samples/output"))
    args = ap.parse_args()

    manifest = args.out / "_Automation" / "State" / "ProcessedSourceManifest.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    known = set()
    if manifest.exists():
        with open(manifest, newline="", encoding="utf-8") as fh:
            known = {r["FileHash"].upper() for r in csv.DictReader(fh) if r["Status"].lower() == "success"}

    digest = sha256(args.pdf)
    print(f"SHA256 {digest}")
    if digest in known:
        print(f"Skipping already-processed source PDF: {args.pdf.name}")
        return

    created = split(args.pdf, args.out)
    for line in created:
        print("  created", line)

    new_file = not manifest.exists() or manifest.stat().st_size == 0
    with open(manifest, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        if new_file:
            fh.write("FileHash,SourceFileName,ReportDate,ProcessedDateTime,TransactionCount,Status\n")
        w.writerow([digest, args.pdf.name, report_date(args.pdf).strftime("%Y-%m-%d"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(created), "Success"])
    print(f"Processed {args.pdf.name}. Created {len(created)} transaction PDF(s).")


if __name__ == "__main__":
    main()
