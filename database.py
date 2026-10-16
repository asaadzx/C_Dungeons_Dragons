# ---------------------------------------------------------------------------
# database.py
# Handles all low-level SQLite database work.
#
# Responsibilities (Database Specialist role):
#   * Open a connection to database.db
#   * Return rows that behave like dictionaries (easy to use in Jinja2)
#   * Create the tables from schema.sql on first run
# ---------------------------------------------------------------------------

import sqlite3   # built-in Python module for SQLite databases
import os        # used to build safe file paths regardless of the OS


# Absolute path to the SQLite file, next to this Python file.
# Using os.path.dirname(__file__) means the path works no matter which
# folder the app is launched from.
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def get_db_connection():
    """
    Open and return a connection to the SQLite database.

    - sqlite3.Row as row_factory lets us access columns by name,
      e.g. row['title'] instead of row[1]. This makes the Jinja2
      templates much easier to read.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create the tables defined in schema.sql if they do not exist yet.

    Called once when app.py starts, so the app never crashes on a fresh
    machine that has no database file yet.
    """
    conn = get_db_connection()
    # Read the whole schema file and run it as one script.
    with open(os.path.join(os.path.dirname(__file__), 'schema.sql'),
              'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()   # save the changes to disk
    conn.close()    # always close the connection when finished
