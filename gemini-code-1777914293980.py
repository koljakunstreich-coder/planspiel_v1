import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# 1. Verbindung zu Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("dein_google_key.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Planspiel_Daten")

# 2. Lehrer-Steuerung auslesen
control_sheet = sheet.worksheet("Steuerung")
aktuelle_runde = int(control_sheet.acell('A1').value)

# 3. UI Design
st.title("🚲 E-Bike Startup Challenge")

mode = st.sidebar.selectbox("Modus", ["Team-Input", "Lehrer-Dashboard"])

if mode == "Team-Input":
    team_id = st.selectbox("Wähle dein Team", [f"Team {i}" for i in range(1, 13)])
    team_name = st.text_input("Startup Name", placeholder="z.B. GreenWheels")
    
    st.header(f"Runde {aktuelle_runde}")
    st.write(f"Willkommen {team_name if team_name else team_id}!")
    
    bestellmenge = st.number_input("Bestellmenge für die nächste Woche:", min_value=0, step=1)
    
    if st.button("Bestellung absenden"):
        # Daten in Google Sheet schreiben
        teams_sheet = sheet.worksheet("Teams")
        # Hier Logik einfügen, um die Zeile des Teams zu finden und die Menge zu speichern
        st.success("Daten wurden in die Google Tabelle übertragen!")

elif mode == "Lehrer-Dashboard":
    st.header("📊 Live-Auswertung (Beamer-Ansicht)")
    # Daten aus Google Sheets laden und als Tabelle/Grafik anzeigen
    data = sheet.worksheet("Teams").get_all_records()
    df = pd.DataFrame(data)
    st.table(df)
    
    if st.button("Nächste Runde freischalten"):
        control_sheet.update('A1', aktuelle_runde + 1)
        st.rerun()