from secrets import token_urlsafe
from pathlib import Path
from datetime import datetime
from flask import (
    Flask,
    session,
    request,
    send_from_directory,
    redirect,
    render_template,
    g
)
from werkzeug.exceptions import NotFound
from api import (
    api_login,
    api_register,
    api_create_dm,
    api_send_message,
    api_create_group
)
from database.sqlite import get_db

# Initialize Flask
app = Flask(__name__)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"


# BEGIN FLAW 3 (part-1)
app.debug = True
# END FLAW 3 (part-1)
# FIX FOR FLAW 3 (part-1): JUST REMOVE CODE ABOVE

# BEGIN FLAW 1
app.secret_key = "VERYSECURE"
# END FLAW 1

# BEGIN FIX 1
#secret_key_file = Path("./.secret")
#if not secret_key_file.exists():
#    secret_key_file.write_text(token_urlsafe(64), "utf-8")
#app.secret_key = secret_key_file.read_text("utf-8")
# END FIX 1

@app.teardown_appcontext
def close_connection(_):  # Auto-closes the database connection
    db = get_db()
    if db is not None:
        db.close()

with app.app_context(): # Initialize database
    get_db()

@app.before_request
def check_csrf():
    # /api/* paths require CSRF protections
    if request.path.startswith("/api/"):
        if (
            "request_token" not in request.form.keys() or
            request.form["request_token"] != session["request_token"]
        ):
            return "Unauthorized", 401
    elif "request_token" not in session:
        # Generate initial request token, expires if user logs out
        session["request_token"] = token_urlsafe(16)


@app.errorhandler(NotFound)
def handle_exception_not_found(_):
    return "Not found.", 404

app.jinja_env.globals["get_timestamp"] = lambda epoch: datetime.fromtimestamp(epoch).strftime("%d.%m.%Y @ %H:%M ")

# MARK: Site routes
@app.get("/")
def home():
    # Get data if logged in
    chats, chat_members, known_users, messages = ([], [], {}, [])
    if "user" in session:
        chats = get_db().get_chats(session["user"]["id"])
        chat_members = { chat.id: get_db().get_chat_members(chat.id) for chat in chats }
        know_user_ids = list({ member.user_id for members in chat_members.values() for member in members })
        known_users = { member_id: get_db().get_user_by_id(member_id) for member_id in know_user_ids }

        if "chat" in request.args:
            messages = get_db().get_messages(int(request.args["chat"]))

    return render_template("./pages/home.html", chats=chats, chat_members=chat_members, known_users=known_users, messages=messages)


@app.get("/login")
def login():
    return redirect("/") if "user" in session else render_template("./pages/login.html")

@app.get("/logout")
def logout():
    if "user" in session:
        del session["user"]

    return redirect("/")

@app.get("/register")
def register():
    return redirect("/") if "user" in session else render_template("./pages/register.html")


@app.get("/public/<string:path>")  # Public dir route
def public(path):
    return send_from_directory("public", path)


# MARK: API
app.add_url_rule("/api/login", view_func=api_login, methods=["POST"])
app.add_url_rule("/api/register", view_func=api_register, methods=["POST"])
app.add_url_rule("/api/create-dm", view_func=api_create_dm, methods=["POST"])
app.add_url_rule("/api/send-message", view_func=api_send_message, methods=["POST"])
app.add_url_rule("/api/create-group", view_func=api_create_group, methods=["POST"])
