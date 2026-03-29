#!/usr/bin/env python3
"""
SQLite Database Layer

Replaces JSON files + shelve with a proper SQLite database.
Tables:
- player_stats: daily stat snapshots (enables rolling charts)
- lineup_predictions: prediction logs (enables accuracy tracking)
- breakout_predictions: breakout signal logs
- waiver_transactions: add/drop history
- cache: key-value cache with TTL
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "fantasy.db"


def _ensure_dir():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    """Context manager for database connections with WAL mode."""
    _ensure_dir()
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                date TEXT NOT NULL,
                stat_type TEXT NOT NULL,  -- 'hitter' or 'pitcher'
                stats_json TEXT NOT NULL,
                source TEXT DEFAULT 'statcast',
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(player_name, date, stat_type, source)
            );

            CREATE TABLE IF NOT EXISTS lineup_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                player_name TEXT NOT NULL,
                position TEXT,
                team TEXT,
                opponent TEXT,
                confidence REAL,
                recommendation TEXT,
                matchup_score REAL,
                park_score REAL,
                form_score REAL,
                platoon_score REAL,
                breakout_boost REAL,
                vegas_total REAL,
                actual_points REAL,
                was_accurate INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(player_name, date)
            );

            CREATE TABLE IF NOT EXISTS breakout_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_id INTEGER,
                player_type TEXT,
                signal TEXT,
                confidence REAL,
                improving_metrics TEXT,  -- JSON array
                declining_metrics TEXT,  -- JSON array
                key_metric_changes TEXT, -- JSON object
                outcome_date TEXT,
                was_successful INTEGER,
                success_score REAL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(player_name, date, signal)
            );

            CREATE TABLE IF NOT EXISTS waiver_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                add_player TEXT NOT NULL,
                add_position TEXT,
                add_team TEXT,
                drop_player TEXT,
                drop_position TEXT,
                drop_team TEXT,
                reason TEXT,
                confidence TEXT,
                value_gain REAL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_player_stats_name_date
                ON player_stats(player_name, date);
            CREATE INDEX IF NOT EXISTS idx_lineup_pred_date
                ON lineup_predictions(date);
            CREATE INDEX IF NOT EXISTS idx_breakout_pred_date
                ON breakout_predictions(date);
            CREATE INDEX IF NOT EXISTS idx_cache_expires
                ON cache(expires_at);
        """)
    logger.info(f"Database initialized at {DB_PATH}")


# ─── Player Stats ──────────────────────────────────────────────────────────

def save_player_stats(
    player_name: str,
    date: str,
    stat_type: str,
    stats: dict,
    source: str = "statcast",
) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO player_stats
               (player_name, date, stat_type, stats_json, source)
               VALUES (?, ?, ?, ?, ?)""",
            (player_name, date, stat_type, json.dumps(stats), source),
        )


def get_player_stats_history(
    player_name: str,
    days: int = 30,
    stat_type: Optional[str] = None,
) -> List[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        if stat_type:
            rows = conn.execute(
                """SELECT date, stat_type, stats_json FROM player_stats
                   WHERE player_name=? AND date>=? AND stat_type=?
                   ORDER BY date""",
                (player_name, cutoff, stat_type),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT date, stat_type, stats_json FROM player_stats
                   WHERE player_name=? AND date>=?
                   ORDER BY date""",
                (player_name, cutoff),
            ).fetchall()
    return [
        {"date": r["date"], "stat_type": r["stat_type"], "stats": json.loads(r["stats_json"])}
        for r in rows
    ]


# ─── Lineup Predictions ───────────────────────────────────────────────────

def log_lineup_prediction(
    date: str,
    player_name: str,
    position: str,
    team: str,
    opponent: str,
    confidence: float,
    recommendation: str,
    matchup_score: float = 0,
    park_score: float = 0,
    form_score: float = 0,
    platoon_score: float = 0,
    breakout_boost: float = 0,
    vegas_total: Optional[float] = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO lineup_predictions
               (date, player_name, position, team, opponent, confidence,
                recommendation, matchup_score, park_score, form_score,
                platoon_score, breakout_boost, vegas_total)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (date, player_name, position, team, opponent, confidence,
             recommendation, matchup_score, park_score, form_score,
             platoon_score, breakout_boost, vegas_total),
        )


def update_lineup_result(
    date: str, player_name: str, actual_points: float, was_accurate: bool
) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE lineup_predictions
               SET actual_points=?, was_accurate=?
               WHERE date=? AND player_name=?""",
            (actual_points, int(was_accurate), date, player_name),
        )


def get_lineup_accuracy(days: int = 30) -> dict:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT recommendation, confidence, actual_points, was_accurate
               FROM lineup_predictions
               WHERE date>=? AND actual_points IS NOT NULL""",
            (cutoff,),
        ).fetchall()

    if not rows:
        return {"total": 0, "accuracy": 0, "by_tier": {}}

    total = len(rows)
    correct = sum(1 for r in rows if r["was_accurate"])
    by_tier: Dict[str, dict] = {}
    for r in rows:
        tier = r["recommendation"]
        if tier not in by_tier:
            by_tier[tier] = {"total": 0, "correct": 0}
        by_tier[tier]["total"] += 1
        if r["was_accurate"]:
            by_tier[tier]["correct"] += 1

    for tier in by_tier:
        t = by_tier[tier]
        t["accuracy"] = round(t["correct"] / t["total"] * 100, 1) if t["total"] else 0

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total * 100, 1),
        "by_tier": by_tier,
    }


# ─── Breakout Predictions ─────────────────────────────────────────────────

def log_breakout_prediction(
    date: str,
    player_name: str,
    player_id: int,
    player_type: str,
    signal: str,
    confidence: float,
    improving_metrics: List[str],
    declining_metrics: List[str],
    key_metric_changes: dict,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO breakout_predictions
               (date, player_name, player_id, player_type, signal,
                confidence, improving_metrics, declining_metrics,
                key_metric_changes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (date, player_name, player_id, player_type, signal, confidence,
             json.dumps(improving_metrics), json.dumps(declining_metrics),
             json.dumps(key_metric_changes)),
        )


def get_breakout_accuracy(days: int = 90) -> dict:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT signal, confidence, was_successful, success_score
               FROM breakout_predictions
               WHERE date>=? AND was_successful IS NOT NULL""",
            (cutoff,),
        ).fetchall()

    if not rows:
        return {"total": 0, "accuracy": 0, "by_signal": {}}

    total = len(rows)
    correct = sum(1 for r in rows if r["was_successful"])
    by_signal: Dict[str, dict] = {}
    for r in rows:
        sig = r["signal"]
        if sig not in by_signal:
            by_signal[sig] = {"total": 0, "correct": 0}
        by_signal[sig]["total"] += 1
        if r["was_successful"]:
            by_signal[sig]["correct"] += 1

    for sig in by_signal:
        s = by_signal[sig]
        s["accuracy"] = round(s["correct"] / s["total"] * 100, 1) if s["total"] else 0

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total * 100, 1),
        "by_signal": by_signal,
    }


def get_recent_breakout_predictions(days: int = 30) -> List[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT date, player_name, player_type, signal, confidence,
                      improving_metrics, was_successful, success_score
               FROM breakout_predictions
               WHERE date>=?
               ORDER BY date DESC, confidence DESC""",
            (cutoff,),
        ).fetchall()
    return [
        {
            "date": r["date"],
            "player_name": r["player_name"],
            "player_type": r["player_type"],
            "signal": r["signal"],
            "confidence": r["confidence"],
            "improving_metrics": json.loads(r["improving_metrics"]) if r["improving_metrics"] else [],
            "was_successful": bool(r["was_successful"]) if r["was_successful"] is not None else None,
            "success_score": r["success_score"],
        }
        for r in rows
    ]


# ─── Waiver Transactions ──────────────────────────────────────────────────

def log_waiver_transaction(
    add_player: str,
    drop_player: str,
    reason: str = "",
    confidence: str = "",
    value_gain: float = 0,
    add_position: str = "",
    add_team: str = "",
    drop_position: str = "",
    drop_team: str = "",
) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO waiver_transactions
               (date, add_player, add_position, add_team,
                drop_player, drop_position, drop_team,
                reason, confidence, value_gain)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (datetime.now().strftime("%Y-%m-%d"),
             add_player, add_position, add_team,
             drop_player, drop_position, drop_team,
             reason, confidence, value_gain),
        )


def get_waiver_history(days: int = 90) -> List[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM waiver_transactions
               WHERE date>=? ORDER BY date DESC""",
            (cutoff,),
        ).fetchall()
    return [dict(r) for r in rows]


# ─── Cache (replaces shelve-based cache_manager) ──────────────────────────

def cache_get(key: str, max_age_hours: float = 24) -> Optional[Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value, created_at, expires_at FROM cache WHERE key=?",
            (key,),
        ).fetchone()

    if not row:
        return None

    if row["expires_at"]:
        expires = datetime.fromisoformat(row["expires_at"])
        if datetime.now() > expires:
            cache_delete(key)
            return None
    else:
        created = datetime.fromisoformat(row["created_at"])
        if (datetime.now() - created).total_seconds() / 3600 > max_age_hours:
            return None

    try:
        return json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return row["value"]


def cache_set(key: str, value: Any, ttl_hours: Optional[float] = None) -> None:
    expires_at = None
    if ttl_hours:
        expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO cache (key, value, created_at, expires_at)
               VALUES (?, ?, datetime('now'), ?)""",
            (key, json.dumps(value) if not isinstance(value, str) else value, expires_at),
        )


def cache_delete(key: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM cache WHERE key=?", (key,))


def cache_clear_expired() -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < datetime('now')"
        )
        return cursor.rowcount


# ─── Aggregate accuracy stats for the dashboard ──────────────────────────

def get_full_accuracy_report() -> dict:
    """Combined accuracy report for lineup + breakout + waiver predictions."""
    lineup = get_lineup_accuracy(days=90)
    breakout = get_breakout_accuracy(days=90)
    recent_breakouts = get_recent_breakout_predictions(days=30)
    waivers = get_waiver_history(days=90)

    return {
        "lineup": lineup,
        "breakout": breakout,
        "recent_breakout_predictions": recent_breakouts,
        "waiver_transaction_count": len(waivers),
        "generated_at": datetime.now().isoformat(),
    }


# Auto-initialize on import
try:
    init_db()
except Exception as e:
    logger.warning(f"Database auto-init failed (will retry on first use): {e}")
