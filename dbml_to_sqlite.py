import os
import sqlite3
from pathlib import Path

from dbml_sqlite import toSQLite
from dotenv import load_dotenv

load_dotenv()


def dmbl_to_sqlite():
    """Converts DBML to SQLite."""
    sqlite_db_path = Path(os.getenv("SQLITE_DB_PATH"))
    dbml_path = Path(os.getenv("DBML_PATH"))
    print(dbml_path)

    ddl = toSQLite(str(dbml_path))
    con = sqlite3.connect(sqlite_db_path)
    with con:
        con.executescript(ddl)
    con.close()


if __name__ == '__main__':
    dmbl_to_sqlite()