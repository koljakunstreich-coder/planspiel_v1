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
# 1. Wir suchen zuerst, ob das Team schon einmal einen Namen abgegeben hat
letzter_name = ""
if all_data: # all_data sind die bisherigen Einträge aus dem Sheet "Teams"
    for entry in reversed(all_data):
        if str(entry.get("TeamID")) == team_id:
            letzter_name = entry.get("Teamname", "")
            break

# 2. Das Eingabefeld für den Namen
# Falls schon ein Name existiert, wird dieser als Standardwert (value) gesetzt
team_name = st.text_input("Startup Name", value=letzter_name, placeholder="z.B. GreenWheels")

if st.button("Bestellung absenden"):
    # ... (hier folgt dein restlicher Code zum Berechnen und Speichern)
    
    # Beim Speichern nutzen wir nun den 'team_name' (egal ob neu getippt oder übernommen)
    neue_zeile = [aktuelle_runde, team_id, team_name, bestellmenge, neuer_bestand, kosten_diese_runde, neue_gesamtkosten]
    teams_sheet.append_row(neue_zeile)
    
    # Standardwerte für die erste Runde
    alt_bestand = 40
    alt_gesamtkosten = 0
    
    # Wir gehen die Daten rückwärts durch, um den aktuellsten Stand zu finden
    for entry in reversed(all_data):
        # .get() verhindert den KeyError. Es sucht nach 'TeamID' (Groß-/Kleinschreibung beachten!)
        # Falls du im Sheet "Team ID" (mit Leerzeichen) geschrieben hast, ändere es hier auch.
        current_id = entry.get("TeamID") or entry.get("Team ID") or entry.get("teamid")
        
        if current_id and str(current_id) == team_id:
            # Falls die Spaltennamen im Sheet anders sind, hier ebenfalls anpassen
            alt_bestand = entry.get("Lagerbestand_Ende", 40)
            alt_gesamtkosten = entry.get("Gesamtkosten_kumuliert", 0)
            break
        

    # 2. Berechnung (wie gehabt)
    nachfrage_liste = {1: 7, 2: 5, 3: 10, 4: 8, 5: 15, 6: 2, 7: 1} # Beispielwerte
    aktuelle_nachfrage = nachfrage_liste.get(aktuelle_runde, 0)
    
    bestand_vor_verkauf = alt_bestand + bestellmenge
    tatsaechlich_verkauft = min(bestand_vor_verkauf, aktuelle_nachfrage)
    fehlmenge = max(0, aktuelle_nachfrage - bestand_vor_verkauf)
    neuer_bestand = bestand_vor_verkauf - tatsaechlich_verkauft
    
    kosten_diese_runde = (50 if bestellmenge > 0 else 0) + (neuer_bestand * 2) + (fehlmenge * 100)
    neue_gesamtkosten = alt_gesamtkosten + kosten_diese_runde

    # 3. DATEN ANHÄNGEN (Erzeugt für jede Runde eine neue Zeile)
    # Reihenfolge: Runde, TeamID, Teamname, Bestellung, Bestand, Kosten_Runde, Gesamtkosten
    neue_zeile = [aktuelle_runde, team_id, team_name, bestellmenge, neuer_bestand, kosten_diese_runde, neue_gesamtkosten]
    teams_sheet.append_row(neue_zeile)
    
    st.success(f"Runde {aktuelle_runde} für {team_id} gespeichert!")                                 
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
    st.header(f"Ergebnisse Runde {aktuelle_runde}")
    
    # Daten laden
    df = pd.DataFrame(sheet.worksheet("Teams").get_all_records())
    
    if not df.empty:
        # Nur Daten der aktuellen Runde filtern
        aktuelle_daten = df[df['Runde'] == aktuelle_runde]
        st.table(aktuelle_daten)
        
        # Ein Liniendiagramm über den Kostenverlauf aller Runden
        st.subheader("Kostenentwicklung")
        st.line_chart(df, x="Runde", y="Gesamtkosten_kumuliert", color="TeamID")
