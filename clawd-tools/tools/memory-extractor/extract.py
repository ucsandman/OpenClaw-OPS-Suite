import argparse
import datetime as dt
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEM_DIR = ROOT / "memory"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_append(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description="Generate structured memory drafts")
    ap.add_argument("--input", required=True, help="Path to a text/markdown file")
    ap.add_argument("--date", help="YYYY-MM-DD (defaults today)")
    ap.add_argument(
        "--append-daily",
        action="store_true",
        help="Append a structured section to memory/YYYY-MM-DD.md",
    )
    ap.add_argument(
        "--out",
        help="Write draft to a file instead of stdout",
    )

    args = ap.parse_args()

    d = args.date or dt.date.today().isoformat()
    in_path = Path(args.input).expanduser().resolve()
    text = load_text(in_path)

    draft = f"""
## Memory Extractor Draft ({d})

### Facts to Remember
- 

### Decisions Made
- 

### Open Loops / Commitments
- 

### Preferences / Style
- 

### Risks / Security Notes
- 

### Where this came from
- Source file: {in_path}
- Characters: {len(text)}

""".lstrip()

    if args.append_daily:
        daily_path = MEM_DIR / f"{d}.md"
        write_append(daily_path, "\n" + draft)
        print(f"[OK] Appended draft to {daily_path}")
        return

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.write_text(draft, encoding="utf-8")
        print(f"[OK] Wrote draft to {out_path}")
        return

    print(draft)


if __name__ == "__main__":
    main()
