"""Initialize the Prediksi Stok project.

Creates the data directory and SQLite database with all required tables.
"""

from app.data import _get_connection

DB_PATH = "data/prediksi.db"


def main() -> None:
    conn = _get_connection(DB_PATH)
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    main()
