"""Turn already-generated HTML briefs into PDFs. No model calls, no cost.

  python scripts/render_pdfs.py --model gemini-flash-latest
"""
import argparse

from _common import ARTIFACTS, slug


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    args = ap.parse_args()
    from weasyprint import HTML

    folder = ARTIFACTS / "reports" / slug(args.model)
    files = sorted(folder.glob("brief_*.html"))
    for f in files:
        HTML(filename=str(f)).write_pdf(str(f.with_suffix(".pdf")))
    print(f"{len(files)} PDFs written to {folder.relative_to(ARTIFACTS.parent)}")


if __name__ == "__main__":
    main()
