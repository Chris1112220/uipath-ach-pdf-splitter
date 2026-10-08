"""Generate a FICTIONAL combined ACH payment-notification PDF for demos and testing.

Every company name, identifier, account and amount below is made up. The layout only
mimics the labels the bot keys on (ORIGINATOR INFORMATION / Company Name / Identification /
Amount / END OF TRANSACTION); it is not a copy of any real bank's report.

Usage:
    pip install reportlab
    python tools/generate_sample_report.py            # writes samples/input/ACH_Remittance_Report 20260831.pdf
"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

REPORT_DATE = "20260831"
OUT = Path(__file__).resolve().parents[1] / "samples" / "input" / f"ACH_Remittance_Report {REPORT_DATE}.pdf"

# (originator, originator id, amount, number of remittance addenda lines)
TRANSACTIONS = [
    ("Northwind Traders", "9000000001", "$1,250.00", 2),
    ("Contoso Medical Supply", "9000000002", "$18,420.75", 6),
    ("Fabrikam Facilities Services", "9000000003", "$7,305.10", 70),  # long addenda -> spans 2 pages
    ("Adventure Works / Cycles", "9000000004", "$640.00", 1),        # '/' is illegal in filenames
    ("Tailspin Toys Foundation", "9000000005", "$25,000.00", 3),
]

LINE = 13
TOP = 750
BOTTOM = 60


def header(c: canvas.Canvas, page_no: int) -> float:
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, TOP, "SAMPLE BANK, N.A. (FICTIONAL)  -  ACH PAYMENT NOTIFICATION REPORT")
    c.setFont("Helvetica", 9)
    c.drawString(50, TOP - LINE, f"Report Date: 08/31/2026        Page {page_no}        FOR DEMONSTRATION ONLY - NOT REAL DATA")
    return TOP - 3 * LINE


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=letter, invariant=1)  # reproducible bytes -> stable SHA-256
    c.setTitle("Fictional ACH payment notification report")
    c.setAuthor("uipath-ach-pdf-splitter sample generator")
    page_no = 1

    for seq, (company, ident, amount, addenda) in enumerate(TRANSACTIONS, start=1):
        y = header(c, page_no)
        body = [
            ("B", "ORIGINATOR INFORMATION"),
            ("", f"Company Name: {company}"),
            ("", f"Identification: {ident}"),
            ("", "Entry Description: PAYMENT"),
            ("B", "RECEIVER INFORMATION"),
            ("", "Receiver Name: EXAMPLE ORGANIZATION (FICTIONAL)"),
            ("", "Account Number: XXXXXX0000"),
            ("B", "PAYMENT INFORMATION"),
            ("", f"Amount: {amount} CR"),
            ("", "Effective Date: 08/31/2026"),
            ("", f"Trace Number: 0000000000{seq:05d}"),
            ("B", "REMITTANCE DETAIL"),
        ]
        for i in range(1, addenda + 1):
            body.append(("", f"RMR*IV*INV-{seq}{i:04d}*{100 + i}.00\\"))
        body.append(("B", "END OF TRANSACTION"))

        for style, text in body:
            if y < BOTTOM:  # transaction continues on the next page
                c.showPage()
                page_no += 1
                y = header(c, page_no)
                c.setFont("Helvetica-Oblique", 9)
                c.drawString(50, y, f"(continued - transaction {seq})")
                y -= 2 * LINE
            c.setFont("Helvetica-Bold" if style == "B" else "Helvetica", 10)
            c.drawString(50, y, text)
            y -= LINE

        c.showPage()  # every transaction starts on a new page
        page_no += 1

    c.save()
    print(f"Wrote {OUT} ({page_no - 1} pages, {len(TRANSACTIONS)} transactions)")


if __name__ == "__main__":
    main()
