from dataclasses import dataclass
from typing import List

class DatabaseException(Exception):
    def __init__(self, message):
        super().__init__(message)

@dataclass
class User():
    id: int = -1
    tag: str = ""
    description: str = ""
    password_hash: str = ""
    is_admin: int = 0

@dataclass
class Chat():
    id: int = -1
    name: str = ""
    is_group: int = 0

@dataclass
class ChatMember():
    id: int = -1
    chat_id: int = -1
    user_id: int = -1
    is_chat_admin: int = 0
    color: str = "#fff"

@dataclass
class ChatInvite():
    id: int = -1
    chat_id: int = -1
    user_id: int = -1

@dataclass
class Message():
    id: int
    chat_id: int
    user_id: int
    created: int
    content: str
