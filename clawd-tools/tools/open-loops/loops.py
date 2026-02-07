import argparse
import os
import sqlite3
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "open_loops.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS open_loops (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'open',
              due_date TEXT,
              created_at TEXT NOT NULL,
              closed_at TEXT,
              source TEXT,
              tags TEXT,
              note TEXT
            )
            """
        )
        conn.commit()


def add_loop(title: str, due: str | None, source: str | None, tags: str | None):
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO open_loops (title, due_date, created_at, source, tags) VALUES (?, ?, ?, ?, ?)",
            (title, due, now, source, tags),
        )
        conn.commit()
        return cur.lastrowid


def list_loops(status: str | None):
    with _conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT id, status, due_date, title FROM open_loops WHERE status=? ORDER BY COALESCE(due_date, '9999-12-31'), id DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, status, due_date, title FROM open_loops ORDER BY status ASC, COALESCE(due_date, '9999-12-31'), id DESC"
            ).fetchall()
    return rows


def due_loops():
    today = date.today().isoformat()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT id, status, due_date, title
            FROM open_loops
            WHERE status='open' AND due_date IS NOT NULL AND due_date <= ?
            ORDER BY due_date ASC, id DESC
            """,
            (today,),
        ).fetchall()
    return rows


def view_loop(loop_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, title, status, due_date, created_at, closed_at, source, tags, note FROM open_loops WHERE id=?",
            (loop_id,),
        ).fetchone()
    return row


def close_loop(loop_id: int, note: str | None):
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as conn:
        conn.execute(
            "UPDATE open_loops SET status='closed', closed_at=?, note=COALESCE(?, note) WHERE id=?",
            (now, note, loop_id),
        )
        conn.commit()


def reopen_loop(loop_id: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE open_loops SET status='open', closed_at=NULL WHERE id=?",
            (loop_id,),
        )
        conn.commit()


def main():
    ap = argparse.ArgumentParser(description="Track open loops (commitments)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    ap_add = sub.add_parser("add")
    ap_add.add_argument("title")
    ap_add.add_argument("--due", help="YYYY-MM-DD")
    ap_add.add_argument("--source", help="Where this came from (chat, email, etc.)")
    ap_add.add_argument("--tags", help="Comma-separated")

    ap_list = sub.add_parser("list")
    ap_list.add_argument("--status", choices=["open", "closed"])

    sub.add_parser("due")

    ap_view = sub.add_parser("view")
    ap_view.add_argument("id", type=int)

    ap_close = sub.add_parser("close")
    ap_close.add_argument("id", type=int)
    ap_close.add_argument("--note")

    ap_reopen = sub.add_parser("reopen")
    ap_reopen.add_argument("id", type=int)

    args = ap.parse_args()

    if args.cmd == "init":
        init_db()
        print(f"[OK] Initialized {DB_PATH}")
        return

    init_db()

    if args.cmd == "add":
        loop_id = add_loop(args.title, args.due, args.source, args.tags)
        print(f"[OK] Added open loop #{loop_id}: {args.title}")
        return

    if args.cmd == "list":
        rows = list_loops(args.status)
        if not rows:
            print("No loops.")
            return
        for (i, status, due, title) in rows:
            due_s = due or "-"
            print(f"#{i}\t{status}\t{due_s}\t{title}")
        return

    if args.cmd == "due":
        rows = due_loops()
        if not rows:
            print("No due open loops.")
            return
        print("[DUE] Open Loops")
        for (i, status, due, title) in rows:
            print(f"#{i}\t{due}\t{title}")
        return

    if args.cmd == "view":
        row = view_loop(args.id)
        if not row:
            print("Not found")
            return
        keys = [
            "id",
            "title",
            "status",
            "due_date",
            "created_at",
            "closed_at",
            "source",
            "tags",
            "note",
        ]
        for k, v in zip(keys, row):
            print(f"{k}: {v}")
        return

    if args.cmd == "close":
        close_loop(args.id, args.note)
        print(f"[OK] Closed loop #{args.id}")
        return

    if args.cmd == "reopen":
        reopen_loop(args.id)
        print(f"[OK] Reopened loop #{args.id}")
        return


if __name__ == "__main__":
    main()
