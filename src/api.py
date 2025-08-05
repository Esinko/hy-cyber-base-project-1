from flask import redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from json import dumps
from time import time, sleep
from database.sqlite import get_db
from util.includes import includes
from database.typings import (
    User,
    Chat
)
from util.auth import requires_authentication, requires_chat_admin

def api_login(): # MARK: Login & Register
    # BEGIN FIX 3
    #if "tag" not in request.form or "password" not in request.form:
    #    return "Bad Request.", 400
    # END FIX 3

    user = get_db().get_user(request.form["tag"])

    try:
        if user and check_password_hash(user.password_hash, request.form["password"]):
            session["user"] = {
                "description": user.description,
                "id": user.id,
                "is_admin": user.is_admin,
                "tag": user.tag
            }
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
    # NOT CHECKING PASSWORD STRENGTH?!
    # Flaw is the lack of following fix.
    # END FLAW 4 (part-2)
    
    # BEGIN FIX 4 (part-2)
    # This is a sane password security strength check from OWASP. 8-long alpha numeric with special char.
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

    # Make chat creator (for now the only) admin
    get_db().set_chat_member_admin(created_chat.id, session["user"]["id"], True)

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

@requires_authentication  # MARK: Polling new-message
def api_poll_new_message():
    data = request.get_json()

    if not includes(data, ["chat_id", "last_message_id"]):
        return "Bad Request.", 400

    chat_id = int(data["chat_id"])
    last_message_id = int(data["last_message_id"])
    start_time = time()

    # FLAW 1 IS THE LACK OF THE FOLLOWING FIX
    # BEGIN FIX 1
    #members = get_db().get_chat_members(chat_id)
    #if not list(filter(lambda member: member.user_id == session["user"]["id"], members)):
    #    return "Unauthorized.", 401
    # END FIX 1

    while time() - start_time < 30: # seconds (timeout)
        messages = get_db().get_messages(chat_id)
        messages.reverse()

        if messages and messages[0].id != last_message_id:
            new_messages = []
            for message in messages:
                if message.id == last_message_id:
                    break
                author = get_db().get_user_by_id(message.user_id)
                new_messages.append({
                    "id": message.id,
                    "content": message.content,
                    "username": author.tag if author else "Unknown",
                    "created": message.created
                })

            return dumps(new_messages), 200

        sleep(2) # seconds (interval)

    return "", 204

@requires_authentication # MARK: Invite
@requires_chat_admin
def api_invite():
    if not includes(request.form, ["tag", "chat_id"]):
        return "Bad Request.", 400
    
    chat_id = int(request.form["chat_id"])
    tag = request.form["tag"]

    # Make sure chat is a group
    chat = get_db().get_chat_by_id(chat_id)
    if not chat or not chat.is_group:
        return "Bad Request.", 400
    
    # Make sure user is not already invited
    # At this point verbose error is possible (session user has admin)
    user_to_invite = get_db().get_user(tag)
    user_to_invite_id = user_to_invite.id if user_to_invite else None
    if any(map(lambda inv: inv.user_id == user_to_invite_id, get_db().get_chat_invites(chat_id))):
        return redirect(f"/?chat={chat_id}&invite&has-invite")
    
    # Make sure user to invite is not already in that group
    members = get_db().get_chat_members(chat_id)
    if user_to_invite_id in list(map(lambda member: member.user_id, members)):
        return redirect(f"/?chat={chat_id}&invite&is-member")
    
    # Create invite
    did_invite = get_db().invite_user_to_group(chat_id, tag)
    if not did_invite:
        return redirect(f"/?chat={chat_id}&invite&no-user")

    return redirect(f"/?chat={chat_id}")

@requires_authentication
def api_join():
    if "chat_id" not in request.form:
        return "Bad Request.", 400
    
    chat_id = int(request.form["chat_id"])

    # Make sure user has been invited to group
    if not any(map(
        lambda inv: inv.user_id == session["user"]["id"],
        get_db().get_chat_invites(chat_id)
    )) and not session["user"]["is_admin"]:
        return "Unauthorized.", 401
    
    # Remove invite or join
    if request.path.endswith("accept"):
        get_db().add_user_to_chat(chat_id, session["user"]["id"])
        get_db().remove_user_invite(chat_id, session["user"]["id"])
        return redirect(f"/?chat={chat_id}")
    elif request.path.endswith("reject"):
        get_db().remove_user_invite(chat_id, session["user"]["id"])
        return redirect(f"/?chat={request.args["return"]}" if "return" in request.args else "/")

    return "Well... uh... Success!", 200

@requires_authentication # MARK: Chat Management
@requires_chat_admin
def api_change_group_name():
    if not includes(request.form, ["name", "chat_id"]):
        return "Bad Request.", 400
    
    chat_id = int(request.form["chat_id"])
    name = request.form["name"]

    if len(name) < 1:
        return "Name too short.", 400

    # Make sure chat is a group
    chat = get_db().get_chat_by_id(chat_id)
    if not chat or not chat.is_group:
        return "Bad Request.", 400
    
    # Edit chat
    get_db().edit_group_chat_name(chat_id, name)

    return redirect(f"/?chat={chat_id}&settings")

@requires_authentication
@requires_chat_admin
def api_kick_member():
    if not includes(request.form, ["tag", "chat_id"]):
        return "Bad Request.", 400
    
    chat_id = int(request.form["chat_id"])
    tag = request.form["tag"]

    # Make sure chat is a group
    chat = get_db().get_chat_by_id(chat_id)
    if not chat or not chat.is_group:
        return "Bad Request.", 400
    
    # Make sure given tag exists
    user_to_kick = get_db().get_user(tag)
    if not user_to_kick:
        return redirect(f"/?chat={chat_id}&settings")
    
    # Make sure user is the chat
    members = get_db().get_chat_members(chat_id)
    if user_to_kick.id not in list(map(lambda member: member.user_id, members)):
        return redirect(f"/?chat={chat_id}&settings")
    
    # Edit chat
    get_db().kick_member_from_group(chat_id, user_to_kick.id)

    return redirect(f"/?chat={chat_id}&settings")
