import streamlit as st
import os
import json
import random
from verses import parse_verses_from_text

USER_DATA_DIR = "user_data"
USERS_FILE = "users.json"

# Hilfsfunktionen
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def get_user_file(username):
    return os.path.join(USER_DATA_DIR, f"{username}.json")

def load_user_verses(username):
    filepath = get_user_file(username)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return {}

def save_user_verses(username, data):
    filepath = get_user_file(username)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# Setup
st.set_page_config(layout="wide")
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Login
st.sidebar.title("🔐 Login")
username = st.sidebar.text_input("Benutzername", value="benjamin")

if not username.strip():
    st.stop()

users = load_users()
if username not in users:
    users[username] = {"points": 0}
    save_users(users)

user_points = users[username]["points"]
st.sidebar.markdown(f"**🏆 Punkte: {user_points}**")

# Texte laden
user_verses = load_user_verses(username)

# Bibeltext hinzufügen
st.sidebar.markdown("### 📥 Eigener Bibeltext")
new_title = st.sidebar.text_input("Titel des Bibeltexts")
new_text = st.sidebar.text_area("Text im Format `1) Eph. 1:1 ...`")

if st.sidebar.button("📌 Speichern"):
    parsed = parse_verses_from_text(new_text)
    if parsed:
        user_verses[new_title] = {
            "verses": parsed,
            "mode": "reihenfolge",  # default
            "last_index": 0
        }
        save_user_verses(username, user_verses)
        st.sidebar.success("Text gespeichert!")

# Textauswahl
st.title("📖 Vers-Lern-App")
if not user_verses:
    st.warning("Bitte erst einen Bibeltext hinzufügen.")
    st.stop()

text_title = st.selectbox("📚 Wähle deinen Bibeltext", list(user_verses.keys()))
mode = st.radio("Lernmodus", ["der Reihe nach", "zufällig"], horizontal=True)

# Modus speichern
user_verses[text_title]["mode"] = "random" if mode == "zufällig" else "reihenfolge"
save_user_verses(username, user_verses)

# Aktueller Vers
verses = user_verses[text_title]["verses"]
if user_verses[text_title]["mode"] == "reihenfolge":
    idx = user_verses[text_title].get("last_index", 0)
else:
    idx = random.randint(0, len(verses) - 1)

current_verse = verses[idx]
tokens = current_verse["text"].split()

# Shuffle-Setup
if "shuffled" not in st.session_state or st.session_state.get("current_ref") != current_verse["ref"]:
    st.session_state.shuffled = random.sample(tokens, len(tokens))
    st.session_state.selected = []
    st.session_state.used = [False] * len(tokens)
    st.session_state.feedback_given = False
    st.session_state.current_ref = current_verse["ref"]

st.markdown(f"### 📌 {current_verse['ref']}")
st.markdown("🔡 Wähle die Wörter in der richtigen Reihenfolge:")

cols = st.columns(len(tokens))
for i, word in enumerate(st.session_state.shuffled):
    if st.session_state.used[i]:
        cols[i].button("✅", key=f"done_{i}", disabled=True)
    else:
        if cols[i].button(word, key=f"btn_{i}"):
            st.session_state.selected.append(word)
            st.session_state.used[i] = True
            st.rerun()

# Feedback
if st.session_state.selected:
    user_input = " ".join(st.session_state.selected)
    correct = " ".join(tokens)

    if user_input == correct and not st.session_state.feedback_given:
        st.success("✅ Richtig!")
        users[username]["points"] += len(tokens)
        save_users(users)
        st.markdown(f"<div style='background-color:#0f0;color:#000;padding:10px;border-radius:10px'>{user_input}</div>", unsafe_allow_html=True)
        st.session_state.feedback_given = True
    elif len(st.session_state.selected) == len(tokens):
        st.error("❌ Leider falsch.")
        st.markdown(f"<div style='background-color:#f88;color:#000;padding:10px;border-radius:10px'>{user_input}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='background-color:#afa;color:#000;padding:10px;border-radius:10px'><b>Korrekt:</b> {correct}</div>", unsafe_allow_html=True)
        st.session_state.feedback_given = True

# Weiter
if st.session_state.feedback_given and st.button("➡️ Nächster Vers"):
    if user_verses[text_title]["mode"] == "reihenfolge":
        user_verses[text_title]["last_index"] = (idx + 1) % len(verses)
        save_user_verses(username, user_verses)
    st.session_state.current_ref = None
    st.rerun()
