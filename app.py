import streamlit as st
import os
import json
import random
import math
import bcrypt
import re # Importiere das Regex-Modul für die Formatprüfung
from verses import parse_verses_from_text # Stelle sicher, dass diese Datei existiert

# --- Konstanten ---
USER_DATA_DIR = "user_data"
USERS_FILE = os.path.join(USER_DATA_DIR, "users.json")
PUBLIC_VERSES_FILE = os.path.join(USER_DATA_DIR, "public_verses.json") # Datei für öffentliche Verse
MAX_CHUNKS = 8
COLS_PER_ROW = 4
LEADERBOARD_SIZE = 10
BIBLE_FORMAT_HELP_URL = "https://bible.benkelm.de/frames.htm?listv.htm"

# --- Hilfsfunktionen ---

os.makedirs(USER_DATA_DIR, exist_ok=True)

# --- Passwort-Funktionen (unverändert) ---
def hash_password(password):
    pw_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode('utf-8')

def verify_password(stored_hash, provided_password):
    stored_hash_bytes = stored_hash.encode('utf-8')
    provided_password_bytes = provided_password.encode('utf-8')
    try:
        return bcrypt.checkpw(provided_password_bytes, stored_hash_bytes)
    except ValueError: # Kann bei ungültigem Hash auftreten
        return False

# --- Benutzer Laden/Speichern (unverändert) ---
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                for user, details in data.items():
                    if 'points' not in details or not isinstance(details['points'], (int, float)):
                        data[user]['points'] = 0
                    if 'password_hash' not in details:
                        # Markiere User ohne Hash eventuell, statt stillschweigend zu ignorieren
                        # Hier ggf. eine Migration oder Fehlerbehandlung einfügen
                        pass
                return data
        except (json.JSONDecodeError, IOError):
            st.error("Benutzerdatei konnte nicht gelesen werden.")
            return {}
    return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except IOError:
        st.error("Fehler beim Speichern der Benutzerdaten.")

# --- Verse Laden/Speichern (Anpassungen für Public/Private) ---
def get_user_verse_file(username):
    safe_username = "".join(c for c in username if c.isalnum() or c in ('_', '-')).rstrip()
    if not safe_username:
        safe_username = f"user_{random.randint(1000, 9999)}"
    return os.path.join(USER_DATA_DIR, f"{safe_username}_verses.json")

def load_user_verses(username):
    """Lädt die privaten Verse eines Benutzers."""
    filepath = get_user_verse_file(username)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding='utf-8') as f:
                # Filtere hier nur die, die NICHT public sind (obwohl public eig. nur in public_verses.json sein sollten)
                # Sicherer ist, anzunehmen, dass alles in dieser Datei privat ist
                data = json.load(f)
                # Füge 'public': False hinzu, falls es fehlt (für Abwärtskompatibilität)
                for title, details in data.items():
                    if 'public' not in details:
                        details['public'] = False
                return data

        except (json.JSONDecodeError, IOError):
             st.warning(f"Private Versdatei für {username} konnte nicht gelesen werden.")
             return {}
    return {}

def save_user_verses(username, data):
    """Speichert die privaten Verse eines Benutzers."""
    filepath = get_user_verse_file(username)
    try:
        with open(filepath, "w", encoding='utf-8') as f:
            # Stelle sicher, dass nur private Texte gespeichert werden
            private_data = {title: details for title, details in data.items() if not details.get('public', False)}
            json.dump(private_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        st.error(f"Fehler beim Speichern der privaten Verse für {username}: {e}")

def load_public_verses():
    """Lädt alle öffentlichen Verse."""
    if os.path.exists(PUBLIC_VERSES_FILE):
        try:
            with open(PUBLIC_VERSES_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                 # Stelle sicher, dass 'public': True gesetzt ist
                for title, details in data.items():
                    details['public'] = True # Sicherstellen, dass Flag korrekt ist
                return data
        except (json.JSONDecodeError, IOError):
            st.warning("Öffentliche Versdatei konnte nicht gelesen werden.")
            return {}
    return {}

def save_public_verses(data):
    """Speichert alle öffentlichen Verse."""
    try:
        with open(PUBLIC_VERSES_FILE, "w", encoding='utf-8') as f:
             # Stelle sicher, dass nur als public markierte Texte gespeichert werden
             public_data = {title: details for title, details in data.items() if details.get('public', False)}
             json.dump(public_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        st.error(f"Fehler beim Speichern der öffentlichen Verse: {e}")

# --- Formatprüfungsfunktion ---
def is_format_likely_correct(text):
    """Prüft, ob der Text wahrscheinlich dem Format 'Zahl) Ref ...' entspricht."""
    if not text or not isinstance(text, str):
        return False
    lines = text.strip().split('\n')
    if not lines:
        return False
    # Prüfe, ob die erste Zeile dem Muster entspricht (sehr einfache Prüfung)
    # Eine robustere Prüfung würde Regex verwenden, z.B. auf jede Zeile
    # Regex: ^\s*\d+\)\s+\w+\.?\s*\d+[:.]\d+.*
    first_line = lines[0].strip()
    # Einfache Prüfung: Beginnt mit Zahl und Klammer zu?
    match = re.match(r"^\s*\d+\)\s+", first_line)
    return match is not None

# --- Textbausteine-Funktion (unverändert) ---
def group_words_into_chunks(words, max_chunks=MAX_CHUNKS):
    n_words = len(words)
    if n_words == 0: return []
    num_chunks = min(n_words, max_chunks)
    base_chunk_size = n_words // num_chunks
    remainder = n_words % num_chunks
    chunks = []
    current_index = 0
    for i in range(num_chunks):
        chunk_size = base_chunk_size + (1 if i < remainder else 0)
        chunk_words = words[current_index : current_index + chunk_size]
        chunks.append(" ".join(chunk_words))
        current_index += chunk_size
    return chunks

# --- Leaderboard Anzeige (unverändert) ---
def display_leaderboard(users):
    st.markdown("---")
    st.subheader("🏆 Leaderboard")
    if not users:
        st.write("Noch keine Benutzer registriert.")
        return
    sorted_users = sorted(
        users.items(),
        key=lambda item: item[1].get('points', 0) if isinstance(item[1].get('points'), (int, float)) else 0,
        reverse=True
    )
    for i, (username, data) in enumerate(sorted_users[:LEADERBOARD_SIZE]):
        points = data.get('points', 0)
        st.markdown(f"{i+1}. **{username}**: {points} Punkte")

# --- App Setup ---
st.set_page_config(layout="wide")

# --- Session State Initialisierung (unverändert) ---
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None
if "login_error" not in st.session_state: st.session_state.login_error = None
if "register_error" not in st.session_state: st.session_state.register_error = None

# --- Login / Registrierung / Logout in der Sidebar (unverändert) ---
users = load_users()

if st.session_state.logged_in_user:
    # --- Ansicht für eingeloggte Benutzer ---
    st.sidebar.success(f"Angemeldet als: **{st.session_state.logged_in_user}**")
    user_points = users.get(st.session_state.logged_in_user, {}).get("points", 0)
    st.sidebar.markdown(f"**🏆 Deine Punkte: {user_points}**")

    if st.sidebar.button("🔒 Logout"):
        keys_to_clear = list(st.session_state.keys())
        for key in keys_to_clear:
            if key not in []: del st.session_state[key]
        st.session_state.logged_in_user = None
        st.rerun()

    # --- Hauptanwendung (nur wenn eingeloggt) ---
    username = st.session_state.logged_in_user

    # --- Layout mit Leaderboard ---
    main_col, leaderboard_col = st.columns([3, 1])

    with leaderboard_col:
        display_leaderboard(users)

    with main_col:
        st.title("📖 Vers-Lern-App")

        # --- Texte laden (Privat + Öffentlich) ---
        user_verses_private = load_user_verses(username)
        public_verses = load_public_verses()

        # Kombiniere die Texte für die Auswahl
        available_texts = {}
        # Füge private Texte hinzu (ohne Präfix)
        for title, data in user_verses_private.items():
            # Stelle sicher, dass nur wirklich private hier landen
             if not data.get('public', False):
                 available_texts[title] = {**data, 'source': 'private'}

        # Füge öffentliche Texte hinzu (mit Präfix)
        public_prefix = "[Ö] "
        for title, data in public_verses.items():
             display_title = f"{public_prefix}{title}"
             # Füge nur hinzu, wenn nicht schon ein privater Text gleichen Namens (ohne Prefix) existiert
             # Oder entscheide, ob öffentliche immer Vorrang haben oder angezeigt werden sollen
             # Hier: Zeige beide an, der User wählt über den Titel mit/ohne Prefix
             available_texts[display_title] = {**data, 'source': 'public', 'original_title': title}


        # --- Text hinzufügen (mit Formatprüfung & Public/Private Option) ---
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📥 Eigener Bibeltext")
        new_title = st.sidebar.text_input("Titel des Bibeltexts", key="new_title_input").strip()
        new_text = st.sidebar.text_area("Text im Format `1) Eph. 1:1 ...`", key="new_text_input").strip()
        # Checkbox für öffentliche Freigabe
        share_publicly = st.sidebar.checkbox("Für alle Benutzer freigeben (öffentlich)", key="share_text_checkbox", value=False)

        if st.sidebar.button("📌 Speichern", key="save_new_text"):
            if not new_title:
                st.sidebar.error("Bitte gib einen Titel ein.")
            elif not new_text:
                st.sidebar.error("Bitte gib einen Text ein.")
            # Formatprüfung HINZUGEFÜGT
            elif not is_format_likely_correct(new_text):
                 error_message = (
                    f"Das Format des Textes scheint nicht korrekt zu sein.\n"
                    f"Erwarte Zeilen wie `1) Eph. 1:1 ...`.\n"
                    f"[Hilfe zur Formatierung]({BIBLE_FORMAT_HELP_URL})"
                )
                 st.sidebar.error(error_message)
            else:
                # Format scheint OK, versuche zu parsen
                try:
                    parsed = parse_verses_from_text(new_text)
                    if parsed:
                        # Entscheiden, wo gespeichert wird (Öffentlich / Privat)
                        if share_publicly:
                            # --- Öffentlichen Text speichern ---
                            current_public_verses = load_public_verses()
                            if new_title in current_public_verses:
                                st.sidebar.error(f"Ein öffentlicher Text mit dem Titel '{new_title}' existiert bereits.")
                            else:
                                current_public_verses[new_title] = {
                                    "verses": parsed,
                                    "public": True, # Wichtiges Flag
                                    "added_by": username # Urheber speichern
                                    # Kein Modus / last_index für öffentliche Texte
                                }
                                save_public_verses(current_public_verses)
                                st.sidebar.success(f"Öffentlicher Text '{new_title}' gespeichert!")
                                st.rerun() # Neu laden, um Auswahl zu aktualisieren
                        else:
                            # --- Privaten Text speichern ---
                            current_user_verses = load_user_verses(username) # Lade aktuelle private Texte
                            if new_title in current_user_verses:
                                # Optional: Überschreiben erlauben oder Fehler anzeigen
                                st.sidebar.warning(f"Privater Text '{new_title}' wird überschrieben.")

                            current_user_verses[new_title] = {
                                "verses": parsed,
                                "mode": "reihenfolge", # Default für neue Texte
                                "last_index": 0,
                                "public": False # Wichtiges Flag
                            }
                            save_user_verses(username, current_user_verses) # Speichere die gesamte (aktualisierte) Liste
                            st.sidebar.success(f"Privater Text '{new_title}' gespeichert!")
                            st.rerun() # Neu laden, um Auswahl zu aktualisieren
                    else:
                        # parser hat None oder leere Liste zurückgegeben
                        st.sidebar.error("Text konnte nicht verarbeitet werden (Parser-Problem). Prüfe das Format erneut.")

                except NameError:
                    st.sidebar.error("Fehler: 'parse_verses_from_text' nicht gefunden.")
                except Exception as e:
                    st.sidebar.error(f"Unerwarteter Fehler beim Parsen/Speichern: {e}")

        # --- Textauswahl (jetzt mit kombinierten Texten) ---
        if not available_texts:
            st.warning("Keine Texte verfügbar. Füge zuerst einen Bibeltext im Menü links hinzu.")
        else:
            # Sortiere die Schlüssel (Titel) für eine konsistente Reihenfolge im Dropdown
            sorted_titles = sorted(available_texts.keys())

            # Setze Default-Auswahl oder behalte letzte Auswahl bei
            if 'selected_display_title' not in st.session_state or st.session_state.selected_display_title not in available_texts:
                 st.session_state.selected_display_title = sorted_titles[0] # Ersten als Default

            selected_display_title = st.selectbox(
                "📚 Wähle deinen Bibeltext",
                sorted_titles,
                index=sorted_titles.index(st.session_state.selected_display_title),
                key=f"selectbox_{username}_combined"
            )

            # Wenn sich die Auswahl ändert
            if selected_display_title != st.session_state.selected_display_title:
                st.session_state.selected_display_title = selected_display_title
                # Reset verse-specific state
                keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "current_verse_index", "points_awarded_for_current_verse"]
                for key in keys_to_delete:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()

            # Hole die Daten für den ausgewählten Text aus dem kombinierten Dictionary
            selected_text_info = available_texts[selected_display_title]
            is_public_text = selected_text_info['source'] == 'public'
            # Der tatsächliche Titel (ohne Prefix für öffentliche)
            actual_title = selected_text_info.get('original_title', selected_display_title)

            # Lade die Vers-Daten
            # 'current_text_data' enthält nun die Kerninfos wie {"verses": [...]}
            # Bei öffentlichen Texten fehlen Mode/LastIndex, das ist OK.
            current_text_data = selected_text_info

            # --- Lernmodus (wird bei öffentlichen Texten nicht persistent gespeichert) ---
            mode_options = ["der Reihe nach", "zufällig"]
            # Lese Modus aus Daten WENN privat, sonst Default
            default_mode_internal = "reihenfolge" # Default auch für öffentliche
            if not is_public_text:
                default_mode_internal = current_text_data.get("mode", "reihenfolge")

            current_mode_display = "zufällig" if default_mode_internal == "random" else "der Reihe nach"

            # Initialisiere Modus im State wenn nötig, basierend auf Texttyp
            session_mode_key = f"selected_mode_{selected_display_title}" # Eindeutiger Key pro Text im State
            if session_mode_key not in st.session_state:
                 st.session_state[session_mode_key] = current_mode_display

            selected_mode_display = st.radio(
                "Lernmodus",
                mode_options,
                index=mode_options.index(st.session_state[session_mode_key]),
                horizontal=True,
                key=f"mode_radio_{username}_{selected_display_title}" # Eindeutiger Key
            )

            # Speichere Modusänderung (nur für private Texte persistent)
            if selected_mode_display != st.session_state[session_mode_key]:
                 st.session_state[session_mode_key] = selected_mode_display
                 new_mode_internal = "random" if selected_mode_display == "zufällig" else "reihenfolge"

                 if not is_public_text:
                     # Nur bei privaten Texten in Datei speichern
                     private_text_data = load_user_verses(username) # Lade User-Daten erneut
                     if actual_title in private_text_data:
                         private_text_data[actual_title]["mode"] = new_mode_internal
                         save_user_verses(username, private_text_data) # Speichere Änderungen
                     else:
                          st.warning(f"Konnte privaten Text '{actual_title}' zum Speichern des Modus nicht finden.")

                 # Reset verse state on mode change regardless of public/private
                 keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "current_verse_index", "points_awarded_for_current_verse"]
                 for key in keys_to_delete:
                     if key in st.session_state: del st.session_state[key]
                 st.rerun()

            # Aktueller Modus für die Logik (aus Session State oder Default)
            mode = "random" if st.session_state[session_mode_key] == "zufällig" else "reihenfolge"
            verses = current_text_data.get("verses", [])

            # --- Restliche Logik (Aktueller Vers, Shuffle, Anzeige, Feedback, Nächster Vers) ---
            # Diese Logik sollte weitgehend funktionieren, da sie `current_text_data` (mit `verses`)
            # und den dynamischen `mode` verwendet.
            # WICHTIG: Beim "Nächster Vers"-Button darf `last_index` nur für private Texte gespeichert werden.

            if not verses:
                st.warning(f"Der Text '{actual_title}' enthält keine Verse.")
            else:
                # --- Aktueller Vers Logik ---
                verse_determined = False
                current_verse_index_key = f"current_verse_index_{selected_display_title}" # Eindeutiger Index-Key

                if mode == "reihenfolge":
                    last_idx = 0 # Default
                    if not is_public_text:
                         # Nur bei privaten Texten aus Datei lesen
                         private_data = load_user_verses(username)
                         last_idx = private_data.get(actual_title, {}).get("last_index", 0)

                    # Verwende Index aus Session State, falls vorhanden, sonst last_idx
                    idx = st.session_state.get(current_verse_index_key, last_idx)
                    idx = idx if 0 <= idx < len(verses) else 0 # Sicherstellen, dass Index gültig ist

                    # Wenn sich Index ändert (oder initial gesetzt wird), State zurücksetzen
                    if st.session_state.get(current_verse_index_key) != idx:
                        st.session_state[current_verse_index_key] = idx
                        keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"]
                        for key in keys_to_delete:
                            if key in st.session_state: del st.session_state[key]
                    verse_determined = True

                elif mode == "random":
                    # Wähle nur neuen Index, wenn Key nicht im State oder Ref sich geändert hat
                    if current_verse_index_key not in st.session_state or st.session_state.get("current_ref") is None:
                        st.session_state[current_verse_index_key] = random.randint(0, len(verses) - 1)
                        keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"]
                        for key in keys_to_delete:
                             if key in st.session_state: del st.session_state[key]
                    idx = st.session_state[current_verse_index_key]
                    verse_determined = True

                # Fallback / Validierung
                if not verse_determined or not (0 <= idx < len(verses)):
                    st.warning("Konnte Vers nicht bestimmen, setze auf Anfang.")
                    idx = 0
                    st.session_state[current_verse_index_key] = idx
                    if not is_public_text: # Nur bei privaten Texten Index speichern
                        private_data = load_user_verses(username)
                        if actual_title in private_data:
                            private_data[actual_title]["last_index"] = 0
                            save_user_verses(username, private_data)
                    keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"]
                    for key in keys_to_delete:
                        if key in st.session_state: del st.session_state[key]
                    st.rerun()


                current_verse = verses[idx]
                tokens = current_verse.get("text", "").split()
                original_chunks = group_words_into_chunks(tokens, MAX_CHUNKS)
                num_chunks = len(original_chunks)

                # --- Leere Verse Behandlung (unverändert) ---
                if not tokens or not original_chunks:
                     st.warning(f"Vers {current_verse.get('ref', '')} scheint leer zu sein.")
                     if st.button("➡️ Diesen leeren Vers überspringen"):
                         if mode == "reihenfolge":
                             next_idx = (idx + 1) % len(verses)
                             st.session_state[current_verse_index_key] = next_idx # Update im Session State
                             if not is_public_text: # Nur bei privaten Texten persistieren
                                  private_data = load_user_verses(username)
                                  if actual_title in private_data:
                                      private_data[actual_title]["last_index"] = next_idx
                                      save_user_verses(username, private_data)
                         # Reset state for next verse
                         keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"]
                         if mode == "random": # Im Zufallsmodus Index löschen für neue Wahl
                              if current_verse_index_key in st.session_state: del st.session_state[current_verse_index_key]
                         for key in keys_to_delete:
                              if key in st.session_state: del st.session_state[key]
                         st.rerun()
                else:
                    # --- Shuffle & State Setup (unverändert, verwendet current_verse["ref"]) ---
                    if "shuffled_chunks" not in st.session_state or st.session_state.get("current_ref") != current_verse["ref"]:
                        # ... (Restliche State-Initialisierung wie zuvor) ...
                        st.session_state.shuffled_chunks = random.sample(original_chunks, num_chunks)
                        st.session_state.selected_chunks = []
                        st.session_state.used_chunks = [False] * num_chunks
                        st.session_state.feedback_given = False
                        st.session_state.current_ref = current_verse["ref"] # Wichtig für Key-Generierung
                        st.session_state.current_verse_data = {
                            "ref": current_verse["ref"],
                            "text": current_verse["text"],
                            "original_chunks": original_chunks,
                            "tokens": tokens
                        }
                        st.session_state.points_awarded_for_current_verse = False

                    # --- Anzeige Buttons (unverändert, verwendet current_ref für Keys) ---
                    st.markdown(f"### 📌 {st.session_state.current_verse_data['ref']}")
                    st.markdown(f"🧩 Wähle die Textbausteine in der richtigen Reihenfolge:")
                    # ... (Button-Logik wie zuvor) ...
                    num_rows = math.ceil(num_chunks / COLS_PER_ROW)
                    button_index = 0
                    for r in range(num_rows):
                        cols = st.columns(COLS_PER_ROW)
                        for c in range(COLS_PER_ROW):
                            if button_index < num_chunks:
                                chunk_display_index = button_index
                                chunk_text = st.session_state.shuffled_chunks[chunk_display_index]
                                is_used = st.session_state.used_chunks[chunk_display_index]
                                button_key = f"chunk_btn_{chunk_display_index}_{st.session_state.current_ref}" # Key mit Ref
                                button_label = f"{chunk_text}"

                                with cols[c]:
                                    if is_used:
                                        st.button(f"~~{button_label}~~", key=button_key, disabled=True, use_container_width=True)
                                    else:
                                        if st.button(button_label, key=button_key, use_container_width=True):
                                            st.session_state.selected_chunks.append(chunk_text)
                                            st.session_state.used_chunks[chunk_display_index] = True
                                            if len(st.session_state.selected_chunks) == num_chunks:
                                                st.session_state.feedback_given = True
                                            st.rerun()
                                button_index += 1


                    # --- Anzeige Auswahl (unverändert) ---
                    st.markdown("---")
                    st.markdown("**Deine Auswahl:**")
                    if st.session_state.get("selected_chunks"):
                         display_text = " ".join(st.session_state.selected_chunks)
                         st.markdown(f"```{display_text}```")
                    else:
                        st.markdown("*Noch keine Bausteine ausgewählt.*")
                    st.markdown("---")

                    # --- Feedback (unverändert) ---
                    if st.session_state.get("feedback_given"):
                        user_input = " ".join(st.session_state.selected_chunks)
                        correct_text = st.session_state.current_verse_data.get("text", "")
                        original_tokens_count = len(st.session_state.current_verse_data.get("tokens", []))

                        if user_input == correct_text:
                            st.success("✅ Richtig!")
                            if not st.session_state.get("points_awarded_for_current_verse", False):
                                current_points = users.get(username, {}).get("points", 0)
                                users[username]["points"] = current_points + original_tokens_count
                                save_users(users) # Speichert die User-Punkte
                                st.session_state.points_awarded_for_current_verse = True
                                st.balloons()
                            st.markdown(f"<div style='...'><b>Richtig:</b> {correct_text}</div>", unsafe_allow_html=True) # Style wie vorher
                        else:
                            st.error("❌ Leider falsch.")
                            st.markdown(f"<div style='...'><b>Deine Eingabe:</b> {user_input}</div>", unsafe_allow_html=True) # Style wie vorher
                            st.markdown(f"<div style='...'><b>Korrekt wäre:</b> {correct_text}</div>", unsafe_allow_html=True) # Style wie vorher
                            st.session_state.points_awarded_for_current_verse = False

                        # --- Nächster Vers Button (angepasst für Public/Private) ---
                        if st.button("➡️ Nächster Vers", key="next_verse_button"):
                            current_idx = st.session_state.get(current_verse_index_key, 0) # Aktuellen Index holen

                            if mode == "reihenfolge":
                                next_idx = (current_idx + 1) % len(verses)
                                st.session_state[current_verse_index_key] = next_idx # Update im Session State für nächsten Lauf

                                # Nur bei privaten Texten den Fortschritt speichern
                                if not is_public_text:
                                    private_data = load_user_verses(username)
                                    if actual_title in private_data:
                                         private_data[actual_title]["last_index"] = next_idx
                                         save_user_verses(username, private_data)

                            # Reset state for next verse
                            keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"]
                            if mode == "random":
                                # Im Zufallsmodus Index löschen, damit neuer gewählt wird
                                if current_verse_index_key in st.session_state:
                                     del st.session_state[current_verse_index_key]

                            for key in keys_to_delete:
                                if key in st.session_state: del st.session_state[key]
                            st.rerun()

else:
    # --- Ansicht für nicht eingeloggte Benutzer (unverändert) ---
    st.sidebar.title("🔐 Anmeldung")
    login_tab, register_tab = st.sidebar.tabs(["Login", "Registrieren"])
    # ... (Login/Register Logik wie zuvor) ...
    with login_tab:
        st.subheader("Login")
        login_username = st.text_input("Benutzername", key="login_user")
        login_password = st.text_input("Passwort", type="password", key="login_pw")
        if st.button("Login", key="login_button"):
            user_data = users.get(login_username)
            if user_data and verify_password(user_data.get("password_hash", ""), login_password):
                st.session_state.logged_in_user = login_username
                st.session_state.login_error = None
                if "register_error" in st.session_state: del st.session_state.register_error
                st.rerun()
            else:
                st.session_state.login_error = "Ungültiger Benutzername oder Passwort."
                st.error(st.session_state.login_error)
        elif st.session_state.login_error:
             st.error(st.session_state.login_error)

    with register_tab:
        st.subheader("Registrieren")
        reg_username = st.text_input("Neuer Benutzername", key="reg_user")
        reg_password = st.text_input("Passwort", type="password", key="reg_pw")
        reg_password_confirm = st.text_input("Passwort bestätigen", type="password", key="reg_pw_confirm")
        if st.button("Registrieren", key="register_button"):
            if not reg_username or not reg_password or not reg_password_confirm:
                 st.session_state.register_error = "Bitte alle Felder ausfüllen."
            elif reg_password != reg_password_confirm:
                 st.session_state.register_error = "Passwörter stimmen nicht überein."
            elif reg_username in users:
                 st.session_state.register_error = "Benutzername bereits vergeben."
            elif len(reg_password) < 6:
                 st.session_state.register_error = "Passwort muss mindestens 6 Zeichen lang sein."
            else:
                 password_hash = hash_password(reg_password)
                 users[reg_username] = {"password_hash": password_hash, "points": 0}
                 save_users(users)
                 st.session_state.logged_in_user = reg_username
                 st.session_state.register_error = None
                 if "login_error" in st.session_state: del st.session_state.login_error
                 st.success(f"Benutzer '{reg_username}' erfolgreich registriert und angemeldet!")
                 st.rerun()
            if st.session_state.register_error:
                st.error(st.session_state.register_error)
        elif st.session_state.register_error:
             st.error(st.session_state.register_error)

    # Zeige Leaderboard auch für nicht eingeloggte User an
    st.title("📖 Vers-Lern-App")
    st.markdown("Bitte melde dich an oder registriere dich, um die App zu nutzen.")
    st.markdown("---")
    display_leaderboard(users)