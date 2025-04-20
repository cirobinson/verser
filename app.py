import streamlit as st
import os
import json
import random
import math
from verses import parse_verses_from_text # Stelle sicher, dass diese Datei existiert und funktioniert

USER_DATA_DIR = "user_data"
USERS_FILE = "users.json"
MAX_CHUNKS = 9 # Maximale Anzahl an Textbausteinen
COLS_PER_ROW = 4 # Wie viele Bausteine pro Zeile angezeigt werden sollen

# --- Hilfsfunktionen ---
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {} # Leeres Dict bei fehlerhafter Datei
    return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def get_user_file(username):
    # Bereinige den Benutzernamen für Dateisystemkompatibilität (optional, aber empfohlen)
    safe_username = "".join(c for c in username if c.isalnum() or c in ('_', '-')).rstrip()
    if not safe_username:
        safe_username = "default_user" # Fallback
    return os.path.join(USER_DATA_DIR, f"{safe_username}.json")


def load_user_verses(username):
    filepath = get_user_file(username)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
             return {} # Leeres Dict bei fehlerhafter Datei
    return {}

def save_user_verses(username, data):
    filepath = get_user_file(username)
    try:
        with open(filepath, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        st.error(f"Fehler beim Speichern der Verse für {username}: {e}")


def group_words_into_chunks(words, max_chunks=MAX_CHUNKS):
    """ Fasst eine Liste von Wörtern in maximal max_chunks zusammen."""
    n_words = len(words)
    if n_words == 0:
        return []
    
    # Bestimme die tatsächliche Anzahl der Chunks (maximal max_chunks)
    num_chunks = min(n_words, max_chunks)

    # Berechne die Basisgröße jedes Chunks und den Rest
    base_chunk_size = n_words // num_chunks
    remainder = n_words % num_chunks

    chunks = []
    current_index = 0
    for i in range(num_chunks):
        # Die ersten 'remainder' Chunks bekommen ein Wort extra
        chunk_size = base_chunk_size + (1 if i < remainder else 0)
        chunk_words = words[current_index : current_index + chunk_size]
        chunks.append(" ".join(chunk_words))
        current_index += chunk_size
        
    return chunks

# --- Setup ---
st.set_page_config(layout="wide")
os.makedirs(USER_DATA_DIR, exist_ok=True)

# --- Login ---
st.sidebar.title("🔐 Login")
# Verwende Session State für den Benutzernamen, um ihn über Reruns zu erhalten
if 'username' not in st.session_state:
    st.session_state.username = "benjamin" # Default

username_input = st.sidebar.text_input("Benutzername", value=st.session_state.username)

# Aktualisiere den Benutzernamen nur, wenn er sich geändert hat
if username_input != st.session_state.username:
    st.session_state.username = username_input
    # Lösche alte Vers-bezogene Session-State-Variablen bei Benutzerwechsel
    keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data"]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun() # Führe die App neu aus, um Daten für den neuen Benutzer zu laden


username = st.session_state.username.strip()

if not username:
    st.warning("Bitte gib einen Benutzernamen ein.")
    st.stop()

users = load_users()
if username not in users:
    users[username] = {"points": 0}
    save_users(users)

user_points = users[username].get("points", 0) # Sicherer Zugriff
st.sidebar.markdown(f"**🏆 Punkte: {user_points}**")

# --- Texte laden ---
user_verses = load_user_verses(username)

# --- Bibeltext hinzufügen ---
st.sidebar.markdown("### 📥 Eigener Bibeltext")
# Verwende eindeutige Keys für die Eingabefelder
new_title = st.sidebar.text_input("Titel des Bibeltexts", key="new_title_input")
new_text = st.sidebar.text_area("Text im Format `1) Eph. 1:1 ...`", key="new_text_input")

if st.sidebar.button("📌 Speichern", key="save_new_text"):
    if not new_title.strip():
        st.sidebar.error("Bitte gib einen Titel ein.")
    elif not new_text.strip():
        st.sidebar.error("Bitte gib einen Text ein.")
    else:
        try:
            # Stelle sicher, dass parse_verses_from_text existiert und funktioniert
            parsed = parse_verses_from_text(new_text)
            if parsed:
                user_verses[new_title] = {
                    "verses": parsed,
                    "mode": "reihenfolge",  # default
                    "last_index": 0
                }
                save_user_verses(username, user_verses)
                st.sidebar.success(f"Text '{new_title}' gespeichert!")
                # Optional: Felder leeren nach Speichern
                # st.session_state.new_title_input = ""
                # st.session_state.new_text_input = ""
                st.rerun() # Neu laden, damit der neue Text in der Auswahl erscheint
            else:
                st.sidebar.error("Text konnte nicht verarbeitet werden. Prüfe das Format.")
        except NameError:
             st.sidebar.error("Fehler: Die Funktion 'parse_verses_from_text' ist nicht definiert.")
        except Exception as e:
            st.sidebar.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}")


# --- Textauswahl ---
st.title("📖 Vers-Lern-App")
if not user_verses:
    st.warning("Bitte füge zuerst einen Bibeltext im Menü links hinzu.")
    st.stop()

# Verwende Session State, um die Auswahl zu speichern
if 'selected_title' not in st.session_state or st.session_state.selected_title not in user_verses:
     st.session_state.selected_title = list(user_verses.keys())[0] # Wähle den ersten Text als Default

selected_title = st.selectbox(
    "📚 Wähle deinen Bibeltext",
    list(user_verses.keys()),
    index=list(user_verses.keys()).index(st.session_state.selected_title) # Setze den Index basierend auf dem gespeicherten Titel
)

# Wenn sich der Titel ändert, aktualisiere den Session State und setze Vers-spezifische Zustände zurück
if selected_title != st.session_state.selected_title:
    st.session_state.selected_title = selected_title
    keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data"]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

text_title = st.session_state.selected_title
current_text_data = user_verses[text_title]

# Verwende Session State für den Modus, um Auswahl zu speichern
mode_options = ["der Reihe nach", "zufällig"]
default_mode = current_text_data.get("mode", "reihenfolge")
# Konvertiere gespeicherten Modus ('reihenfolge'/'random') in Anzeigeoption
current_mode_display = "zufällig" if default_mode == "random" else "der Reihe nach"
if 'selected_mode' not in st.session_state:
    st.session_state.selected_mode = current_mode_display

selected_mode_display = st.radio(
    "Lernmodus",
    mode_options,
    index=mode_options.index(st.session_state.selected_mode),
    horizontal=True,
    key=f"mode_radio_{text_title}" # Eindeutiger Key pro Text
)

# Aktualisiere Modus im Session State und speichere ihn, wenn er sich ändert
if selected_mode_display != st.session_state.selected_mode:
    st.session_state.selected_mode = selected_mode_display
    new_mode_internal = "random" if selected_mode_display == "zufällig" else "reihenfolge"
    if current_text_data["mode"] != new_mode_internal:
        current_text_data["mode"] = new_mode_internal
        save_user_verses(username, user_verses)
        # Setze Vers-spezifische Zustände zurück bei Moduswechsel
        keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data"]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

mode = current_text_data["mode"]
verses = current_text_data["verses"]

if not verses:
    st.warning(f"Der Text '{text_title}' enthält keine Verse.")
    st.stop()

# --- Aktueller Vers bestimmen ---
# Logik, um den aktuellen Vers basierend auf Modus und Index zu finden
if mode == "reihenfolge":
    # Stelle sicher, dass last_index gültig ist
    last_idx = current_text_data.get("last_index", 0)
    idx = last_idx if 0 <= last_idx < len(verses) else 0
    if "current_verse_index" not in st.session_state or st.session_state.current_verse_index != idx:
         st.session_state.current_verse_index = idx
         # Setze Vers-spezifische Zustände zurück, wenn sich der Index ändert
         keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data"]
         for key in keys_to_delete:
             if key in st.session_state:
                 del st.session_state[key]

elif mode == "random":
    # Wähle nur dann einen neuen zufälligen Index, wenn keiner im Session State ist
    if "current_verse_index" not in st.session_state:
        st.session_state.current_verse_index = random.randint(0, len(verses) - 1)
        # Setze Vers-spezifische Zustände zurück
        keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data"]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
    idx = st.session_state.current_verse_index
else: # Fallback
    idx = 0
    st.session_state.current_verse_index = idx

# Stelle sicher, dass der Index gültig ist
if not (0 <= idx < len(verses)):
    st.error("Ungültiger Vers-Index. Setze auf den ersten Vers zurück.")
    idx = 0
    st.session_state.current_verse_index = idx
    current_text_data["last_index"] = 0 # Korrigiere auch gespeicherten Index
    save_user_verses(username, user_verses)
     # Setze Vers-spezifische Zustände zurück
    keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data"]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


current_verse = verses[idx]
tokens = current_verse["text"].split()
original_chunks = group_words_into_chunks(tokens, MAX_CHUNKS)
num_chunks = len(original_chunks)

# --- Shuffle-Setup für Textbausteine ---
# Initialisiere, wenn noch nicht geschehen oder wenn sich der Vers geändert hat
# Verwende die Vers-Referenz als Indikator für einen Verswechsel
if "shuffled_chunks" not in st.session_state or st.session_state.get("current_ref") != current_verse["ref"]:
    st.session_state.shuffled_chunks = random.sample(original_chunks, num_chunks)
    st.session_state.selected_chunks = [] # Speichert die ausgewählten Bausteine
    st.session_state.used_chunks = [False] * num_chunks # Verfolgt, welche Buttons (Bausteine) geklickt wurden
    st.session_state.feedback_given = False
    st.session_state.current_ref = current_verse["ref"]
    # Speichere auch die Originaldaten des aktuellen Verses im State
    st.session_state.current_verse_data = {
        "ref": current_verse["ref"],
        "text": current_verse["text"],
        "original_chunks": original_chunks,
        "tokens": tokens # Speichere auch die Originalwörter für die Punkte
    }


# --- Anzeige der Baustein-Buttons ---
st.markdown(f"### 📌 {st.session_state.current_verse_data['ref']}")
st.markdown("🧩 Wähle die Textbausteine in der richtigen Reihenfolge:")

# Berechne Zeilen und Spalten für die Anzeige
num_rows = math.ceil(num_chunks / COLS_PER_ROW)
button_index = 0

for r in range(num_rows):
    cols = st.columns(COLS_PER_ROW)
    for c in range(COLS_PER_ROW):
        if button_index < num_chunks:
            chunk_display_index = button_index # Index in der gemischten Liste
            chunk_text = st.session_state.shuffled_chunks[chunk_display_index]
            
            # Verwende den Index in der *gemischten* Liste, um den 'used' Status zu prüfen/setzen
            is_used = st.session_state.used_chunks[chunk_display_index]
            button_key = f"chunk_btn_{chunk_display_index}_{st.session_state.current_ref}" # Eindeutiger Key pro Button & Vers

            if is_used:
                # Zeige den Button als deaktiviert an, eventuell mit anderem Stil
                 with cols[c]: # Platziere im richtigen Spaltencontainer
                    st.button(f"~~{chunk_text}~~", key=button_key, disabled=True, use_container_width=True)
            else:
                 with cols[c]: # Platziere im richtigen Spaltencontainer
                    if st.button(chunk_text, key=button_key, use_container_width=True):
                        st.session_state.selected_chunks.append(chunk_text)
                        st.session_state.used_chunks[chunk_display_index] = True
                        # Prüfe, ob das der letzte Baustein war
                        if len(st.session_state.selected_chunks) == num_chunks:
                             # Verzögere Feedback nicht, setze es hier direkt
                             user_input = " ".join(st.session_state.selected_chunks)
                             correct_text = st.session_state.current_verse_data["text"]
                             if user_input == correct_text:
                                 # Positive Feedback Logik hier einfügen wenn nötig oder im Feedback Block lassen
                                 pass
                             else:
                                 # Negative Feedback Logik hier einfügen wenn nötig oder im Feedback Block lassen
                                 pass
                             st.session_state.feedback_given = True # Feedback kann jetzt angezeigt werden

                        st.rerun() # Wichtig: Neu zeichnen nach Klick
            
            button_index += 1
        else:
            # Fülle leere Spalten in der letzten Zeile (optional)
            # cols[c].empty() # Oder lasse sie einfach leer
            pass

# Platzhalter für ausgewählten Text (wird unten im Feedback-Block angezeigt)
st.markdown("---") # Trennlinie
st.markdown("**Deine Auswahl:**")
if st.session_state.selected_chunks:
    # Zeige ausgewählte Chunks formatiert an
    display_text = " ".join(st.session_state.selected_chunks)
    st.markdown(f"`{display_text}`")
else:
    st.markdown("*Noch keine Bausteine ausgewählt.*")
st.markdown("---") # Trennlinie


# --- Feedback ---
# Dieser Block wird nur ausgeführt, wenn Feedback gegeben werden soll (alle Chunks ausgewählt)
if st.session_state.feedback_given:
    user_input = " ".join(st.session_state.selected_chunks)
    correct_text = st.session_state.current_verse_data["text"]
    original_tokens_count = len(st.session_state.current_verse_data["tokens"]) # Für Punkte

    if user_input == correct_text:
        st.success("✅ Richtig!")
        # Punkte nur einmalig pro korrektem Vers geben
        if not st.session_state.get("points_awarded_for_current_verse", False):
             users[username]["points"] = users[username].get("points", 0) + original_tokens_count
             save_users(users)
             st.session_state.points_awarded_for_current_verse = True # Markieren, dass Punkte vergeben wurden
             st.balloons() # Kleine Belohnung

        # Zeige den korrekten Text grün hinterlegt
        st.markdown(f"<div style='background-color:#e6ffed; color:#094d21; padding:10px; border-radius:5px; border: 1px solid #b3e6c5;'><b>Richtig:</b> {correct_text}</div>", unsafe_allow_html=True)

    else:
         st.error("❌ Leider falsch.")
         # Zeige die falsche Eingabe rot hinterlegt
         st.markdown(f"<div style='background-color:#ffebeb; color:#8b0000; padding:10px; border-radius:5px; border: 1px solid #f5c6cb;'><b>Deine Eingabe:</b> {user_input}</div>", unsafe_allow_html=True)
         # Zeige die korrekte Lösung grün hinterlegt
         st.markdown(f"<div style='background-color:#e6ffed; color:#094d21; padding:10px; border-radius:5px; border: 1px solid #b3e6c5; margin-top: 5px;'><b>Korrekt wäre:</b> {correct_text}</div>", unsafe_allow_html=True)
         st.session_state.points_awarded_for_current_verse = False # Keine Punkte bei falscher Antwort

    # --- Weiter Button ---
    if st.button("➡️ Nächster Vers", key="next_verse_button"):
        if mode == "reihenfolge":
            # Berechne nächsten Index und speichere ihn
            next_idx = (st.session_state.current_verse_index + 1) % len(verses)
            current_text_data["last_index"] = next_idx
            save_user_verses(username, user_verses)
        
        # Lösche alle Zustände, die sich auf den *aktuellen* Vers beziehen, für den nächsten Durchlauf
        keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"]
        # Im Zufallsmodus auch den Index löschen, damit ein neuer gewählt wird
        if mode == "random":
            keys_to_delete.append("current_verse_index")
            
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun() # Starte den Prozess für den nächsten Vers