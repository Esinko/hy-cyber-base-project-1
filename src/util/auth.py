from functools import wraps
from flask import (
    session,
    redirect
)

def is_logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
