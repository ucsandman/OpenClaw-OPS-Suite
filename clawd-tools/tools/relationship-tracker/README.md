# Relationship Tracker

MoltFire's mini-CRM for tracking contacts and follow-ups across platforms.

## Quick Start

```bash
cd tools/relationship-tracker

# Add a contact
python tracker.py add "Name" --platform moltbook --handle "@user" -t hot -o "bounty_collab" -n "Notes here"

# List all contacts
python tracker.py list
python tracker.py list --hot          # Hot leads only
python tracker.py list --platform moltbook

# View contact details
python tracker.py view 1

# Log an interaction
python tracker.py log 1 -t reply -d outbound -s "Discussed bounty strategies"

# Set follow-up
python tracker.py followup 1 --date 2026-02-10
python tracker.py followup 1 --date +3          # 3 days from now
python tracker.py followup 1 --date tomorrow

# Update temperature
python tracker.py temp 1 hot

# See due follow-ups
python tracker.py due

# Search
python tracker.py search "algora"

# Update notes
python tracker.py notes 1 "Updated notes here"
```

## Schema

**Contacts:**
- name, platform, handle, platform_id
- temperature (hot/warm/cold)
- status (active/nurturing/dormant/closed)
- first_contact, last_contact, next_followup
- opportunity_type, opportunity_value
- notes, tags

**Interactions:**
- contact_id, date, type, direction
- platform, platform_ref
- summary, sentiment

## Workflow Integration

Check due follow-ups during heartbeats:
```bash
python tracker.py due
```

After any Moltbook engagement, log it:
```bash
python tracker.py log <id> -t comment -d outbound -s "What happened"
```

---

*Built 2026-02-03*
