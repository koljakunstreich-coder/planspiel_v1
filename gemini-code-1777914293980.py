import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# 1. Verbindung zu Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# 1. Definiere den Zugriffsbereich (Scope)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# 2. Lade die Daten aus den Streamlit Secrets (statt aus einer Datei)
# Wichtig: Der Name ["gcp_service_account"] muss exakt so in deinen Secrets stehen
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

# 3. Autorisiere den Client
client = gspread.authorize(creds)
sheet = client.open("Planspiel_Daten")

# 2. Lehrer-Steuerung auslesen
control_sheet = sheet.worksheet("Steuerung")
# Den Wert aus A1 holen
cell_value = control_sheet.acell('A1').value

# Prüfen, ob die Zelle leer ist oder keine Zahl enthält
if cell_value is None or not str(cell_value).isdigit():
    st.warning("Achtung: In Zelle A1 von 'Steuerung' wurde keine gültige Zahl gefunden. Standardwert 1 wird genutzt.")
    aktuelle_runde = 1
else:
    aktuelle_runde = int(cell_value)

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
        # Ab hier MUSS alles eingerückt sein (4 Leerzeichen oder 1 Tab)
        teams_sheet = sheet.worksheet("Teams")
        
        # Daten für die Suche laden
        all_teams = teams_sheet.get_all_records()
        
        row_index = None
        for i, entry in enumerate(all_teams, start=2):
            if entry["TeamID"] == team_id:
                row_index = i
                break
                
        if row_index:
            # Auch diese Zeilen müssen eingerückt sein
            teams_sheet.update_cell(row_index, 2, team_name)
            teams_sheet.update_cell(row_index, 3, aktuelle_runde)
            teams_sheet.update_cell(row_index, 4, bestellmenge)
            st.success(f"Daten für {team_id} gespeichert!")
        else:
            st.error("TeamID nicht gefunden!")
# Ab hier wäre der Code wieder auf der Ebene des 'if', falls noch etwas kommt
elif mode == "Lehrer-Dashboard":
    st.header("📊 Live-Auswertung (Beamer-Ansicht)")
    # Daten aus Google Sheets laden und als Tabelle/Grafik anzeigen
    data = sheet.worksheet("Teams").get_all_records()
    df = pd.DataFrame(data)
    st.table(df)
    
    if st.button("Nächste Runde freischalten"):
       # Wir packen den Wert in doppelte Klammern [[...]], um eine "Tabelle" zu simulieren
        control_sheet.update(range_name='A1', values=[[aktuelle_runde + 1]])
        st.rerun()
if mode == "Lehrer-Dashboard":
    neue_runde = st.number_input("Runde manuell setzen", value=aktuelle_runde)
    if st.button("Runde in Google Sheets aktualisieren"):
        control_sheet.update('A1', [[neue_runde]]) # Doppelte Klammern für Google API
        st.success(f"Runde wurde auf {neue_runde} gesetzt!")
        st.rerun()
