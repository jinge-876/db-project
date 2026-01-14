from dotenv import load_dotenv
import os
from mysql.connector import pooling

# Load .env variables
load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE")
}

# Init db
_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        # Check: ENV wirklich gesetzt?
        missing = [k for k, v in DB_CONFIG.items() if not v]
        if missing:
            raise RuntimeError(f"Missing DB env vars: {missing}")

        _pool = pooling.MySQLConnectionPool(
            pool_name="pool",
            pool_size=5,
            **DB_CONFIG
        )
    return _pool

def get_conn():
    return _get_pool().get_connection()

# DB-Helper
def db_read(sql, params=None, single=False):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())

        if single:
            # liefert EIN Dict oder None
            row = cur.fetchone()
            print("db_read(single=True) ->", row)   # DEBUG
            return row
        else:
            # liefert Liste von Dicts (evtl. [])
            rows = cur.fetchall()
            print("db_read(single=False) ->", rows)  # DEBUG
            return rows

    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()


def db_write(sql, params=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        print("db_write OK:", sql, params)  # DEBUG
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()

def init_schema_and_seed():
    try:
        schema_sql = """
        CREATE TABLE IF NOT EXISTS patient (
          patientennummer INT PRIMARY KEY,
          `alter` INT,
          name TEXT,
          krankenkasse TEXT,
          krankheiten TEXT,
          `ehemalige aufenthalte` TEXT,
          `ehemalige medikamente` TEXT,
          bettnummer INT
        );
        """

        seed_sql = """
        INSERT INTO patient
          (patientennummer, `alter`, name, krankenkasse, krankheiten,
           `ehemalige aufenthalte`, `ehemalige medikamente`, bettnummer)
        VALUES
          (1001, 34, 'Mila Meier', 'CSS', 'Asthma', '2019: Bronchitis', 'Salbutamol', 12),
          (1002, 58, 'Noah Keller', 'Helsana', 'Diabetes Typ 2', '2021: Knie-OP', 'Metformin', 14),
          (1003, 22, 'Lea Schmid', 'SWICA', 'Migräne', '2020: Beobachtung', 'Ibuprofen', 15)
        ON DUPLICATE KEY UPDATE patientennummer = patientennummer;
        """

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(schema_sql)
        cur.execute(seed_sql)
        conn.commit()
        print("✅ init_schema_and_seed ok")

    except Exception as e:
        print("⚠️ init_schema_and_seed failed:", e)

    finally:
        try:
            cur.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass

