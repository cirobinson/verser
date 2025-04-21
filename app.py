import streamlit as st
import os
import json
import random
import math
import bcrypt
import re
import time # Hinzugefügt für Auto-Advance
from difflib import SequenceMatcher # Hinzugefügt für Fehlerhervorhebung
from verses import parse_verses_from_text

# --- Konstanten ---
USER_DATA_DIR = "user_data"
USERS_FILE = os.path.join(USER_DATA_DIR, "users.json")
PUBLIC_VERSES_FILE = os.path.join(USER_DATA_DIR, "public_verses.json")
MAX_CHUNKS = 8
COLS_PER_ROW = 4
LEADERBOARD_SIZE = 10
BIBLE_FORMAT_HELP_URL = "https://bible.benkelm.de/frames.htm?listv.htm"
AUTO_ADVANCE_DELAY = 2 # Sekunden Verzögerung für Auto-Advance

# NEU: Sprachkonfiguration
LANGUAGES = {
    "DE": "🇩🇪 Deutsch",
    "EN": "🇬🇧 English",
    # Füge hier weitere Sprachen hinzu
}
DEFAULT_LANGUAGE = "DE"
PUBLIC_MARKER = "[P]" # Geändert von [Ö]

# --- Hilfsfunktionen ---

os.makedirs(USER_DATA_DIR, exist_ok=True)

# --- Passwort-Funktionen (unverändert) ---
def hash_password(password):
    # ... (wie zuvor) ...
    pw_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode('utf-8')

def verify_password(stored_hash, provided_password):
    # ... (wie zuvor) ...
    stored_hash_bytes = stored_hash.encode('utf-8')
    provided_password_bytes = provided_password.encode('utf-8')
    try:
        return bcrypt.checkpw(provided_password_bytes, stored_hash_bytes)
    except ValueError:
        return False

# --- Benutzer Laden/Speichern (unverändert) ---
def load_users():
    # ... (wie zuvor) ...
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                for user, details in data.items():
                    if 'points' not in details or not isinstance(details['points'], (int, float)):
                        data[user]['points'] = 0
                    if 'password_hash' not in details:
                        pass
                return data
        except (json.JSONDecodeError, IOError):
            st.error("Benutzerdatei konnte nicht gelesen werden.")
            return {}
    return {}

def save_users(users):
    # ... (wie zuvor) ...
    try:
        with open(USERS_FILE, "w", encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except IOError:
        st.error("Fehler beim Speichern der Benutzerdaten.")


# --- Verse Laden/Speichern (Stark angepasst für Sprachen) ---

def get_user_verse_file(username):
    # ... (wie zuvor) ...
    safe_username = "".join(c for c in username if c.isalnum() or c in ('_', '-')).rstrip()
    if not safe_username:
        safe_username = f"user_{random.randint(1000, 9999)}"
    return os.path.join(USER_DATA_DIR, f"{safe_username}_verses_v2.json") # v2 wegen Sprachstruktur

def load_user_verses(username, language_code):
    """Lädt die privaten Verse eines Benutzers für eine bestimmte Sprache."""
    filepath = get_user_verse_file(username)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding='utf-8') as f:
                all_lang_data = json.load(f)
                lang_data = all_lang_data.get(language_code, {})
                # Stelle sicher, dass interne Flags korrekt sind (optional)
                for title, details in lang_data.items():
                    details['public'] = False # Sollten alle privat sein
                    details['language'] = language_code
                return lang_data
        except (json.JSONDecodeError, IOError):
             st.warning(f"Private Versdatei für {username} konnte nicht gelesen werden.")
             return {}
    return {}

def save_user_verses(username, language_code, lang_specific_data):
    """Speichert die privaten Verse eines Benutzers für eine bestimmte Sprache."""
    filepath = get_user_verse_file(username)
    all_data = {}
    # Lade zuerst alle vorhandenen Sprachen
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding='utf-8') as f:
                all_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            st.warning(f"Konnte alte Daten für {username} nicht laden, überschreibe evtl.")

    # Update die spezifische Sprache
    # Stelle sicher, dass nur wirklich private Daten gespeichert werden
    all_data[language_code] = {title: details for title, details in lang_specific_data.items() if not details.get('public', False)}

    # Speichere das gesamte Objekt zurück
    try:
        with open(filepath, "w", encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        st.error(f"Fehler beim Speichern der privaten Verse für {username}: {e}")

def load_public_verses(language_code):
    """Lädt alle öffentlichen Verse für eine bestimmte Sprache."""
    if os.path.exists(PUBLIC_VERSES_FILE):
        try:
            with open(PUBLIC_VERSES_FILE, "r", encoding='utf-8') as f:
                all_lang_data = json.load(f)
                lang_data = all_lang_data.get(language_code, {})
                # Stelle sicher, dass interne Flags korrekt sind
                for title, details in lang_data.items():
                    details['public'] = True
                    details['language'] = language_code
                return lang_data
        except (json.JSONDecodeError, IOError):
            st.warning("Öffentliche Versdatei konnte nicht gelesen werden.")
            return {}
    return {}

def save_public_verses(language_code, lang_specific_data):
    """Speichert alle öffentlichen Verse für eine bestimmte Sprache."""
    all_data = {}
     # Lade zuerst alle vorhandenen Sprachen
    if os.path.exists(PUBLIC_VERSES_FILE):
        try:
            with open(PUBLIC_VERSES_FILE, "r", encoding='utf-8') as f:
                all_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            st.warning("Konnte alte öffentliche Daten nicht laden, überschreibe evtl.")

    # Update die spezifische Sprache
    # Stelle sicher, dass nur als public markierte gespeichert werden
    all_data[language_code] = {title: details for title, details in lang_specific_data.items() if details.get('public', False)}

    # Speichere das gesamte Objekt zurück
    try:
        with open(PUBLIC_VERSES_FILE, "w", encoding='utf-8') as f:
             json.dump(all_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        st.error(f"Fehler beim Speichern der öffentlichen Verse: {e}")


# --- Formatprüfungsfunktion (unverändert) ---
def is_format_likely_correct(text):
    # ... (wie zuvor) ...
    if not text or not isinstance(text, str): return False
    lines = text.strip().split('\n')
    if not lines: return False
    first_line = lines[0].strip()
    match = re.match(r"^\s*\d+\)\s+", first_line)
    return match is not None

# --- NEU: Einfache Inhaltsprüfung (Platzhalter!) ---
def contains_forbidden_content(text):
    """Sehr einfache Prüfung auf unerwünschte Schlüsselwörter."""
    if not text or not isinstance(text, str):
        return False
    text_lower = text.lower()
    # !! Dies ist nur ein Beispiel - SEHR unzureichend für echte Moderation !!
    forbidden_keywords = ["sex", "porn", "gamble", "kill", "drogen", "nazi", "hitler", "idiot", "arschloch", "fick"]
    # Füge hier ggf. weitere, sprachspezifische Begriffe hinzu
    for keyword in forbidden_keywords:
        if keyword in text_lower:
            return True
    # Prüfung auf "Nonsense" (z.B. nur Zufallszeichen) ist noch schwieriger
    # Hier könnte man z.B. die Ratio von Vokalen/Konsonanten, Wortlänge etc. prüfen
    return False

# --- Textbausteine-Funktion (unverändert) ---
def group_words_into_chunks(words, max_chunks=MAX_CHUNKS):
    # ... (wie zuvor) ...
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
    # ... (wie zuvor) ...
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

# --- NEU: Funktion zur Hervorhebung von Fehlern ---
def highlight_errors(selected_chunks, correct_chunks):
    """Erzeugt einen HTML-String, der Fehler in den ausgewählten Chunks hervorhebt."""
    html_output = []
    matcher = SequenceMatcher(None, correct_chunks, selected_chunks)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            html_output.append(" ".join(selected_chunks[j1:j2]))
        elif tag == 'replace' or tag == 'insert':
             # Rot hervorheben, was der User gewählt hat
            html_output.append(f"<span style='color:red; font-weight:bold;'>{' '.join(selected_chunks[j1:j2])}</span>")
        elif tag == 'delete':
             # Optional: anzeigen, was fehlt (hier nicht direkt sichtbar in User-Auswahl)
             pass
    # Führe die Teile mit Leerzeichen zusammen (außer am Anfang/Ende)
    return " ".join(filter(None, html_output))


# --- App Setup ---
st.set_page_config(layout="wide")

# --- Session State Initialisierung ---
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None
if "login_error" not in st.session_state: st.session_state.login_error = None
if "register_error" not in st.session_state: st.session_state.register_error = None
# NEU: Sprache im State speichern
if "selected_language" not in st.session_state:
    st.session_state.selected_language = DEFAULT_LANGUAGE

# --- Login / Registrierung / Logout (unverändert) ---
users = load_users()

if st.session_state.logged_in_user:
    # --- Ansicht für eingeloggte Benutzer ---
    st.sidebar.success(f"Angemeldet als: **{st.session_state.logged_in_user}**")
    user_points = users.get(st.session_state.logged_in_user, {}).get("points", 0)
    st.sidebar.markdown(f"**🏆 Deine Punkte: {user_points}**")

    if st.sidebar.button("🔒 Logout"):
        # ... (Logout Logik wie zuvor) ...
        keys_to_clear = list(st.session_state.keys())
        for key in keys_to_clear:
            # Spracheinstellung evtl. behalten? Oder auch zurücksetzen? Hier zurücksetzen.
            # if key not in ['selected_language']:
                del st.session_state[key]
        st.session_state.logged_in_user = None
        st.session_state.selected_language = DEFAULT_LANGUAGE # Sprache zurücksetzen
        st.rerun()

    # --- Hauptanwendung (nur wenn eingeloggt) ---
    username = st.session_state.logged_in_user

    # --- Layout mit Leaderboard ---
    main_col, leaderboard_col = st.columns([3, 1])

    with leaderboard_col:
        display_leaderboard(users)

    with main_col:
        st.title("📖 Vers-Lern-App")

        # --- NEU: Konsolidierte Auswahl (Sprache | Text | Modus) ---
        sel_col1, sel_col2, sel_col3 = st.columns([1, 3, 1]) # Relative Breiten

        with sel_col1:
            # Sprachauswahl
            lang_options = list(LANGUAGES.keys())
            lang_display = [LANGUAGES[k] for k in lang_options]
            selected_lang_display = st.selectbox(
                "Sprache",
                lang_display,
                index=lang_options.index(st.session_state.selected_language), # Index basierend auf Key 'DE', 'EN'
                key="language_select"
            )
            # Finde den Key ('DE', 'EN') zur Anzeige
            selected_lang_key = next(key for key, value in LANGUAGES.items() if value == selected_lang_display)

            # Wenn Sprache geändert wurde, State aktualisieren und neu laden
            if selected_lang_key != st.session_state.selected_language:
                st.session_state.selected_language = selected_lang_key
                # Wichtige States zurücksetzen, da Texte etc. wechseln
                keys_to_delete = [k for k in st.session_state if k.startswith("selected_display_title_") or k.startswith("selected_mode_") or k.startswith("current_verse_index_")]
                keys_to_delete.extend(["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"])
                for key in keys_to_delete:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()

        # Aktuelle Sprache für den Rest des Codes
        current_language = st.session_state.selected_language

        # --- Texte laden (basierend auf Sprache) ---
        user_verses_private = load_user_verses(username, current_language)
        public_verses = load_public_verses(current_language)

        # Kombiniere Texte für die Auswahl
        available_texts = {}
        for title, data in user_verses_private.items():
            available_texts[title] = {**data, 'source': 'private'}
        for title, data in public_verses.items():
            display_title = f"{PUBLIC_MARKER} {title}"
            available_texts[display_title] = {**data, 'source': 'public', 'original_title': title}

        with sel_col2:
            # Textauswahl
            if not available_texts:
                st.warning(f"Keine Texte für {LANGUAGES[current_language]} verfügbar.")
                selected_display_title = None
            else:
                sorted_titles = sorted(available_texts.keys())
                # Eindeutiger State Key pro Sprache
                session_title_key = f"selected_display_title_{current_language}"

                if session_title_key not in st.session_state or st.session_state[session_title_key] not in available_texts:
                    st.session_state[session_title_key] = sorted_titles[0]

                selected_display_title = st.selectbox(
                    "Bibeltext",
                    sorted_titles,
                    index=sorted_titles.index(st.session_state[session_title_key]),
                    key=f"selectbox_{username}_{current_language}"
                )

                # Wenn Textauswahl geändert wurde
                if selected_display_title != st.session_state[session_title_key]:
                    st.session_state[session_title_key] = selected_display_title
                    keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "current_verse_index", "points_awarded_for_current_verse"]
                    # Modus- und Index-Keys könnten auch Text-spezifisch sein
                    keys_to_delete.extend([k for k in st.session_state if k.startswith("selected_mode_") or k.startswith("current_verse_index_")])
                    for key in keys_to_delete:
                        if key in st.session_state: del st.session_state[key]
                    st.rerun()

        # Holen der Textdaten (nur wenn ein Titel ausgewählt wurde)
        if selected_display_title:
            selected_text_info = available_texts[selected_display_title]
            is_public_text = selected_text_info['source'] == 'public'
            actual_title = selected_text_info.get('original_title', selected_display_title)
            current_text_data = selected_text_info
            verses = current_text_data.get("verses", [])
            total_verses = len(verses)
        else:
            # Setze Defaults, wenn kein Text ausgewählt ist
            selected_text_info = None
            is_public_text = False
            actual_title = None
            current_text_data = {}
            verses = []
            total_verses = 0

        with sel_col3:
            # Lernmodus Auswahl (Dropdown)
            # Modus "linear" statt "der Reihe nach"
            mode_options_map = {"linear": "Linear", "random": "Zufällig"} # Intern:Anzeige
            mode_keys = list(mode_options_map.keys())
            mode_display_options = list(mode_options_map.values())

            default_mode_internal = "linear" # Default auch für öffentliche
            if not is_public_text and actual_title in user_verses_private:
                 # Lese Modus aus privaten Daten
                 default_mode_internal = user_verses_private.get(actual_title, {}).get("mode", "linear")

            # Eindeutiger Session Key pro Text und Sprache
            session_mode_key = f"selected_mode_{current_language}_{selected_display_title}"

            # Initialisiere Modus im State wenn nötig
            if session_mode_key not in st.session_state:
                 st.session_state[session_mode_key] = default_mode_internal

            # Finde den Anzeige-Namen für den aktuellen State
            current_selected_mode_display = mode_options_map.get(st.session_state[session_mode_key], mode_options_map["linear"])

            # Selectbox erstellen
            selected_mode_display = st.selectbox(
                "Lernmodus",
                mode_display_options,
                index=mode_display_options.index(current_selected_mode_display),
                key=f"mode_select_{username}_{current_language}_{selected_display_title}"
            )

            # Finde den internen Key ('linear', 'random') zum ausgewählten Anzeige-Namen
            selected_mode_internal = next(key for key, value in mode_options_map.items() if value == selected_mode_display)

            # Speichere Modusänderung (nur für private Texte persistent)
            if selected_mode_internal != st.session_state[session_mode_key]:
                 st.session_state[session_mode_key] = selected_mode_internal

                 if not is_public_text:
                     # Nur bei privaten Texten in Datei speichern
                     # Laden -> Ändern -> Speichern
                     private_texts = load_user_verses(username, current_language)
                     if actual_title in private_texts:
                         private_texts[actual_title]["mode"] = selected_mode_internal
                         save_user_verses(username, current_language, private_texts)
                     else:
                          st.warning(f"Konnte privaten Text '{actual_title}' zum Speichern des Modus nicht finden.")

                 # Reset verse state on mode change
                 keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "current_verse_index", "points_awarded_for_current_verse"]
                 keys_to_delete.extend([k for k in st.session_state if k.startswith("current_verse_index_")]) # Index auch zurücksetzen
                 for key in keys_to_delete:
                     if key in st.session_state: del st.session_state[key]
                 st.rerun()

            # Aktueller Modus für die Logik
            mode = st.session_state[session_mode_key]


        # --- NEU: Fortschrittsbalken ---
        if selected_display_title and total_verses > 0:
             # Sicherstellen, dass der Index im State existiert und gültig ist
             current_verse_index_key = f"current_verse_index_{current_language}_{selected_display_title}"
             # Verwende last_index als Startwert nur wenn Modus linear & Text privat
             start_idx = 0
             if mode == 'linear' and not is_public_text and actual_title in user_verses_private:
                  start_idx = user_verses_private.get(actual_title, {}).get("last_index", 0)
             # Korrigiere Startindex, falls er außerhalb des Bereichs liegt
             start_idx = start_idx if 0 <= start_idx < total_verses else 0

             # Lese aktuellen Index aus Session State, nutze start_idx als Fallback
             idx = st.session_state.get(current_verse_index_key, start_idx)
             # Stelle sicher, dass idx immer gültig ist
             idx = max(0, min(idx, total_verses - 1))

             progress_value = (idx + 1) / total_verses
             st.progress(progress_value, text=f"Vers {idx + 1} von {total_verses}")
        else:
             idx = 0 # Kein Text oder keine Verse -> Index 0


        # --- Text hinzufügen (Sidebar, angepasst für Sprache und Content Check) ---
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### 📥 Text für {LANGUAGES[current_language]} hinzufügen")
        new_title = st.sidebar.text_input("Titel", key=f"new_title_input_{current_language}").strip()
        new_text = st.sidebar.text_area("Text (`1) Ref...`)", key=f"new_text_input_{current_language}").strip()
        share_publicly = st.sidebar.checkbox("Öffentlich freigeben", key=f"share_checkbox_{current_language}", value=False)

        if st.sidebar.button("📌 Speichern", key=f"save_button_{current_language}"):
            # Prüfungen: Titel, Text, Format, Inhalt
            if not new_title: st.sidebar.error("Bitte Titel eingeben.")
            elif not new_text: st.sidebar.error("Bitte Text eingeben.")
            elif not is_format_likely_correct(new_text):
                 st.sidebar.error(f"Format nicht korrekt. [Hilfe]({BIBLE_FORMAT_HELP_URL})")
            # NEU: Inhaltsprüfung
            elif contains_forbidden_content(new_text):
                 st.sidebar.error("Inhalt unzulässig. Bitte prüfe den Text.")
            else:
                # Alle Prüfungen OK -> Parsen und Speichern
                try:
                    parsed = parse_verses_from_text(new_text)
                    if parsed:
                        if share_publicly:
                            all_public_verses = load_public_verses(current_language)
                            if new_title in all_public_verses:
                                st.sidebar.error(f"Öffentlicher Titel '{new_title}' existiert bereits in dieser Sprache.")
                            else:
                                all_public_verses[new_title] = {"verses": parsed, "public": True, "added_by": username, "language": current_language}
                                save_public_verses(current_language, all_public_verses)
                                st.sidebar.success("Öffentlicher Text gespeichert!")
                                st.rerun()
                        else:
                            all_user_verses = load_user_verses(username, current_language)
                            if new_title in all_user_verses: st.sidebar.warning("Privater Text wird überschrieben.")
                            all_user_verses[new_title] = {"verses": parsed, "mode": "linear", "last_index": 0, "public": False, "language": current_language}
                            save_user_verses(username, current_language, all_user_verses)
                            st.sidebar.success("Privater Text gespeichert!")
                            st.rerun()
                    else:
                        st.sidebar.error("Text konnte nicht geparsed werden.")
                except Exception as e:
                    st.sidebar.error(f"Fehler: {e}")


        # --- Haupt-Lernlogik (nur wenn Text ausgewählt und Verse vorhanden) ---
        if selected_display_title and verses:

                # --- Aktueller Vers Logik (Verwendet idx von oben) ---
                # Sicherstellen, dass idx gültig ist (wird oben bereits gemacht)
                idx = max(0, min(idx, len(verses) - 1)) # Doppelte Sicherheit
                current_verse = verses[idx]
                tokens = current_verse.get("text", "").split()
                original_chunks = group_words_into_chunks(tokens, MAX_CHUNKS)
                num_chunks = len(original_chunks)

                # --- Leere Verse Behandlung ---
                if not tokens or not original_chunks:
                     st.warning(f"Vers {current_verse.get('ref', '')} ist leer oder konnte nicht verarbeitet werden.")
                     # --- NEU: Buttons für Navigation bei leerem Vers ---
                     nav_cols = st.columns(5)
                     with nav_cols[0]: # Vorheriger Vers Button (nur linear)
                         show_prev_button = (mode == 'linear' and total_verses > 1)
                         if st.button("⬅️ Zurück", key="prev_verse_button_empty", disabled=not show_prev_button):
                             prev_idx = (idx - 1 + total_verses) % total_verses
                             st.session_state[current_verse_index_key] = prev_idx
                             if not is_public_text: # Nur bei privaten Texten persistieren
                                  private_data = load_user_verses(username, current_language)
                                  if actual_title in private_data:
                                      private_data[actual_title]["last_index"] = prev_idx
                                      save_user_verses(username, current_language, private_data)
                             # Reset State für den neuen (vorherigen) Vers
                             keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"]
                             for key in keys_to_delete:
                                 if key in st.session_state: del st.session_state[key]
                             st.rerun()
                     with nav_cols[4]: # Nächster Vers Button
                         if st.button("➡️ Überspringen", key="skip_verse_button_empty"):
                             next_idx = (idx + 1) % total_verses
                             st.session_state[current_verse_index_key] = next_idx
                             if mode == 'linear' and not is_public_text: # Nur bei linearen, privaten Texten persistieren
                                  private_data = load_user_verses(username, current_language)
                                  if actual_title in private_data:
                                      private_data[actual_title]["last_index"] = next_idx
                                      save_user_verses(username, current_language, private_data)
                             # Reset State für nächsten Vers
                             keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"]
                             if mode == "random":
                                 if current_verse_index_key in st.session_state: del st.session_state[current_verse_index_key]
                             for key in keys_to_delete:
                                 if key in st.session_state: del st.session_state[key]
                             st.rerun()

                else:
                    # --- State Initialisierung für den aktuellen Vers ---
                    # Verwende Ref UND Index für State-Keys, um bei Zufall sicher zu sein
                    verse_state_base_key = f"{current_language}_{selected_display_title}_{current_verse.get('ref', idx)}"

                    # Initialisiere, wenn nötig oder wenn sich Ref geändert hat
                    if f"shuffled_chunks_{verse_state_base_key}" not in st.session_state or st.session_state.get("current_ref") != current_verse["ref"]:
                        st.session_state[f"shuffled_chunks_{verse_state_base_key}"] = random.sample(original_chunks, num_chunks)
                        # NEU: Speichere ausgewählte Chunks als Liste von Tupeln: (text, original_shuffled_index)
                        st.session_state[f"selected_chunks_{verse_state_base_key}"] = []
                        st.session_state[f"used_chunks_{verse_state_base_key}"] = [False] * num_chunks
                        st.session_state[f"feedback_given_{verse_state_base_key}"] = False
                        # Globale Refs für einfachere Prüfung
                        st.session_state["current_ref"] = current_verse["ref"]
                        st.session_state["current_verse_data"] = { # Allgemeine Daten für Feedback etc.
                            "ref": current_verse["ref"],
                            "text": current_verse["text"],
                            "original_chunks": original_chunks,
                            "tokens": tokens
                        }
                        st.session_state[f"points_awarded_{verse_state_base_key}"] = False


                    # Lese aktuellen State für diesen Vers
                    shuffled_chunks = st.session_state[f"shuffled_chunks_{verse_state_base_key}"]
                    selected_chunks_list = st.session_state[f"selected_chunks_{verse_state_base_key}"] # Liste der Tupel
                    used_chunks = st.session_state[f"used_chunks_{verse_state_base_key}"]
                    feedback_given = st.session_state[f"feedback_given_{verse_state_base_key}"]
                    points_awarded = st.session_state[f"points_awarded_{verse_state_base_key}"]


                    # --- Anzeige der Baustein-Buttons ---
                    st.markdown(f"### 📌 {current_verse['ref']}")
                    st.markdown(f"🧩 Wähle die Textbausteine:")

                    num_rows = math.ceil(num_chunks / COLS_PER_ROW)
                    button_index = 0

                    for r in range(num_rows):
                        cols = st.columns(COLS_PER_ROW)
                        for c in range(COLS_PER_ROW):
                            if button_index < num_chunks:
                                chunk_display_index = button_index # Index in der *gemischten* Liste
                                chunk_text = shuffled_chunks[chunk_display_index]
                                is_used = used_chunks[chunk_display_index]
                                # Eindeutiger Key pro Button & Ref
                                button_key = f"chunk_btn_{chunk_display_index}_{current_verse['ref']}"

                                with cols[c]:
                                    if is_used:
                                        st.button(f"~~{chunk_text}~~", key=button_key, disabled=True, use_container_width=True)
                                    else:
                                        if st.button(chunk_text, key=button_key, use_container_width=True):
                                            # Füge Tupel zur Liste hinzu
                                            selected_chunks_list.append((chunk_text, chunk_display_index))
                                            used_chunks[chunk_display_index] = True
                                            st.session_state[f"selected_chunks_{verse_state_base_key}"] = selected_chunks_list
                                            st.session_state[f"used_chunks_{verse_state_base_key}"] = used_chunks


                                            # Prüfe, ob alle ausgewählt wurden -> Feedback
                                            if len(selected_chunks_list) == num_chunks:
                                                st.session_state[f"feedback_given_{verse_state_base_key}"] = True
                                                feedback_given = True # Update lokale Variable für sofortige Anzeige

                                            st.rerun()
                                button_index += 1


                    # --- NEU: Anzeige der ausgewählten Bausteine (ohne Titel) & Rückgängig-Button ---
                    st.markdown("---") # Trenner
                    sel_chunks_cols = st.columns([5, 1]) # Platz für Button
                    with sel_chunks_cols[0]:
                         # Zeige ausgewählte Chunks (nur Texte)
                         display_text = " ".join([item[0] for item in selected_chunks_list]) if selected_chunks_list else "*Noch nichts ausgewählt.*"
                         st.markdown(f"```{display_text}```")
                    with sel_chunks_cols[1]:
                         # NEU: "Letzten zurücknehmen" Button
                         if st.button("↩️", key=f"undo_last_{verse_state_base_key}", help="Letzten Baustein zurücknehmen", disabled=not selected_chunks_list):
                              if selected_chunks_list:
                                  last_chunk_text, last_original_index = selected_chunks_list.pop()
                                  # Markiere den entsprechenden Button wieder als verfügbar
                                  used_chunks[last_original_index] = False
                                  # Update State
                                  st.session_state[f"selected_chunks_{verse_state_base_key}"] = selected_chunks_list
                                  st.session_state[f"used_chunks_{verse_state_base_key}"] = used_chunks
                                  # Feedback zurücksetzen, falls es durch die letzte Auswahl ausgelöst wurde
                                  if feedback_given and len(selected_chunks_list) < num_chunks:
                                       st.session_state[f"feedback_given_{verse_state_base_key}"] = False
                                  st.rerun()


                    st.markdown("---") # Trenner


                    # --- Feedback & Navigation ---
                    if feedback_given:
                        user_input_chunks = [item[0] for item in selected_chunks_list]
                        user_input_text = " ".join(user_input_chunks)
                        correct_text = st.session_state["current_verse_data"].get("text", "")
                        correct_chunks_original = st.session_state["current_verse_data"].get("original_chunks", [])
                        original_tokens_count = len(st.session_state["current_verse_data"].get("tokens", []))

                        is_correct = (user_input_text == correct_text)

                        if is_correct:
                            st.success("✅ Richtig!")
                            if not points_awarded:
                                current_points = users.get(username, {}).get("points", 0)
                                users[username]["points"] = current_points + original_tokens_count
                                save_users(users)
                                st.session_state[f"points_awarded_{verse_state_base_key}"] = True
                                st.balloons()
                            st.markdown(f"<div style='background-color:#e6ffed; color:#094d21; padding:10px; border-radius:5px; border: 1px solid #b3e6c5;'><b>{correct_text}</b></div>", unsafe_allow_html=True)

                            # --- NEU: Auto-Advance ---
                            st.markdown("➡️ Nächster Vers in Kürze...")
                            time.sleep(AUTO_ADVANCE_DELAY)
                            # Logik für nächsten Vers (wie im Button)
                            next_idx = (idx + 1) % total_verses
                            st.session_state[current_verse_index_key] = next_idx
                            if mode == 'linear' and not is_public_text:
                                private_data = load_user_verses(username, current_language)
                                if actual_title in private_data:
                                    private_data[actual_title]["last_index"] = next_idx
                                    save_user_verses(username, current_language, private_data)
                            # Reset State für nächsten Vers
                            keys_to_delete = ["shuffled_chunks", "selected_chunks", "used_chunks", "feedback_given", "current_ref", "current_verse_data", "points_awarded_for_current_verse"]
                            keys_to_delete.extend([k for k in st.session_state if k.startswith(f"shuffled_chunks_{verse_state_base_key.split('_')[0]}_{verse_state_base_key.split('_')[1]}")]) # Alle States für diesen Text/Sprache löschen? Vorsicht!
                            # Sicherer: Nur die spezifischen für diesen Ref löschen
                            keys_to_delete.extend([k for k in st.session_state if verse_state_base_key in k])

                            if mode == "random":
                                if current_verse_index_key in st.session_state: del st.session_state[current_verse_index_key]
                            for key in keys_to_delete:
                                if key in st.session_state: del st.session_state[key]
                            st.rerun()

                        else: # Falsche Antwort
                            st.error("❌ Leider falsch.")
                            # --- NEU: Fehler hervorheben ---
                            highlighted_input = highlight_errors(user_input_chunks, correct_chunks_original)
                            st.markdown("<b>Deine Eingabe (Fehler markiert):</b>", unsafe_allow_html=True)
                            st.markdown(f"<div style='background-color:#ffebeb; color:#8b0000; padding:10px; border-radius:5px; border: 1px solid #f5c6cb;'>{highlighted_input}</div>", unsafe_allow_html=True)
                            st.markdown("<b>Korrekt wäre:</b>", unsafe_allow_html=True)
                            st.markdown(f"<div style='background-color:#e6ffed; color:#094d21; padding:10px; border-radius:5px; border: 1px solid #b3e6c5; margin-top: 5px;'>{correct_text}</div>", unsafe_allow_html=True)
                            st.session_state[f"points_awarded_{verse_state_base_key}"] = False # Keine Punkte

                            # --- NEU: Buttons bei falscher Antwort (Zurück / Nächster Vers) ---
                            nav_cols_feedback = st.columns([1,3,1])
                            with nav_cols_feedback[0]: # Vorheriger Vers Button
                                show_prev_button = (mode == 'linear' and total_verses > 1)
                                if st.button("⬅️ Zurück", key="prev_verse_button_feedback", disabled=not show_prev_button):
                                    prev_idx = (idx - 1 + total_verses) % total_verses
                                    st.session_state[current_verse_index_key] = prev_idx
                                    if not is_public_text: # Persistieren
                                        private_data = load_user_verses(username, current_language)
                                        if actual_title in private_data:
                                            private_data[actual_title]["last_index"] = prev_idx
                                            save_user_verses(username, current_language, private_data)
                                    # Reset State
                                    keys_to_delete = [k for k in st.session_state if verse_state_base_key in k or k == "current_verse_data" or k == "current_ref"]
                                    for key in keys_to_delete:
                                        if key in st.session_state: del st.session_state[key]
                                    st.rerun()

                            with nav_cols_feedback[2]: # Nächster Vers Button
                                if st.button("➡️ Nächster Vers", key="next_verse_button_feedback"):
                                    next_idx = (idx + 1) % total_verses
                                    st.session_state[current_verse_index_key] = next_idx
                                    if mode == 'linear' and not is_public_text: # Persistieren
                                        private_data = load_user_verses(username, current_language)
                                        if actual_title in private_data:
                                            private_data[actual_title]["last_index"] = next_idx
                                            save_user_verses(username, current_language, private_data)
                                    # Reset State
                                    keys_to_delete = [k for k in st.session_state if verse_state_base_key in k or k == "current_verse_data" or k == "current_ref"]
                                    if mode == "random":
                                        if current_verse_index_key in st.session_state: del st.session_state[current_verse_index_key]
                                    for key in keys_to_delete:
                                        if key in st.session_state: del st.session_state[key]
                                    st.rerun()

else: # Nicht eingeloggt
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
                # Sprache auf Default setzen beim Login
                st.session_state.selected_language = DEFAULT_LANGUAGE
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
            # ... (Validierungen wie zuvor) ...
            if not reg_username or not reg_password or not reg_password_confirm:
                 st.session_state.register_error = "Bitte alle Felder ausfüllen."
            elif reg_password != reg_password_confirm:
                 st.session_state.register_error = "Passwörter stimmen nicht überein."
            elif reg_username in users:
                 st.session_state.register_error = "Benutzername bereits vergeben."
            elif len(reg_password) < 6:
                 st.session_state.register_error = "Passwort muss mind. 6 Zeichen lang sein."
            else:
                 password_hash = hash_password(reg_password)
                 users[reg_username] = {"password_hash": password_hash, "points": 0}
                 save_users(users)
                 st.session_state.logged_in_user = reg_username
                 st.session_state.register_error = None
                 if "login_error" in st.session_state: del st.session_state.login_error
                 # Sprache auf Default setzen beim Registrieren/Login
                 st.session_state.selected_language = DEFAULT_LANGUAGE
                 st.success(f"Benutzer '{reg_username}' registriert & angemeldet!")
                 st.rerun()
            if st.session_state.register_error:
                st.error(st.session_state.register_error)
        elif st.session_state.register_error:
             st.error(st.session_state.register_error)


    # Zeige Leaderboard auch für nicht eingeloggte User an
    st.title("📖 Vers-Lern-App")
    st.markdown("Bitte melde dich an oder registriere dich.")
    st.markdown("---")
    display_leaderboard(users)