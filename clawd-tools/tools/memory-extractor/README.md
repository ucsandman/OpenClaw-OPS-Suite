# Memory Extractor (Glue Tool)

Turns a chunk of text (chat, notes) into structured outputs that plug into the tools we already have.

## Goal
Avoid rebuilding separate systems. This tool produces *draft updates* for:
- daily memory file (`memory/YYYY-MM-DD.md`)
- suggested `MEMORY.md` additions
- optional open loops

## Usage

```bash
cd tools/memory-extractor
python extract.py --input memory\\2026-02-05.md --date 2026-02-05

# Or paste from clipboard / file:
python extract.py --input some_notes.txt
```

For now this is a **template generator** (safe, deterministic). Next step can add an LLM-backed extractor if you want.
