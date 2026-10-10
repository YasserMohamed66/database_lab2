import os
import re
from functools import wraps

import bcrypt
import pymysql
from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template, request, session, url_for

load_dotenv()  # reads the .env file into os.environ

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]  # signs the session cookie
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,   # JavaScript cannot read the cookie
    SESSION_COOKIE_SAMESITE="Lax",  # not sent with POSTs from other sites
)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# ---------------------------------------------------------------
# Database: one connection per request, closed when the request ends
# ---------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = pymysql.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", 3306)),
            user=os.environ["DB_USER"],
            password=os.environ.get("DB_PASSWORD", ""),
            database=os.environ.get("DB_NAME", "registration"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------
# Passwords (bcrypt)
# ---------------------------------------------------------------

def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


# Used when the e-mail does not exist, so "unknown e-mail" takes as long
# as "wrong password" and the two cannot be told apart by timing.
DUMMY_HASH = hash_password("dummy-password")


def password_matches(password, stored_hash):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii"))
    except ValueError:  # bcrypt refuses passwords longer than 72 bytes
        return False


# ---------------------------------------------------------------
# Validation: the SAME rules and messages as the JavaScript
# ---------------------------------------------------------------

def validate_register(name, email, password, confirm_password):
    errors = {}

    if name == "":
        errors["name"] = "Name is required"
    elif len(name) > 100:
        errors["name"] = "Name is too long (100 characters at most)"

    if email == "":
        errors["email"] = "Email is required"
    elif len(email) > 255:
        errors["email"] = "Email is too long (255 characters at most)"
    elif not EMAIL_PATTERN.match(email):
        errors["email"] = "Enter a valid email address"

    if password == "":
        errors["password"] = "Password is required"
    elif len(password) < 8:
        errors["password"] = "Password must be at least 8 characters"
    elif len(password.encode("utf-8")) > 72:
        errors["password"] = "Password is too long (72 bytes at most)"
    elif not re.search(r"[A-Z]", password):
        errors["password"] = "Password must contain an uppercase letter"
    elif not re.search(r"[a-z]", password):
        errors["password"] = "Password must contain a lowercase letter"
    elif not re.search(r"[^A-Za-z0-9]", password):
        errors["password"] = "Password must contain a symbol (e.g. ! @ # $)"

    if confirm_password == "":
        errors["confirm_password"] = "Confirm password is required"
    elif password != "" and password != confirm_password:
        errors["confirm_password"] = "Passwords do not match"

    return errors


def validate_login(email, password):
    errors = {}
    if email == "":
        errors["email"] = "Email is required"
    if password == "":
        errors["password"] = "Password is required"
    return errors


def validate_title(raw_title):
    """Returns (clean_title, error_message_or_None)."""
    title = raw_title.strip()
    if title == "":
        return title, "Title is required"
    if len(title) > 200:
        return title, "Title is too long (200 characters at most)"
    return title, None


# ---------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------

def log_in(user_id, name):
    session.clear()  # forget anything from before
    session["user_id"] = user_id
    session["name"] = name


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


@app.after_request
def no_cache(response):
    # So the "Back" button after logout does not show a private page.
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------
# Register / login / logout
# ---------------------------------------------------------------

@app.route("/")
def home():
    return redirect(url_for("todos"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("todos"))

    if request.method == "GET":
        return render_template("register.html", errors={}, form={})

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    errors = validate_register(name, email, password, confirm_password)

    if not errors:  # only now do we touch the database
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
                    (email, name, hash_password(password)),
                )
                user_id = cur.lastrowid
            db.commit()
        except pymysql.err.IntegrityError as error:
            db.rollback()
            if error.args[0] != 1062:  # 1062 = duplicate entry (UNIQUE email)
                raise
            errors["email"] = "Email Already Exists"
        else:
            log_in(user_id, name)
            return redirect(url_for("todos"))  # redirect after POST: refresh is safe

    # Show the form again with the messages (never send the passwords back).
    return render_template("register.html", errors=errors, form={"name": name, "email": email})


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("todos"))

    if request.method == "GET":
        return render_template("login.html", errors={}, form={}, form_error=None)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    errors = validate_login(email, password)
    form_error = None

    if not errors:
        with get_db().cursor() as cur:
            cur.execute(
                "SELECT user_id, name, password_hash FROM users WHERE email = %s",
                (email,),
            )
            user = cur.fetchone()

        stored_hash = user["password_hash"] if user else DUMMY_HASH
        if password_matches(password, stored_hash) and user:
            log_in(user["user_id"], user["name"])
            return redirect(url_for("todos"))

        # Same message for a wrong e-mail and a wrong password.
        form_error = "Invalid email or password"

    return render_template("login.html", errors=errors, form={"email": email}, form_error=form_error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------
# To-do list (every query has AND user_id = %s, taken from the session)
# ---------------------------------------------------------------

FILTERS = ("all", "open", "done")


def current_filter():
    """The filter and the search text come from the address (?status=open&q=milk)."""
    status = request.args.get("status", "all")
    if status not in FILTERS:
        status = "all"
    query = request.args.get("q", "").strip()[:200]
    return status, query


def keep_args():
    """Only the non-default values, so the address stays short."""
    status, query = current_filter()
    args = {}
    if status != "all":
        args["status"] = status
    if query:
        args["q"] = query
    return args


def list_url():
    """The list address with the same filter, so an action does not reset it."""
    return url_for("todos", **keep_args())


def render_todos(add_error=None, add_value="", edit_error=None):
    with get_db().cursor() as cur:
        cur.execute(
            "SELECT todo_id, title, is_done, created_at FROM todos "
            "WHERE user_id = %s ORDER BY todo_id DESC",
            (session["user_id"],),
        )
        items = cur.fetchall()

    # Filter and search happen here, on this user's rows only,
    # so the SQL stays exactly the query from the lab.
    status, query = current_filter()
    shown = items
    if status == "open":
        shown = [item for item in shown if not item["is_done"]]
    elif status == "done":
        shown = [item for item in shown if item["is_done"]]
    if query:
        shown = [item for item in shown if query.lower() in item["title"].lower()]

    # When an edit failed, show what the user typed next to the message.
    if edit_error:
        for item in shown:
            if item["todo_id"] == edit_error["todo_id"]:
                item["title"] = edit_error["value"]

    return render_template(
        "todos.html",
        name=session["name"],
        todos=shown,
        total=len(items),
        open_count=sum(1 for item in items if not item["is_done"]),
        status=status,
        q=query,
        keep=keep_args(),
        add_error=add_error,
        add_value=add_value,
        edit_error=edit_error,
    )


@app.route("/todos")
@login_required
def todos():
    return render_todos()


@app.route("/todos/add", methods=["POST"])
@login_required
def add_todo():
    title, error = validate_title(request.form.get("title", ""))
    if error:
        return render_todos(add_error=error, add_value=request.form.get("title", ""))

    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO todos (user_id, title) VALUES (%s, %s)",
            (session["user_id"], title),
        )
    db.commit()
    return redirect(list_url())


@app.route("/todos/<int:todo_id>/edit", methods=["POST"])
@login_required
def edit_todo(todo_id):
    raw_title = request.form.get("title", "")
    title, error = validate_title(raw_title)
    if error:
        return render_todos(
            edit_error={"todo_id": todo_id, "message": error, "value": raw_title}
        )

    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE todos SET title = %s WHERE todo_id = %s AND user_id = %s",
            (title, todo_id, session["user_id"]),
        )
    db.commit()
    return redirect(list_url())


@app.route("/todos/<int:todo_id>/toggle", methods=["POST"])
@login_required
def toggle_todo(todo_id):
    is_done = 1 if request.form.get("is_done") == "1" else 0

    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE todos SET is_done = %s WHERE todo_id = %s AND user_id = %s",
            (is_done, todo_id, session["user_id"]),
        )
    db.commit()
    return redirect(list_url())


@app.route("/todos/<int:todo_id>/delete", methods=["POST"])
@login_required
def delete_todo(todo_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "DELETE FROM todos WHERE todo_id = %s AND user_id = %s",
            (todo_id, session["user_id"]),
        )
    db.commit()
    return redirect(list_url())


# ---------------------------------------------------------------
# Friendly error pages (no stack traces)
# ---------------------------------------------------------------

@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html", code=404, message="We could not find that page."
    ), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return render_template(
        "error.html", code=405, message="That action is not allowed here."
    ), 405


@app.errorhandler(500)
def server_error(_error):
    return render_template(
        "error.html", code=500, message="Something went wrong on our side. Please try again."
    ), 500


if __name__ == "__main__":
    app.run(debug=False)
