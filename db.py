"""
db.py — Database connection module

Manages a PostgreSQL connection pool for the game.
All other modules should import get_connection() from here
rather than creating their own connections.
"""

import os
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Pool setup
# ---------------------------------------------------------------------------
# The pool is created once when this module is first imported.
# minconn=1 keeps one connection always open (cheap, fast).
# maxconn=10 is a safe ceiling for a local game; raise it later for multiplayer.

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise EnvironmentError(
        "DATABASE_URL environment variable is not set. "
        "Add it to your .env file or shell environment before running the game."
    )

_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL,
)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

@contextmanager
def get_connection():
    """
    Borrow a connection from the pool.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ...")

    The connection is automatically returned to the pool when the
    'with' block exits — whether normally or due to an exception.
    If an exception occurs, the connection is rolled back before
    being returned.
    """
    conn = _pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def close_pool():
    """
    Close all connections in the pool.
    Call this once when the game shuts down cleanly.
    """
    _pool.closeall()