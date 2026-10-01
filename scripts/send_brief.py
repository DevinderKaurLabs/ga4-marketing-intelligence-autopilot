"""Email a rendered brief.

  python scripts/send_brief.py --to you@example.com                # latest week, MODEL_PRIMARY
  python scripts/send_brief.py --to you@example.com --week 2020-12-21
"""
import argparse
import os

from _common import ARTIFACTS, slug

from mia.emailer import send


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True)
    ap.add_argument("--model", default=os.getenv("MODEL_PRIMARY"))
    ap.add_argument("--week", default="latest")
    args = ap.parse_args()
    folder = ARTIFACTS / "reports" / slug(args.model)
    briefs = sorted(folder.glob("brief_*.html"))
    if not briefs:
        raise SystemExit(f"No briefs in {folder}. Run generate_briefs.py first.")
    html = briefs[-1] if args.week == "latest" else folder / f"brief_{args.week}.html"
    week = html.stem.replace("brief_", "")
    send(args.to, f"Marketing brief: week of {week}", html, html.with_suffix(".pdf"))
    print(f"Sent brief for week of {week} to {args.to}")


if __name__ == "__main__":
    main()
