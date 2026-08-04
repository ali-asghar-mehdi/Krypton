import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import sqlite3
import json
import urllib.parse

st.set_page_config(page_title="AI Workspace", layout="wide")

DB_FILE = "chats.db"

# ---------- DB SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            title TEXT PRIMARY KEY,
            messages TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS trash_chats (
            title TEXT PRIMARY KEY,
            messages TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS global_memory (
            id INTEGER PRIMARY KEY,
            instructions TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

def load_chats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, messages FROM chats")
    rows = c.fetchall()
    conn.close()
    chats = {title: json.loads(msgs) for title, msgs in rows}
    if not chats:
        chats = {"New Chat": []}
    return chats

def load_trash():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, messages FROM trash_chats")
    rows = c.fetchall()
    conn.close()
    return {title: json.loads(msgs) for title, msgs in rows}

def save_chat(title, messages):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chats (title, messages) VALUES (?, ?)", (title, json.dumps(messages)))
    conn.commit()
    conn.close()

def save_trash(title, messages):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO trash_chats (title, messages) VALUES (?, ?)", (title, json.dumps(messages)))
    conn.commit()
    conn.close()

def move_to_trash(title, messages):
    save_trash(title, messages)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM chats WHERE title = ?", (title,))
    conn.commit()
    conn.close()

def restore_chat(title):
    """Move chat from trash back to normal chats."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT messages FROM trash_chats WHERE title = ?", (title,))
    row = c.fetchone()
    if row:
        messages = json.loads(row[0])
        save_chat(title, messages)
        c.execute("DELETE FROM trash_chats WHERE title = ?", (title,))
        conn.commit()
    conn.close()
