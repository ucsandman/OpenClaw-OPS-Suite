# Open Loops Tracker

Track commitments we made ("we said we'd do X") so nothing falls through the cracks.

## Commands

```bash
cd tools/open-loops
python loops.py init
python loops.py add "Follow up with Elliot about lunch agenda" --due 2026-02-06
python loops.py list
python loops.py due
python loops.py close 3 --note "Done"
python loops.py view 3
```

## Why this exists
We already have: daily logs, context capture, and task lists. This tool is specifically for **commitments made in conversation** — open loops that are easy to forget.

## Data
SQLite DB at `tools/open-loops/data/open_loops.db` (gitignored).
