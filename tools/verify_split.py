"""CI check for the offline simulator and the UiPath project files.

1. Every .xaml file in the repository parses as well-formed XML.
2. tools/simulate_split.py, run on samples/input into a temporary folder, produces exactly the
   files in samples/expected-output (same names, same page counts) and writes a manifest.
3. Running the simulator a second time skips the report because its SHA-256 is already in the
   manifest, and creates no new files.

Usage:
    pip install -r tools/requirements.txt
    python tools/verify_split.py
"""
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SIMULATOR = ROOT / "tools" / "simulate_split.py"
INPUT_DIR = ROOT / "samples" / "input"
EXPECTED_DIR = ROOT / "samples" / "expected-output"
SKIP_DIRS = {".git", ".local", ".venv", "node_modules"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def check_xaml() -> None:
    files = [p for p in ROOT.rglob("*.xaml") if not SKIP_DIRS & set(p.relative_to(ROOT).parts)]
    if not files:
        fail("no .xaml files found")
    for path in sorted(files):
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            fail(f"{path.relative_to(ROOT)} is not well-formed XML: {exc}")
    print(f"OK: {len(files)} .xaml files parse as XML")


def page_counts(folder: Path) -> dict[str, int]:
    return {p.name: len(PdfReader(str(p)).pages) for p in sorted(folder.glob("*.pdf"))}


def pdf_files(root: Path) -> set[Path]:
    return {p.relative_to(root) for p in root.rglob("*.pdf")}


def run_simulator(pdf: Path, out: Path) -> str:
    result = subprocess.run([sys.executable, str(SIMULATOR), str(pdf), "--out", str(out)],
                            capture_output=True, text=True)
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, end="")
        fail(f"simulator exited with code {result.returncode} for {pdf.name}")
    return result.stdout


def check_split() -> None:
    inputs = sorted(INPUT_DIR.glob("*.pdf"))
    if not inputs:
        fail("no sample PDFs in samples/input")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        for pdf in inputs:
            run_simulator(pdf, out)

        expected_folders = sorted(p for p in EXPECTED_DIR.iterdir() if p.is_dir())
        produced_folders = sorted(p.name for p in out.iterdir() if p.is_dir() and p.name != "_Automation")
        if produced_folders != [p.name for p in expected_folders]:
            fail(f"output folders {produced_folders} != expected {[p.name for p in expected_folders]}")
        for exp in expected_folders:
            want, got = page_counts(exp), page_counts(out / exp.name)
            if want != got:
                fail(f"{exp.name}: produced {got}\n      expected {want}")
            print(f"OK: {exp.name} has the {len(want)} expected files with matching page counts")

        manifest = out / "_Automation" / "State" / "ProcessedSourceManifest.csv"
        if not manifest.exists():
            fail("manifest was not written")
        rows = manifest.read_text(encoding="utf-8").strip().splitlines()
        if len(rows) != len(inputs) + 1:
            fail(f"manifest has {len(rows) - 1} rows, expected {len(inputs)}")

        before = pdf_files(out)
        for pdf in inputs:
            stdout = run_simulator(pdf, out)
            if "Skipping already-processed source PDF" not in stdout:
                fail(f"re-run did not skip {pdf.name} by manifest hash")
        if pdf_files(out) != before:
            fail("re-run created or removed files")
        if manifest.read_text(encoding="utf-8").strip().splitlines() != rows:
            fail("re-run changed the manifest")
        print("OK: re-run skipped every report by manifest hash and changed nothing")


if __name__ == "__main__":
    check_xaml()
    check_split()
    print("All checks passed.")
