import os
import sqlite3
import json
import logging

from config import DB_FILE, FILES_OFFSETS_PATH
from log_parser import read_logs_from_files

logger = logging.getLogger(__name__)


def init_db():
    newly_created = False
    if not os.path.exists(DB_FILE):
        logger.info("Initializing new database.")
        newly_created = True
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    query TEXT,
                    response TEXT,
                    tool TEXT,
                    tester TEXT,
                    is_independent_question TEXT DEFAULT '',
                    response_review TEXT DEFAULT '',
                    query_review TEXT DEFAULT '',
                    urls_review TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    last_updated_by TEXT DEFAULT NULL,
                    last_updated_at TEXT DEFAULT NULL
                )
            ''')
            conn.commit()
    else:
        logger.info("Database already exists.")

    if newly_created:
        logs = read_logs_from_files()
        with sqlite3.connect(DB_FILE) as conn:
            for log in logs:
                insert_log(conn, log)


def ensure_notes_column():
    """Add notes column if the DB existed before notes was introduced."""
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(logs)")
        cols = [row[1] for row in cur.fetchall()]
        if "notes" not in cols:
            cur.execute("ALTER TABLE logs ADD COLUMN notes TEXT DEFAULT ''")
            conn.commit()
            logger.info("Added notes column to logs table.")


def load_offsets():
    if FILES_OFFSETS_PATH and os.path.exists(FILES_OFFSETS_PATH):
        with open(FILES_OFFSETS_PATH, 'r') as f:
            return json.load(f)
    return {}


def save_offsets(positions):
    with open(FILES_OFFSETS_PATH, 'w') as f:
        json.dump(positions, f)


def insert_log(conn, log):
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM logs WHERE timestamp=? AND query=?",
        (log['timestamp'], log['query'])
    )
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO logs (
                timestamp, query, response, tool, tester,
                is_independent_question, response_review,
                query_review, urls_review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            log['timestamp'],
            log['query'],
            log['response'],
            log['tool'],
            log['tester'],
            log['is_independent_question'],
            log['response_review'],
            log['query_review'],
            log['urls_review']
        ))
        conn.commit()
        logger.info(f"Inserted log with timestamp: {log['timestamp']}")
    else:
        logger.info(f"Log already exists for timestamp: {log['timestamp']}")


def get_logs(start_date, end_date, tool='All', independent='All',
             response_reviews=None, query_reviews=None, urls_reviews=None,
             review_status='All'):
    """Build and run the filtered log query. Returns a list of dicts."""
    sql = "SELECT * FROM logs WHERE timestamp BETWEEN ? AND ?"
    params = [f"{start_date} 00:00:00,000", f"{end_date} 23:59:59,999"]

    if tool != 'All':
        sql += " AND tool=?"
        params.append(tool)
    if independent != 'All':
        sql += " AND is_independent_question=?"
        params.append(independent)
    if response_reviews:
        sql += " AND response_review IN ({})".format(','.join('?' for _ in response_reviews))
        params.extend(response_reviews)
    if query_reviews:
        sql += " AND query_review IN ({})".format(','.join('?' for _ in query_reviews))
        params.extend(query_reviews)
    if urls_reviews:
        sql += " AND urls_review IN ({})".format(','.join('?' for _ in urls_reviews))
        params.extend(urls_reviews)
    if review_status == 'Reviewed':
        sql += " AND (" + " OR ".join([
            "is_independent_question<>''",
            "response_review<>''",
            "query_review<>''",
            "urls_review<>''",
            "last_updated_at IS NOT NULL",
        ]) + ")"
    elif review_status == 'Not Reviewed':
        sql += " AND (" + " AND ".join([
            "is_independent_question=''",
            "response_review=''",
            "query_review=''",
            "urls_review=''",
            "last_updated_at IS NULL",
        ]) + ")"

    sql += " ORDER BY timestamp DESC"

    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(sql, params)
        return [dict(r) for r in c.fetchall()]
