import sqlite3


def find_orders(db_path, customer_name):
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            f"SELECT id, total FROM orders WHERE customer = '{customer_name}'"
        )
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        conn.close()
