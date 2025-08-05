from functools import wraps
from typing import List
from flask import (
    request,
    session,
    redirect
)

from database.sqlite import get_db
from database.typings import ChatMember

def requires_authentication(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def requires_chat_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        
        if "chat_id" not in request.form:
            return redirect(location="/")
        
        chat_id = request.form["chat_id"]
        members = get_db().get_chat_members(chat_id)
        admin_user_ids = list(map(lambda member: member.user_id, list(filter(lambda member: member.is_chat_admin, members))))
        
        if session["user"]["id"] not in admin_user_ids and not session["user"]["is_admin"]:
            return redirect("/login")

        return f(*args, **kwargs)
    return decorated_function
