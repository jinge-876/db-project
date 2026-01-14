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
        conn = get_conn()
        cur = conn.cursor()

        # -------- CREATE TABLES --------

        # patient (muss zuerst!)
        cur.execute("""
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
        """)

        # medizin
        cur.execute("""
        CREATE TABLE IF NOT EXISTS medizin (
          fachname VARCHAR(255) PRIMARY KEY,
          dosierung VARCHAR(255)
        );
        """)

        # arzt
        cur.execute("""
        CREATE TABLE IF NOT EXISTS arzt (
          ärztenummer INT PRIMARY KEY,
          name VARCHAR(255),
          spezialisierung VARCHAR(255),
          anstellzeit INT
        );
        """)

        # aktuellerAufenthalt
        cur.execute("""
        CREATE TABLE IF NOT EXISTS aktuellerAufenthalt (
          bettnummer INT PRIMARY KEY,
          pflegebedarf TEXT,
          anfangsdatum DATE
        );
        """)

        # nimmt (Patient ↔ Medizin)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS nimmt (
          patientennummer INT,
          fachname VARCHAR(255),
          PRIMARY KEY (patientennummer, fachname),
          FOREIGN KEY (patientennummer) REFERENCES patient(patientennummer),
          FOREIGN KEY (fachname) REFERENCES medizin(fachname)
        );
        """)

        # behandelt (Patient ↔ Arzt)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS behandelt (
          patientennummer INT,
          ärztenummer INT,
          PRIMARY KEY (patientennummer, ärztenummer),
          FOREIGN KEY (patientennummer) REFERENCES patient(patientennummer),
          FOREIGN KEY (ärztenummer) REFERENCES arzt(ärztenummer)
        );
        """)

        # -------- SEEDS (Reihenfolge wichtig) --------

        # medizin zuerst (weil nimmt darauf zeigt)
        cur.execute("""
        INSERT INTO medizin (fachname, dosierung)
        VALUES
          ('Salbutamol', '2 Hübe bei Atemnot'),
          ('Metformin', '500 mg morgens und abends'),
          ('Ibuprofen', '400 mg bei Schmerzen')
        ON DUPLICATE KEY UPDATE fachname = fachname;
        """)

        # arzt (weil behandelt darauf zeigt)
        cur.execute("""
        INSERT INTO arzt (ärztenummer, name, spezialisierung, anstellzeit)
        VALUES
          (1, 'Dr. Anna Weber', 'Innere Medizin', 8),
          (2, 'Dr. Lukas Frei', 'Neurologie', 5),
          (3, 'Dr. Sarah Müller', 'Orthopädie', 10)
        ON DUPLICATE KEY UPDATE ärztenummer = ärztenummer;
        """)

        # patient (mit ehemalige Aufenthalte)
        cur.execute("""
        INSERT INTO patient
          (patientennummer, `alter`, name, krankenkasse, krankheiten,
           `ehemalige aufenthalte`, `ehemalige medikamente`, bettnummer)
        VALUES
          (1001, 34, 'Mila Meier', 'CSS', 'Asthma',
           '2018: Lungenentzündung; 2019: Bronchitis', 'Salbutamol', 12),
          (1002, 58, 'Noah Keller', 'Helsana', 'Diabetes Typ 2',
           '2020: Bluthochdruck; 2021: Knie-OP', 'Metformin', 14),
          (1003, 22, 'Lea Schmid', 'SWICA', 'Migräne',
           '2019: Beobachtung Neurologie', 'Ibuprofen', 15)
        ON DUPLICATE KEY UPDATE patientennummer = patientennummer;
        """)

        # aktueller Aufenthalt
        cur.execute("""
        INSERT INTO aktuellerAufenthalt (bettnummer, pflegebedarf, anfangsdatum)
        VALUES
          (12, 'mittel', '2026-01-10'),
          (14, 'hoch', '2026-01-08'),
          (15, 'niedrig', '2026-01-12')
        ON DUPLICATE KEY UPDATE bettnummer = bettnummer;
        """)

        # nimmt (braucht patient + medizin)
        cur.execute("""
        INSERT INTO nimmt (patientennummer, fachname)
        VALUES
          (1001, 'Salbutamol'),
          (1002, 'Metformin'),
          (1003, 'Ibuprofen')
        ON DUPLICATE KEY UPDATE patientennummer = patientennummer;
        """)

        # behandelt (braucht patient + arzt)
        cur.execute("""
        INSERT INTO behandelt (patientennummer, ärztenummer)
        VALUES
          (1001, 1),
          (1002, 3),
          (1003, 2)
        ON DUPLICATE KEY UPDATE patientennummer = patientennummer;
        """)

        conn.commit()
        print("✅ init_schema_and_seed: alle Tabellen + Seed-Daten OK")

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
