import sqlite3
import os

databases = [
    'tools/learning-database/data/learning.db',
    'tools/inspiration/data/ideas.db',
    'tools/goal-tracker/data/goals.db',
    'tools/relationship-tracker/relationships.db',
    'tools/workflow-orchestrator/data/workflows.db',
]

for db_path in databases:
    if os.path.exists(db_path):
        print(f"\n=== {db_path} ===")
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
        for name, sql in cursor.fetchall():
            print(f"\n{sql}")
        conn.close()
    else:
        print(f"\n=== {db_path} === NOT FOUND")
