from sqlite3 import Error, connect
from pathlib import Path
from types import new_class
from typing import Any, List, Optional, Tuple, Union
from flask import g
from time import time
from database.typings import (
    DatabaseException,
    User,
    Chat,
    ChatMember,
    Message,
    ChatInvite
)

class Database:
    def __init__(self, database="./main.db", schema="./schema.sql", init: str = ""):
        self.database_filepath = database
        self.schema_filepath = schema
        self.init_filepath = init
        self.connection = None

    # Open the database connection
    def open(self):
        if self.connection:
            raise DatabaseException("Database already open.")

        schema_file = Path(self.schema_filepath)
        if not schema_file.exists():
            raise FileNotFoundError("Schema file not found.")

        init_file = None
        if self.init_filepath:
            init_file = Path(self.init_filepath)
            if not init_file.exists():
                raise FileNotFoundError("Init file not found.")

        # Load
        database_file = Path(self.database_filepath)
        if not database_file.exists():
            schema = schema_file.read_text("utf-8")
            self.connection = connect(database_file)
            self.connection.executescript(schema)

            # Init if init is present
            if init_file:
                init = init_file.read_text("utf-8")
                self.connection.executescript(init)
            
            self.connection.commit()
        else:
            self.connection = connect(database_file)

        # Configure
        self.connection.execute("PRAGMA foreign_keys = ON")

        return self

    def close(self):
        if not self.connection:
            raise DatabaseException("Database not open.")
        self.connection.close()

    # Execute a command against the database
    def execute(self, query: str, parameters: Union[Tuple[Any, ...], dict] = ()) -> int:
        cursor = None
        try:
            if not self.connection:
                raise DatabaseException("Database not open!")
            cursor = self.connection.cursor()
            cursor.execute(query, parameters)
            self.connection.commit()
        except Error as err:
            print("Database execution error:", err, "For:",
                  query, "With params:", parameters)
            if self.connection:
                self.connection.rollback()
        return int(cursor.lastrowid) if cursor is not None and cursor.lastrowid is not None else -1

    # Query the database
    def query(self,
              query: str,
              parameters: Optional[Union[Tuple[Any, ...], dict]],
              limit: int = -1) -> List[Tuple[Any, ...]]:
        if not self.connection:
            raise DatabaseException("Database not open!")
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, parameters) # type: ignore
        except Error as e:
            print("Database execution error:", e, "For:",
                  query, "With params:", parameters)
            self.connection.rollback()
        results = cursor.fetchmany(limit)
        return results

class DatabaseAbstractions(Database):
    def get_user(self, tag: str) -> Union[User, None]:
        result = self.query("SELECT * FROM Users WHERE tag = ?", parameters=(tag,))
        return User(*result[0]) if len(result) > 0 else None
    
    def get_user_by_id(self, user_id: int) -> Union[User, None]:
        result = self.query("SELECT * FROM Users WHERE id = ?", parameters=(user_id,))
        return User(*result[0]) if len(result) > 0 else None

    def create_user(self, user: User):
        self.execute("INSERT INTO Users (tag, description, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                     parameters=(user.tag, user.description, user.password_hash, user.is_admin))
        
    def edit_user(self, id: int, new_user: User):
        self.execute("UPDATE Users SET tag = ?, SET description = ?, SET password_hash = ?, SET is_admin = ? WHERE id = ?",
                     parameters=(new_user.tag, new_user.description, new_user.password_hash, new_user.is_admin, id))
        
    def create_chat(self, new_chat: Chat, member_ids: List[int]) -> Chat:
        lastrowid = self.execute("INSERT INTO Chats (name, is_group) VALUES (?, ?)",
                     parameters=(new_chat.name, new_chat.is_group))
        chat_id = int(lastrowid)

        for member_id in member_ids:
            self.add_user_to_chat(chat_id, member_id)
            
        new_chat.id = chat_id
        return new_chat
    
    def edit_group_chat_name(self, chat_id: int, new_name: str):
        self.execute("UPDATE Chats SET name = ? WHERE id = ?",
                     parameters=(new_name, chat_id))
        
    def kick_member_from_group(self, chat_id: int, user_id: int):
        self.execute("DELETE FROM ChatMembers WHERE chat_id = ? AND user_id = ?",
                     parameters=(chat_id, user_id))
        
    def set_chat_member_admin(self, chat_id: int, user_id: int, is_admin: bool) :
        self.execute("UPDATE ChatMembers SET is_chat_admin = ? WHERE user_id = ? AND chat_id = ?",
                     parameters=(is_admin, user_id, chat_id))
    
    def dm_exists_between(self, first_user_id: int, second_user_id: int) -> bool:
        results = self.query("""
                     SELECT c.id
                     FROM Chats c
                     JOIN ChatMembers cm1 ON cm1.chat_id = c.id AND cm1.user_id = ?
                     JOIN ChatMembers cm2 ON cm2.chat_id = c.id AND cm2.user_id = ?
                     WHERE c.is_group = 0
                     """,
                     parameters=(first_user_id, second_user_id))
        return len(results) != 0
    
    def add_user_to_chat(self, chat_id: int, user_id: int):
        self.execute("INSERT INTO ChatMembers (chat_id, user_id) VALUES (?, ?)",
                     parameters=(chat_id, user_id))
        
    def invite_user_to_group(self, chat_id: int, user_tag: str) -> bool:
        # BEGIN FLAW 2
        self.connection.executescript(f"INSERT INTO ChatInvites (chat_id, user_id) SELECT '{chat_id}', id FROM Users WHERE tag = '{user_tag}'")
        self.connection.commit()
        return True
        # END FLAW 2
        
        # BEGIN FIX 2
        # REPLACE FLAW ABOVE WITH FIX BELOW
        #user_to_invite = self.get_user(user_tag)
        #if not user_to_invite: return False
        #self.execute(f"INSERT INTO ChatInvites (chat_id, user_id) VALUES (?, ?)",
        #             parameters=(chat_id, user_to_invite.id))
        #return True
        # END FIX 2

    def remove_user_invite(self, chat_id: int, user_id: int):
        self.execute("DELETE FROM ChatInvites WHERE chat_id = ? AND user_id = ?", parameters=(chat_id, user_id))
        
    def get_chats(self, user_id: int, page=0):
        results = self.query("""
                             SELECT c.*
                             FROM Chats AS c
                             JOIN ChatMembers AS cm ON cm.chat_id = c.id
                             WHERE cm.user_id = ?
                             """,
                             parameters=(user_id,))
        return [ Chat(*result) for result in results ]
    
    def get_chat_by_id(self, chat_id: int) -> Chat | None:
        results = self.query("""
                             SELECT c.*
                             FROM Chats AS c
                             WHERE c.id = ?
                             """,
                             parameters=(chat_id,))
        return Chat(*results[0]) if len(results) != 0 else None
    
    def get_chat_members(self, chat_id: int) -> List[ChatMember]:
        results = self.query("""
                             SELECT
                             cm.*
                             FROM ChatMembers cm
                             JOIN Users u ON cm.user_id = u.id
                             WHERE cm.chat_id = ?
                             """,
                             parameters=(chat_id,))
        return [ ChatMember(*result) for result in results ]
    
    def get_chat_invites(self, chat_id: int) -> List[ChatInvite]:
        results = self.query("""
                             SELECT
                             ci.*
                             FROM ChatInvites ci
                             JOIN Users u ON ci.user_id = u.id
                             WHERE ci.chat_id = ?
                             """,
                             parameters=(chat_id,))
        return [ ChatInvite(*result) for result in results ]
    
    def get_user_invites(self, user_id: int) -> List[Chat]:
        results = self.query("""
                             SELECT
                             c.id as id,
                             c.name as name,
                             c.is_group as is_group
                             FROM ChatInvites ci
                             JOIN Chats c ON ci.chat_id = c.id
                             WHERE ci.user_id = ?
                             """,
                             parameters=(user_id,))
        return [ Chat(*result) for result in results ]
    
    def get_messages(self, chat_id: int):
        results = self.query("""
                             SELECT
                             m.*
                             FROM Messages m
                             JOIN Users u ON m.user_id = u.id
                             WHERE m.chat_id = ?
                             ORDER BY m.created ASC
                             """,
                             parameters=(chat_id,))
        return [ Message(*result) for result in results ]
    
    def create_message(self, chat_id: int, user_id: int, content: str):
        self.execute("INSERT INTO Messages (chat_id, user_id, created, content) VALUES (?, ?, ?, ?)",
                     parameters=(chat_id, user_id, int(time()), content))

def get_db() -> DatabaseAbstractions:
    db = getattr(g, "_database", None)
    if db is None:
        db = DatabaseAbstractions("./main.db", "./src/database/schema.sql", "./src/database/init.sql")
        db.open()
    return db
