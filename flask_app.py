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
login_manager.login_view = "login"

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
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# --- DB visualisation routes ---
@app.route("/db_viz")
@login_required
def db_viz():
    """
    Renders a D3 page that visualizes the database objects (users + todos)
    as a hierarchical edge-bundling plot.
    """
    return render_template("db_viz.html")


@app.route("/db_viz/data")
@login_required
def db_viz_data():
    """
    Returns a JSON structure for D3:
    {
      "classes": [
         {"name": "users.1", "label": "alice"},
         {"name": "todos.3", "label": "Buy milk", "imports": ["users.1"]}
         ...
      ]
    }
    Each todo has an import pointing to the user it references (by id).
    """
    # Load users
    users = db_read("SELECT id, username FROM users ORDER BY id", ())
    # Load todos
    todos = db_read("SELECT id, user_id, content, due FROM todos ORDER BY id", ())

    classes = []

    # Create user leaves: name = "users.<id>"
    for u in users:
        # safe label
        uname = u.get("username") or f"user{u['id']}"
        classes.append({
            "name": f"users.{u['id']}",
            "label": uname,
            # users won't import anyone
            "imports": []
        })

    # Create todo leaves: name = "todos.<id>", imports -> users.<user_id>
    for t in todos:
        # short content label (truncate for display if too long)
        content = t.get("content") or ""
        label = (content[:50] + "...") if len(content) > 50 else content
        import_to = f"users.{t['user_id']}" if t.get("user_id") is not None else None

        entry = {"name": f"todos.{t['id']}", "label": label}
        # only add imports if valid
        if import_to:
            entry["imports"] = [import_to]
        else:
            entry["imports"] = []
        classes.append(entry)

    return jsonify({"classes": classes})

# App routes
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # GET
    if request.method == "GET":
        todos = db_read("SELECT id, content, due FROM todos WHERE user_id=%s ORDER BY due", (current_user.id,))
        return render_template("main_page.html", todos=todos)

    # POST
    content = request.form["contents"]
    due = request.form["due_at"]
    db_write("INSERT INTO todos (user_id, content, due) VALUES (%s, %s, %s)", (current_user.id, content, due, ))
    return redirect(url_for("index"))

@app.post("/complete")
@login_required
def complete():
    todo_id = request.form.get("id")
    db_write("DELETE FROM todos WHERE user_id=%s AND id=%s", (current_user.id, todo_id,))
    return redirect(url_for("index"))

@app.route("/users", methods=["GET"])
@login_required
def users():
    users = db_read("SELECT username FROM users ORDER BY username", ())
    return render_template("users.html", users=users)

# DB Explorer routes
@app.route("/dbexplorer", methods=["GET", "POST"])
@login_required
def dbexplorer():
    """
    Interactive database explorer that lets users view any table
    """
    # Liste aller verfügbaren Tabellen
    available_tables = [
        "users", 
        "todos", 
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

if __name__ == "__main__":
    app.run()
