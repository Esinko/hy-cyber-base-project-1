from re import match
from flask import redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.sqlite import get_db
from util.includes import includes
from database.typings import (
    User,
    Chat
)
from util.auth import requires_authentication

def api_login(): # MARK: Login & Register
    # BEGIN FIX 3 (part-2)
    #if "tag" not in request.form or "password" not in request.form:
    #    return "Bad Request.", 400
    # END FIX 3 (part-2)

    user = get_db().get_user(request.form["tag"])

    try:
        if user and check_password_hash(user.password_hash, request.form["password"]):
            session["user"] = user
            return redirect("/")
    except Exception:
        raise Exception("Failed to login to", user, "with params", request.form)

    return redirect("/login?check-credentials")

def api_register():
    if not includes(request.form, ["tag", "password", "password-again"]):
        return "Bad Request.", 400

    tag = request.form["tag"]
    password = request.form["password"]
    password_again = request.form["password-again"]

    if get_db().get_user(tag):
        return redirect("/register?tag-taken")

    if password != password_again:
        return redirect("/register?password-mismatch")
    
    # BEGIN FLAW 4 (part-2)
    # NOT CHECKING PASSWORD STRENGTH
    # END FLAW 4 (part-2)
    
    # BEGIN FIX 4 (part-2)
    #if not bool(match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$", password)):
    #    return redirect("/register?password-weak")
    # END FIX 4 (part-2)

    get_db().create_user(User(tag=tag, password_hash=generate_password_hash(password)))

    return redirect("/login")

@requires_authentication # MARK: Create Chats
def api_create_dm():
    if "tag" not in request.form.keys():
        return "Bad Request.", 400
    
    other_user = get_db().get_user(request.form["tag"])
    if not other_user:
        return redirect("/?create-dm&no-user")
    
    if get_db().dm_exists_between(other_user.id, session["user"]["id"]):
        return redirect("/?create-dm&dm-exists")
    
    created_chat = get_db().create_chat(Chat(name="DM"), [
        session["user"]["id"],
        other_user.id
    ])

    return redirect(f"/?chat={created_chat.id}")

@requires_authentication # MARK: Create Chats
def api_create_group():
    if "name" not in request.form.keys():
        return "Bad Request.", 400
    
    created_chat = get_db().create_chat(Chat(name=request.form["name"], is_group=True), [ session["user"]["id"] ])

    return redirect(f"/?chat={created_chat.id}")

@requires_authentication # MARK: Send message
def api_send_message():
    if not includes(request.form, ["chat_id", "content"]) or len(request.form["content"]) < 1:
        return "Bad Request.", 400
    
    # Make sure user is in chat
    chat_id = int(request.form["chat_id"])
    members = get_db().get_chat_members(chat_id)
    if not members:
        return "Bad Request.", 400
    if len(list(filter(lambda member: member.user_id == session["user"]["id"], members))) == 0:
        return "Unauthorized.", 401
    
    # Create message
    get_db().create_message(chat_id, session["user"]["id"], request.form["content"])
    return redirect(f"/?chat={chat_id}")

