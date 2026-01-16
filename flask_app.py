from flask import jsonify
from flask import Flask, redirect, render_template, request, url_for
from dotenv import load_dotenv
import os
import git
import hmac
import hashlib
from db import db_read, db_write
from auth import login_manager, authenticate, register_user
from flask_login import login_user, logout_user, login_required, current_user
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Load .env variables
load_dotenv()
W_SECRET = os.getenv("W_SECRET")

# Init flask app
app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = "supersecret"

# Init auth
login_manager.init_app(app)

# Init DB schema + seed (SAFE)
try:
    from db import init_schema_and_seed
    init_schema_and_seed()
except Exception as e:
    print("⚠️ init_schema_and_seed crashed:", repr(e))

# DON'T CHANGE
def is_valid_signature(x_hub_signature, data, private_key):
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

# DON'T CHANGE
@app.post('/update_server')
def webhook():
    x_hub_signature = request.headers.get('X-Hub-Signature')
    if is_valid_signature(x_hub_signature, request.data, W_SECRET):
        repo = git.Repo('./mysite')
        origin = repo.remotes.origin
        origin.pull()
        return 'Updated PythonAnywhere successfully', 200
    return 'Unathorized', 401

# Auth routes
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user = authenticate(
            request.form["username"],
            request.form["password"]
        )

        if user:
            login_user(user)
            return redirect(url_for("index"))

        error = "Benutzername oder Passwort ist falsch."

    return render_template(
        "auth.html",
        title="In dein Konto einloggen",
        action=url_for("login"),
        button_label="Einloggen",
        error=error,
        footer_text="Noch kein Konto?",
        footer_link_url=url_for("register"),
        footer_link_label="Registrieren"
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        ok = register_user(username, password)
        if ok:
            return redirect(url_for("login"))

        error = "Benutzername existiert bereits."

    return render_template(
        "auth.html",
        title="Neues Konto erstellen",
        action=url_for("register"),
        button_label="Registrieren",
        error=error,
        footer_text="Du hast bereits ein Konto?",
        footer_link_url=url_for("login"),
        footer_link_label="Einloggen"
    )

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


# --- DB visualisation routes ---
@app.route("/db_viz")
def db_viz():
    """
    Renders a D3 page that visualizes the database objects (users + todos)
    as a hierarchical edge-bundling plot.
    """
    return render_template("db_viz.html")

@app.route("/db_viz/data")
def db_viz_data():
    classes = []

    users = db_read("SELECT id, username FROM users ORDER BY id", ())
    for u in users:
        uname = u.get("username") or f"user{u['id']}"
        classes.append({"name": f"users.{u['id']}", "label": uname, "imports": []})

    todos = db_read("SELECT id, user_id, content, due FROM todos ORDER BY id", ())
    for t in todos:
        content = t.get("content") or ""
        label = (content[:50] + "...") if len(content) > 50 else content
        import_to = f"users.{t['user_id']}" if t.get("user_id") is not None else None

        entry = {"name": f"todos.{t['id']}", "label": label, "imports": []}
        if import_to:
            entry["imports"] = [import_to]
        classes.append(entry)

    patients = db_read("SELECT patientennummer, name FROM patient ORDER BY patientennummer", ())
    for p in patients:
        classes.append({"name": f"patient.{p['patientennummer']}", "label": p["name"], "imports": []})

    doctors = db_read("SELECT `ärztenummer`, name FROM arzt ORDER BY `ärztenummer`", ())
    for d in doctors:
        classes.append({"name": f"arzt.{d['ärztenummer']}", "label": d["name"], "imports": []})

    meds = db_read("SELECT fachname FROM medizin ORDER BY fachname", ())
    for m in meds:
        classes.append({"name": f"medizin.{m['fachname']}", "label": m["fachname"], "imports": []})

    behandelt = db_read("SELECT patientennummer, `ärztenummer` FROM behandelt", ())
    for b in behandelt:
        classes.append({
            "name": f"link.patient_arzt.{b['patientennummer']}.{b['ärztenummer']}",
            "label": "",
            "imports": [f"patient.{b['patientennummer']}", f"arzt.{b['ärztenummer']}"]
        })

    nimmt = db_read("SELECT patientennummer, fachname FROM nimmt", ())
    for n in nimmt:
        classes.append({
            "name": f"link.patient_med.{n['patientennummer']}.{n['fachname']}",
            "label": "",
            "imports": [f"patient.{n['patientennummer']}", f"medizin.{n['fachname']}"]
        })

    return jsonify({"classes": classes})

# App routes
@app.route("/", methods=["GET", "POST"])
def index():
    # GET
    if request.method == "GET":
        todos = db_read("SELECT id, content, due FROM todos ORDER BY due")
        return render_template("main_page.html", todos=todos)

    # POST
    content = request.form["contents"]
    due = request.form["due_at"]
    db_write("INSERT INTO todos (user_id, content, due) VALUES (%s, %s, %s)", (current_user.id, content, due, ))
    return redirect(url_for("index"))

@app.post("/complete")
def complete():
    todo_id = request.form.get("id")
    db_write("DELETE FROM todos WHERE user_id=%s AND id=%s", (current_user.id, todo_id,))
    return redirect(url_for("index"))

@app.route("/users", methods=["GET"])
def users():
    users = db_read("SELECT username FROM users ORDER BY username", ())
    return render_template("users.html", users=users)

@app.route("/erfassen", methods=["GET", "POST"])
def erfassen():
    message = None
    error = None

    if request.method == "POST":
        form_type = request.form.get("form_type")

        try:
            # -------- Patient --------
            if form_type == "patient":
                patientennummer = int(request.form["patientennummer"])
                alter = int(request.form["alter"])
                name = request.form["name"]
                krankenkasse = request.form["krankenkasse"]
                krankheiten = request.form.get("krankheiten", "")
                ehemalige_aufenthalte = request.form.get("ehemalige_aufenthalte", "")
                ehemalige_medikamente = request.form.get("ehemalige_medikamente", "")
                bettnummer = int(request.form["bettnummer"])

                db_write("""
                    INSERT INTO patient
                    (patientennummer, `alter`, name, krankenkasse, krankheiten,
                     `ehemalige aufenthalte`, `ehemalige medikamente`, bettnummer)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (patientennummer, alter, name, krankenkasse, krankheiten,
                      ehemalige_aufenthalte, ehemalige_medikamente, bettnummer))

                message = "✅ Patient gespeichert!"

            # -------- Arzt --------
            elif form_type == "arzt":
                a_nr = int(request.form["aerztenummer"])
                name = request.form["name"]
                spezialisierung = request.form["spezialisierung"]
                anstellzeit = int(request.form["anstellzeit"])

                db_write("""
                    INSERT INTO arzt (`ärztenummer`, name, spezialisierung, anstellzeit)
                    VALUES (%s,%s,%s,%s)
                """, (a_nr, name, spezialisierung, anstellzeit))

                message = "✅ Arzt gespeichert!"

            # -------- Medizin --------
            elif form_type == "medizin":
                fachname = request.form["fachname"]
                dosierung = request.form["dosierung"]

                db_write("""
                    INSERT INTO medizin (fachname, dosierung)
                    VALUES (%s,%s)
                """, (fachname, dosierung))

                message = "✅ Medizin gespeichert!"

            # -------- nimmt (Patient ↔ Medizin) --------
            elif form_type == "nimmt":
                patientennummer = int(request.form["patientennummer"])
                fachname = request.form["fachname"]

                db_write("""
                    INSERT INTO nimmt (patientennummer, fachname)
                    VALUES (%s,%s)
                """, (patientennummer, fachname))

                message = "✅ Beziehung 'nimmt' gespeichert!"

            # -------- behandelt (Patient ↔ Arzt) --------
            elif form_type == "behandelt":
                patientennummer = int(request.form["patientennummer"])
                aerztenummer = int(request.form["aerztenummer"])

                db_write("""
                    INSERT INTO behandelt (patientennummer, `ärztenummer`)
                    VALUES (%s,%s)
                """, (patientennummer, aerztenummer))

                message = "✅ Beziehung 'behandelt' gespeichert!"

        except Exception as e:
            error = f"❌ Fehler: {e}"

    # Für Dropdowns (praktisch):
    patients = db_read("SELECT patientennummer, name FROM patient ORDER BY patientennummer", ())
    doctors = db_read("SELECT `ärztenummer`, name FROM arzt ORDER BY `ärztenummer`", ())
    meds = db_read("SELECT fachname FROM medizin ORDER BY fachname", ())

    return render_template("erfassen.html", message=message, error=error,
                           patients=patients, doctors=doctors, meds=meds)

# DB Explorer routes
@app.route("/dbexplorer", methods=["GET", "POST"])
def dbexplorer():
    """
    Interactive database explorer that lets users view any table
    """
    # Liste aller verfügbaren Tabellen
    available_tables = [
        "patient", 
        "medizin", 
        "arzt", 
        "aktuellerAufenthalt",
        "nimmt",
        "behandelt"
    ]
    
    selected_table = None
    table_data = []
    columns = []
    error = None
    
    if request.method == "POST":
        selected_table = request.form.get("table")
        limit = request.form.get("limit", "50")
        search_column = request.form.get("search_column", "")
        search_value = request.form.get("search_value", "")
        
        # Validierung: Tabelle muss in der Liste sein
        if selected_table not in available_tables:
            error = "Ungültige Tabelle ausgewählt."
        else:
            try:
                # Basis-Query
                if search_column and search_value:
                    # Mit Suche (LIKE für Textsuche)
                    sql = f"SELECT * FROM {selected_table} WHERE {search_column} LIKE %s LIMIT {int(limit)}"
                    table_data = db_read(sql, (f"%{search_value}%",))
                else:
                    # Ohne Suche
                    sql = f"SELECT * FROM {selected_table} LIMIT {int(limit)}"
                    table_data = db_read(sql)
                
                # Spaltennamen extrahieren
                if table_data:
                    columns = list(table_data[0].keys())
                    
            except Exception as e:
                error = f"Fehler beim Laden der Daten: {str(e)}"
                table_data = []
    
    return render_template(
        "dbexplorer.html",
        available_tables=available_tables,
        selected_table=selected_table,
        columns=columns,
        table_data=table_data,
        error=error
    )

@app.route("/patient/new", methods=["GET", "POST"])
def new_patient():
    if request.method == "POST":
        patientennummer = request.form["patientennummer"]
        alter = request.form["alter"]
        name = request.form["name"]
        krankenkasse = request.form["krankenkasse"]
        krankheiten = request.form.get("krankheiten", "")

        db_write("""
            INSERT INTO patient
            (patientennummer, `alter`, name, krankenkasse, krankheiten,
             `ehemalige aufenthalte`, `ehemalige medikamente`, bettnummer)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (patientennummer, alter, name, krankenkasse, krankheiten, "", "", 0))

        return redirect(url_for("dbexplorer"))

    return render_template("patient_new.html")

@app.route("/arzt/new", methods=["GET", "POST"])
def new_arzt():
    if request.method == "POST":
        aerztenummer = int(request.form["aerztenummer"])
        name = request.form["name"]
        spezialisierung = request.form["spezialisierung"]
        anstellzeit = int(request.form["anstellzeit"])

        db_write("""
            INSERT INTO arzt (`ärztenummer`, name, spezialisierung, anstellzeit)
            VALUES (%s, %s, %s, %s)
        """, (aerztenummer, name, spezialisierung, anstellzeit))

        return redirect(url_for("dbexplorer"))

    return render_template("arzt_new.html")

@app.route("/aufenthalt/new", methods=["GET", "POST"])
def new_aufenthalt():
    if request.method == "POST":
        bettnummer = int(request.form["bettnummer"])
        pflegebedarf = request.form["pflegebedarf"]
        anfangsdatum = request.form["anfangsdatum"]  # Format: YYYY-MM-DD

        db_write("""
            INSERT INTO aktuellerAufenthalt (bettnummer, pflegebedarf, anfangsdatum)
            VALUES (%s, %s, %s)
        """, (bettnummer, pflegebedarf, anfangsdatum))

        return redirect(url_for("dbexplorer"))

    return render_template("aufenthalt_new.html")

@app.route("/nimmt/new", methods=["GET", "POST"])
def new_nimmt():
    if request.method == "POST":
        patientennummer = int(request.form["patientennummer"])
        fachname = request.form["fachname"]

        db_write("""
            INSERT INTO nimmt (patientennummer, fachname)
            VALUES (%s, %s)
        """, (patientennummer, fachname))

        return redirect(url_for("dbexplorer"))

    # Daten für Dropdowns laden
    patients = db_read(
        "SELECT patientennummer, name FROM patient ORDER BY name"
    )
    medikamente = db_read(
        "SELECT fachname FROM medizin ORDER BY fachname"
    )

    return render_template(
        "nimmt_new.html",
        patients=patients,
        medikamente=medikamente
    )

@app.route("/medizin/new", methods=["GET", "POST"])
def new_medizin():
    if request.method == "POST":
        fachname = request.form["fachname"].strip()
        dosierung = request.form["dosierung"].strip()

        db_write("""
            INSERT INTO medizin (fachname, dosierung)
            VALUES (%s, %s)
        """, (fachname, dosierung))

        return redirect(url_for("dbexplorer"))

    return render_template("medizin_new.html")

@app.route("/behandelt/new", methods=["GET", "POST"])
def new_behandelt():
    if request.method == "POST":
        patientennummer = int(request.form["patientennummer"])
        aerztenummer = int(request.form["aerztenummer"])

        db_write("""
            INSERT INTO behandelt (patientennummer, `ärztenummer`)
            VALUES (%s, %s)
        """, (patientennummer, aerztenummer))

        return redirect(url_for("dbexplorer"))

    # Dropdown-Daten laden
    patients = db_read(
        "SELECT patientennummer, name FROM patient ORDER BY name"
    )
    doctors = db_read(
        "SELECT `ärztenummer`, name FROM arzt ORDER BY name"
    )

    return render_template(
        "behandelt_new.html",
        patients=patients,
        doctors=doctors
    )

@app.post("/patient/delete")
def delete_patient():
    patientennummer = request.form.get("patientennummer")

    if not patientennummer:
        return redirect(url_for("patients_list"))

    # 1) Beziehungen zuerst löschen (wegen Foreign Keys)
    db_write("DELETE FROM nimmt WHERE patientennummer=%s", (patientennummer,))
    db_write("DELETE FROM behandelt WHERE patientennummer=%s", (patientennummer,))

    # 2) Patient löschen
    db_write("DELETE FROM patient WHERE patientennummer=%s", (patientennummer,))

    return redirect(url_for("patients_list"))

@app.get("/patient")
def patients_list():
    patients = db_read(
        "SELECT patientennummer, name, `alter`, krankenkasse, bettnummer FROM patient ORDER BY patientennummer"
    )
    return render_template("patients_list.html", patients=patients)

@app.post("/arzt/delete")
def delete_arzt():
    aerztenummer = request.form.get("aerztenummer")

    if not aerztenummer:
        return redirect(url_for("doctors_list"))

    # 1) Beziehungen zuerst löschen (wegen Foreign Keys)
    db_write("DELETE FROM behandelt WHERE `ärztenummer`=%s", (aerztenummer,))

    # 2) Arzt löschen
    db_write("DELETE FROM arzt WHERE `ärztenummer`=%s", (aerztenummer,))

    return redirect(url_for("doctors_list"))

@app.get("/arzt")
def doctors_list():
    doctors = db_read(
        "SELECT `ärztenummer`, name, spezialisierung, anstellzeit FROM arzt ORDER BY `ärztenummer`"
    )
    return render_template("doctors_list.html", doctors=doctors)

@app.get("/medizin")
def meds_list():
    meds = db_read("SELECT fachname, dosierung FROM medizin ORDER BY fachname")
    return render_template("meds_list.html", meds=meds)

@app.post("/medizin/delete")
def delete_medizin():
    fachname = request.form.get("fachname")
    if not fachname:
        return redirect(url_for("meds_list"))

    # Beziehungen zuerst löschen (nimmt referenziert medizin.fachname)
    db_write("DELETE FROM nimmt WHERE fachname=%s", (fachname,))

    # Medikament löschen
    db_write("DELETE FROM medizin WHERE fachname=%s", (fachname,))

    return redirect(url_for("meds_list"))

@app.get("/nimmt")
def nimmt_list():
    rows = db_read("""
        SELECT
          n.patientennummer,
          p.name AS patient_name,
          n.fachname,
          m.dosierung
        FROM nimmt n
        LEFT JOIN patient p ON p.patientennummer = n.patientennummer
        LEFT JOIN medizin m ON m.fachname = n.fachname
        ORDER BY n.patientennummer, n.fachname
    """)
    return render_template("nimmt_list.html", rows=rows)

@app.post("/nimmt/delete")
def delete_nimmt():
    patientennummer = request.form.get("patientennummer")
    fachname = request.form.get("fachname")

    if not patientennummer or not fachname:
        return redirect(url_for("nimmt_list"))

    db_write(
        "DELETE FROM nimmt WHERE patientennummer=%s AND fachname=%s",
        (patientennummer, fachname)
    )
    return redirect(url_for("nimmt_list"))

if __name__ == "__main__":
    app.run()
