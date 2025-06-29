-- User Data
CREATE TABLE Users (
    id INTEGER PRIMARY KEY,
    tag TEXT UNIQUE NOT NULL,
    description TEXT,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0
);

-- Chats
CREATE TABLE Chats (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    is_group INTEGER NOT NULL DEFAULT 0
);

-- Chat members
CREATE TABLE ChatMembers (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES Chats(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    is_chat_admin INTEGER NOT NULL DEFAULT 0,
    color TEXT NOT NULL DEFAULT "#fff"
);

-- Optimize searching all chats of given user
CREATE INDEX idx_chatmembers_userid ON ChatMembers(user_id);

-- Chat invites
CREATE TABLE ChatInvites (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES Chats(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE
);

-- Optimize searching all invites of given user
CREATE INDEX idx_chatinvites_userid ON ChatInvites(user_id);

-- Chat messages
CREATE TABLE Messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES Chats(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    created INTEGER NOT NULL,
    content TEXT NOT NULL
);

-- Optimize searching all messages of given chat
CREATE INDEX idx_messages_chatid ON Messages(chat_id);
