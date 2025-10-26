import streamlit as st
import pandas as pd
import random, time, os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------
# SEITENKONFIGURATION
# ---------------------------------------------
st.set_page_config(page_title="Verhandlungsexperiment", page_icon="💬", layout="centered")

# ---------------------------------------------
# INITIALISIERUNG DER SESSION-STATE VARIABLEN
# ---------------------------------------------
def init_state():
    if "tempo" not in st.session_state:
        st.session_state.tempo = random.choice(["sofort", "verzoegert", "gegenverhandlung"])
    if "batna" not in st.session_state:
        st.session_state.batna = random.choice(["stark", "schwach"])
    if "chat" not in st.session_state:
        st.session_state.chat = []
    if "angebot" not in st.session_state:
        st.session_state.angebot = 450
    if "phase" not in st.session_state:
        st.session_state.phase = "consent"
    if "response_time_ms" not in st.session_state:
        st.session_state.response_time_ms = None
    if "start_ts" not in st.session_state:
        st.session_state.start_ts = None

# ---------------------------------------------
# HILFSFUNKTIONEN
# ---------------------------------------------
def add_msg(speaker, text):
    """Fügt dem Chat eine neue Nachricht hinzu."""
    st.session_state.chat.append({"speaker": speaker, "text": text, "ts": datetime.utcnow().isoformat()})

def ensure_data_dir():
    """Erstellt bei Bedarf den Ordner 'data' für Ergebnisdateien."""
    os.makedirs("data", exist_ok=True)
# --- Verbindung zu Google Sheets ---
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)

# Deine Google-Sheet-ID aus der URL:
SHEET_ID = "1kAljwsbwhl6U4EjBJK-VVIZlLsQzTKD-So36l7ULXkw"
sheet = client.open_by_key(SHEET_ID).sheet1

def save_row(row):
    """Speichert eine Teilnahme als Zeile in Google Sheets."""
    try:
        # Werte in der Reihenfolge der Keys extrahieren
        values = [row[k] for k in row.keys()]
        sheet.append_row(values)
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern in Google Sheets: {e}")

# ---------------------------------------------
# APP-START
# ---------------------------------------------
init_state()
st.title("💬 Verhandlungsexperiment: „Zu schnell, zu schade?“")

# ---------------------------------------------
# PHASE 1: EINVERSTÄNDNISERKLÄRUNG & ERKLÄRUNG ZUR AUFGABE
# ---------------------------------------------
if st.session_state.phase == "consent":
    st.markdown("""
    **Kurzinfo & Einwilligung**

    Sie nehmen an einer kurzen, anonymen Studie zu Verhandlungen teil (Dauer ca. 10 Minuten).
    Die Gegenseite ist simuliert. Es werden keine personenbezogenen Daten erhoben.

    *Ich stimme der anonymen Datenerhebung zu und kann jederzeit abbrechen.*
    """)
    if st.button("Zustimmen und starten"):
        st.session_state.phase = "intro_batna"
        st.rerun()

elif st.session_state.phase == "intro_batna":
    st.markdown("""
    **Hinweis zur Aufgabe**

    In dieser Studie wird Ihnen eine sogenannte *BATNA* beschrieben.  
    Das steht für *Best Alternative to a Negotiated Agreement* –  
    also Ihre **beste Alternative**, falls die Verhandlung scheitert.  

    Eine *starke BATNA* bedeutet: Sie haben ein gutes alternatives Angebot.  
    Eine *schwache BATNA* bedeutet: Sie haben keine Alternative und sind stärker vom aktuellen Angebot abhängig.
    """)
    if st.button("Weiter"):
        st.session_state.phase = "scenario"
        st.rerun()
# ---------------------------------------------
# PHASE 2: SZENARIO / BATNA
# ---------------------------------------------
elif st.session_state.phase == "scenario":
    batna = st.session_state.batna

    st.markdown("""
    **Szenario (Ihre Rolle: Anbieter:in)**  
    Sie sind Freelancer:in (Grafikdesign).  
    Sie möchten für ein Projekt einen **angemessenen Betrag** verlangen,  
    den Sie selbst festlegen können.  

    Je nach Situation haben Sie eine unterschiedliche Ausgangslage (BATNA):
    """)

    if batna == "stark":
        st.info("Sie haben eine **starke BATNA**: Ein anderes Projekt über 440 € ist in Aussicht.")
    else:
        st.info("Sie haben eine **schwache/unsichere BATNA**: Aktuell kein weiteres konkretes Angebot.")
    
    st.session_state.angebot = st.number_input(
        "Ihr Angebot (€):",
        min_value=100,
        max_value=2000,
        step=10,
        placeholder="Bitte Betrag eingeben"
    )

    if st.button("Angebot im Chat senden"):
        st.session_state.phase = "chat"
        st.session_state.chat = []
        add_msg("Sie", f"Ich könnte das Projekt für {int(st.session_state.angebot)} € übernehmen.")
        st.session_state.start_ts = time.time()
        st.rerun()


# ---------------------------------------------
# PHASE 3: CHAT
# ---------------------------------------------
elif st.session_state.phase == "chat":
    tempo = st.session_state.tempo

    for m in st.session_state.chat:
        if m["speaker"] == "Sie":
            st.chat_message("user").write(m["text"])
        else:
            st.chat_message("assistant").write(m["text"])

    if "reacted" not in st.session_state:
        st.session_state.reacted = False

    if not st.session_state.reacted:
        with st.spinner("Kundin tippt..."):
            if tempo == "sofort":
                time.sleep(1)
                add_msg("Kundin", "Das klingt super, ich nehme Ihr Angebot direkt an!")
                st.session_state.response_time_ms = int((time.time() - st.session_state.start_ts)*1000)
  elif tempo == "verzoegert":
    # 1️⃣ Wenn Kundin noch nicht reagiert hat, erste Nachricht senden
    if "verzoegert_phase" not in st.session_state:
        add_msg("Kundin", "Hm... ich muss kurz nachdenken...")
        st.session_state.verzoegert_phase = "waiting"
        st.session_state.verzoegert_start = time.time()
        st.rerun()

    # 2️⃣ Während der Wartezeit: nichts tun, nur anzeigen, dass Kundin tippt
    elif st.session_state.verzoegert_phase == "waiting":
        elapsed = time.time() - st.session_state.verzoegert_start

        # Anzeige: „Kundin tippt...“ während der 10 Sekunden
        with st.spinner("💬 Kundin tippt..."):
            if elapsed < 10:
                time.sleep(1)
                st.rerun()

        # Nach Ablauf von 10 Sekunden: zweite Nachricht senden
        add_msg("Kundin", "Okay, ich nehme Ihr Angebot an.")
        st.session_state.response_time_ms = int((time.time() - st.session_state.start_ts)*1000)
        st.session_state.reacted = True

        # Flags löschen, damit die Phase sauber zurückgesetzt wird
        del st.session_state.verzoegert_phase
        del st.session_state.verzoegert_start

    if tempo == "gegenverhandlung" and not any("430" in m["text"] for m in st.session_state.chat):
        with st.spinner("Kundin tippt..."):
            time.sleep(7)
            add_msg("Kundin", "Wäre 430 € auch möglich?")
            st.rerun()

    if tempo == "gegenverhandlung" and any("430" in m["text"] for m in st.session_state.chat) and not any("bestes" in m["text"] for m in st.session_state.chat):
        time.sleep(0.3)
        add_msg("Sie", f"{int(st.session_state.angebot)} € ist mein bestes Angebot.")
        st.rerun()

    if tempo == "gegenverhandlung" and any("bestes" in m["text"] for m in st.session_state.chat) and not any("Ich stimme" in m["text"] for m in st.session_state.chat):
        with st.spinner("Kundin tippt..."):
            time.sleep(7)
            add_msg("Kundin", "In Ordnung, ich stimme zu.")
            st.session_state.response_time_ms = int((time.time() - st.session_state.start_ts)*1000)
            st.rerun()

    if any(("nehme Ihr Angebot" in m["text"]) or ("Ich stimme" in m["text"]) for m in st.session_state.chat):
        st.success("Die Verhandlung ist abgeschlossen.")
        if st.button("Weiter zum Fragebogen"):
            st.session_state.phase = "survey"
            st.rerun()

# ---------------------------------------------
# PHASE 4: FRAGEBOGEN
# ---------------------------------------------
elif st.session_state.phase == "survey":
    st.subheader("Fragebogen")

    zufriedenheit = st.slider("Wie zufrieden sind Sie mit dem Ergebnis?", 1,7,4)
    fairness = st.slider("Wie fair war die Verhandlung?", 1,7,4)
    bedauern = st.slider("Wie stark empfinden Sie Bedauern über Ihr Angebot?", 1,7,3)
    alter = st.number_input("Alter", 16, 90, 25)
    erfahrung = st.selectbox("Verhandlungserfahrung", ["gering","mittel","hoch"])

    if st.button("Absenden"):
        row = dict(
            ts=datetime.utcnow().isoformat(),
            tempo=st.session_state.tempo,
            batna=st.session_state.batna,
            angebot=int(st.session_state.angebot),
            response_time_ms=st.session_state.response_time_ms,
            zufriedenheit=zufriedenheit,
            fairness=fairness,
            bedauern=bedauern,
            alter=alter,
            erfahrung=erfahrung
        )
        save_row(row)
        st.session_state.phase = "done"
        st.rerun()

# ---------------------------------------------
# PHASE 5: ABSCHLUSS
# ---------------------------------------------
elif st.session_state.phase == "done":
    st.success("Vielen Dank! Ihre Antworten wurden gespeichert.")
    st.markdown("""
**Debriefing:**  
Die Gegenseite war simuliert. Untersucht wird, wie die **Annahmegeschwindigkeit**
die **Zufriedenheit** beeinflusst. Ihre Daten sind anonym.
    """)
