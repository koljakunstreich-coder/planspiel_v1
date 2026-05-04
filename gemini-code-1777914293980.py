import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# --- 1. VERBINDUNG ZU GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Planspiel_Daten")

# Worksheets definieren
teams_sheet = sheet.worksheet("Teams")
control_sheet = sheet.worksheet("Steuerung")

# --- 2. DATEN VORAB LADEN ---
try:
    # Wir laden die Daten frisch, damit der "Gedächtnis-Effekt" sofort eintritt
    all_data = teams_sheet.get_all_records()
except:
    all_data = []

# Lehrer-Steuerung (aktuelle Runde) auslesen
cell_value = control_sheet.acell('A1').value
if cell_value is None or not str(cell_value).isdigit():
    aktuelle_runde = 1
else:
    aktuelle_runde = int(cell_value)

# --- 3. UI DESIGN ---
st.title("🚲 E-Bike Startup Challenge")
mode = st.sidebar.selectbox("Modus", ["Team-Input", "Lehrer-Dashboard"])

if mode == "Team-Input":
    # Auswahl der TeamID (Konstante ID über das ganze Spiel)
    team_id = st.selectbox("Wähle deine Team-Nummer", [f"Team {i}" for i in range(1, 13)])
    
    # GEDÄCHTNIS-LOGIK:
    # Wir suchen den Namen, den dieses Team zuletzt benutzt hat
    letzter_name = ""
    for entry in reversed(all_data):
        if str(entry.get("TeamID")) == team_id:
            letzter_name = entry.get("Teamname", "")
            break

    # Das Namensfeld wird mit dem gefundenen Namen vorausgefüllt
    team_name = st.text_input("Startup Name", value=letzter_name, placeholder="Wird nach Runde 1 automatisch geladen...")
    
    st.divider()
    st.header(f"Runde {aktuelle_runde}")
    bestellmenge = st.number_input("Bestellmenge (Stück):", min_value=0, step=1)

    if st.button("Bestellung absenden"):
        # Aktuelle Werte für dieses Team aus der Vorrunde ermitteln
        alt_bestand = 40
        alt_gesamtkosten = 0
        
        for entry in reversed(all_data):
            # Flexibler Spaltenzugriff
            current_id = entry.get("TeamID") or entry.get("Team ID")
            if current_id and str(current_id) == team_id:
                alt_bestand = entry.get("Lagerbestand_Ende", 40)
                alt_gesamtkosten = entry.get("Gesamtkosten_kumuliert", 0)
                break
        
        # --- BERECHNUNGSLOGIK ---
        nachfrage_liste = {1: 7, 2: 5, 3: 10, 4: 8, 5: 15, 6: 2, 7: 1}
        aktuelle_nachfrage = nachfrage_liste.get(aktuelle_runde, 0)
        
        bestand_vor_verkauf = alt_bestand + bestellmenge
        tatsaechlich_verkauft = min(bestand_vor_verkauf, aktuelle_nachfrage)
        fehlmenge = max(0, aktuelle_nachfrage - bestand_vor_verkauf)
        neuer_bestand = bestand_vor_verkauf - tatsaechlich_verkauft
        
        kosten_diese_runde = (50 if bestellmenge > 0 else 0) + (neuer_bestand * 2) + (fehlmenge * 100)
        neue_gesamtkosten = alt_gesamtkosten + kosten_diese_runde

        # --- SPEICHERN ---
        # Der team_name wird hier wieder mitgespeichert, damit er in der nächsten Runde 
        # über 'reversed(all_data)' wiedergefunden wird.
        neue_zeile = [aktuelle_runde, team_id, team_name, bestellmenge, neuer_bestand, kosten_diese_runde, neue_gesamtkosten]
        teams_sheet.append_row(neue_zeile)
        
        st.success(f"Erfolgreich gespeichert! Ihr habt nun {neuer_bestand} Bikes im Lager.")
        st.balloons()

elif mode == "Lehrer-Dashboard":
    st.header(f"📊 Auswertung Runde {aktuelle_runde}")
    
    if all_data:
        df = pd.DataFrame(all_data)
        
        # Nur die aktuellsten Daten pro Team für die Tabelle anzeigen
        st.subheader("Aktueller Stand aller Teams")
        st.dataframe(df)
        
        # Kostenverlauf-Grafik
        st.subheader("Finanzielle Entwicklung")
        st.line_chart(df, x="Runde", y="Gesamtkosten_kumuliert", color="TeamID")
    else:
        st.info("Warten auf erste Abgaben der Teams...")

    st.divider()
    if st.button("Nächste Runde freischalten"):
        control_sheet.update(range_name='A1', values=[[aktuelle_runde + 1]])
        st.success(f"Runde {aktuelle_runde + 1} wurde gestartet!")
        st.rerun()
