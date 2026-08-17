"""Copy the legacy JSONB state record into additive relational tables."""

import os

import psycopg


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', created_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, username TEXT NOT NULL, role TEXT NOT NULL, token_hash TEXT NOT NULL, persistent BOOLEAN NOT NULL, created_at TIMESTAMPTZ NOT NULL, last_used_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL, absolute_expires_at TIMESTAMPTZ NOT NULL);
CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, username TEXT NOT NULL, title TEXT NOT NULL, updated_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS conversation_messages (conversation_id TEXT NOT NULL REFERENCES conversations(id), message_index INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, PRIMARY KEY (conversation_id, message_index));
CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, content TEXT NOT NULL, category TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL);
CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS briefing_schedule (id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id), morning TIME NOT NULL, afternoon TIME NOT NULL, enabled BOOLEAN NOT NULL);
CREATE TABLE IF NOT EXISTS briefings (briefing_index INTEGER PRIMARY KEY, period TEXT NOT NULL, text TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL);
CREATE TABLE IF NOT EXISTS grace_settings (id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id), personality TEXT NOT NULL, voice TEXT NOT NULL, humor TEXT NOT NULL, formality TEXT NOT NULL, response_length TEXT NOT NULL, proactive_comments TEXT NOT NULL, confirm_sensitive_actions BOOLEAN NOT NULL);
CREATE TABLE IF NOT EXISTS music_state (id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id), status TEXT NOT NULL, track TEXT, volume INTEGER NOT NULL, shuffle BOOLEAN NOT NULL, queue JSONB NOT NULL, queue_index INTEGER NOT NULL, updated_at TIMESTAMPTZ);
"""


def main() -> None:
    database_url = os.environ["GRACE_DATABASE_URL"]
    with psycopg.connect(database_url) as connection:
        connection.execute(SCHEMA)
        payload = connection.execute("SELECT payload FROM grace_state WHERE id = TRUE").fetchone()[0]
        cursor = connection.cursor()
        cursor.executemany("INSERT INTO users VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET username=EXCLUDED.username,password_hash=EXCLUDED.password_hash,role=EXCLUDED.role,created_at=EXCLUDED.created_at", [(item["id"], item["username"], item["password_hash"], item.get("role", "user"), item.get("created_at")) for item in payload["users"]])
        cursor.executemany("INSERT INTO sessions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (session_id) DO UPDATE SET last_used_at=EXCLUDED.last_used_at,expires_at=EXCLUDED.expires_at,absolute_expires_at=EXCLUDED.absolute_expires_at", [(item["session_id"], item["id"], item["username"], item["role"], item["token_hash"], item["persistent"], item["created_at"], item["last_used_at"], item["expires_at"], item["absolute_expires_at"]) for item in payload["sessions"]])
        cursor.executemany("INSERT INTO conversations VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title,updated_at=EXCLUDED.updated_at", [(item["id"], item["user_id"], item["username"], item["title"], item.get("updated_at")) for item in payload["conversations"]])
        cursor.executemany("INSERT INTO conversation_messages VALUES (%s,%s,%s,%s) ON CONFLICT (conversation_id,message_index) DO UPDATE SET role=EXCLUDED.role,content=EXCLUDED.content", [(conversation["id"], index, message["role"], message["content"]) for conversation in payload["conversations"] for index, message in enumerate(conversation["messages"])])
        cursor.executemany("INSERT INTO memories VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET content=EXCLUDED.content,category=EXCLUDED.category", [(item["id"], item["content"], item["category"], item["created_at"]) for item in payload["memories"]])
        cursor.executemany("INSERT INTO preferences VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", payload["preferences"].items())
        schedule = payload["briefing_schedule"]
        connection.execute("INSERT INTO briefing_schedule VALUES (TRUE,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET morning=EXCLUDED.morning,afternoon=EXCLUDED.afternoon,enabled=EXCLUDED.enabled", (schedule["morning"], schedule["afternoon"], schedule["enabled"]))
        cursor.executemany("INSERT INTO briefings VALUES (%s,%s,%s,%s) ON CONFLICT (briefing_index) DO UPDATE SET period=EXCLUDED.period,text=EXCLUDED.text,created_at=EXCLUDED.created_at", [(index, item["period"], item["text"], item["created_at"]) for index, item in enumerate(payload["briefings"])])
        settings = payload["grace_settings"]
        connection.execute("INSERT INTO grace_settings VALUES (TRUE,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET personality=EXCLUDED.personality,voice=EXCLUDED.voice,humor=EXCLUDED.humor,formality=EXCLUDED.formality,response_length=EXCLUDED.response_length,proactive_comments=EXCLUDED.proactive_comments,confirm_sensitive_actions=EXCLUDED.confirm_sensitive_actions", tuple(settings[key] for key in ("personality", "voice", "humor", "formality", "response_length", "proactive_comments", "confirm_sensitive_actions")))
        music = payload["music"]
        connection.execute("INSERT INTO music_state VALUES (TRUE,%s,%s,%s,%s,%s::jsonb,%s,%s) ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status,track=EXCLUDED.track,volume=EXCLUDED.volume,shuffle=EXCLUDED.shuffle,queue=EXCLUDED.queue,queue_index=EXCLUDED.queue_index,updated_at=EXCLUDED.updated_at", (music["status"], music["track"], music["volume"], music["shuffle"], psycopg.types.json.Jsonb(music["queue"]), music["index"], music["updated_at"]))


if __name__ == "__main__":
    main()
