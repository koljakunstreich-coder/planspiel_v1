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
    teams_sheet = sheet.worksheet("Teams")
    all_teams = teams_sheet.get_all_records()
    
    # --- SCHRITT A: Daten für die Berechnung vorbereiten ---
    # Nachfrage-Werte pro Runde (aus deinem Bild)
    nachfrage_liste = {1: 7, 2: 2, 3: 15, 4: 32, 5: 28, 6: 1, 7: 10}
    aktuelle_nachfrage = nachfrage_liste.get(aktuelle_runde, 0)
    
    row_index = None
    alt_bestand = 40 # Standardwert für Runde 1
    alt_kosten = 0

    # Suche das Team und hole die alten Werte
    for i, entry in enumerate(all_teams, start=2):
        if str(entry["TeamID"]) == team_id:
            row_index = i
            # Falls schon Werte im Sheet stehen, nimm diese, sonst Startwerte
            alt_bestand = entry.get("Lagerbestand", 40) if entry.get("Lagerbestand") != "" else 40
            alt_kosten = entry.get("Gesamtkosten", 0) if entry.get("Gesamtkosten") != "" else 0
            break

    if row_index:
        # --- SCHRITT B: Die eigentliche Berechnung ---
        
        # 1. Neuer Bestand vor Verkauf
        bestand_vor_verkauf = alt_bestand + bestellmenge
        
        # 2. Verkäufe berechnen (man kann nicht mehr verkaufen als man hat)
        tatsaechlich_verkauft = min(bestand_vor_verkauf, aktuelle_nachfrage)
        fehlmenge = max(0, aktuelle_nachfrage - bestand_vor_verkauf)
        
        # 3. Neuer Lagerbestand nach Verkauf
        neuer_bestand = bestand_vor_verkauf - tatsaechlich_verkauft
        
        # 4. Kosten berechnen
        kosten_dieser_runde = 0
        if bestellmenge > 0:
            kosten_dieser_runde += 50 # Bestellfixe Kosten
        
        kosten_dieser_runde += (neuer_bestand * 2) # Lagerkosten
        kosten_dieser_runde += (fehlmenge * 100)   # Strafkosten
        
        neue_gesamtkosten = alt_kosten + kosten_dieser_runde

        # --- SCHRITT C: Zurückschreiben ins Google Sheet ---
        # Spalte B=2 (Name), C=3 (Runde), D=4 (Bestellung), E=5 (Bestand), F=6 (Kosten)
        teams_sheet.update_cell(row_index, 2, team_name)
        teams_sheet.update_cell(row_index, 3, aktuelle_runde)
        teams_sheet.update_cell(row_index, 4, bestellmenge)
        teams_sheet.update_cell(row_index, 5, neuer_bestand)
        teams_sheet.update_cell(row_index, 6, neue_gesamtkosten)
        
        st.success(f"Berechnung abgeschlossen für Runde {aktuelle_runde}!")
        st.metric("Neuer Lagerbestand", f"{neuer_bestand} Bikes")
        st.metric("Gesamtkosten", f"{neue_gesamtkosten} €", f"+{kosten_dieser_runde} €")                                  
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
