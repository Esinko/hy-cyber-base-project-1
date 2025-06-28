from secrets import token_urlsafe
from pathlib import Path
from flask import (
    Flask,
    session,
    request
)

# Initialize Flask
app = Flask(__name__)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

# BEGIN VULNERABILITY 1
app.secret_key = "VERYSECURE"
# END VULNERABILITY 1

# BEGIN FIX 1
#secret_key_file = Path("./.secret")
#if not secret_key_file.exists():
#    secret_key_file.write_text(token_urlsafe(64), "utf-8")
#app.secret_key = secret_key_file.read_text("utf-8")
# END FIX 1

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

@app.get("/")
def home():
    return "Hello world!", 200

