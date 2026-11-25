import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "resumes.json"
DB_FILE = BASE / "data" / "recruit.db"

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS candidates (
        name TEXT PRIMARY KEY,
        degree TEXT,
        years INTEGER,
        address TEXT,
        applied_at TEXT
    )
    """
)
cur.execute("DELETE FROM candidates")

resumes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
rows = [
    (r["name"], r["degree"], r["years"], r["address"], r["applied_at"])
    for r in resumes
]
cur.executemany("INSERT INTO candidates VALUES (?, ?, ?, ?, ?)", rows)
conn.commit()

cur.execute(
    "SELECT name, degree, years FROM candidates WHERE address = ? AND years >= ?",
    ("上海", 2),
)
for row in cur.fetchall():
    print(row)

conn.close()
print(f"已写入 {DB_FILE}，共 {len(rows)} 条")
