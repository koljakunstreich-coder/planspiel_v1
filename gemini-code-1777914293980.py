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
st.title("🚲 Bikes & More Challenge")

mode = st.sidebar.selectbox("Modus", ["Team-Input", "Lehrer-Dashboard"])

if mode == "Team-Input":
    team_id = st.selectbox("Wähle deine Team-Nummer", [f"Team {i}" for i in range(1, 13)])
    
    # GEDÄCHTNIS-LOGIK
    letzter_name = ""
    for entry in reversed(all_data):
        if str(entry.get("TeamID")) == team_id:
            letzter_name = entry.get("Teamname", "")
            break

    team_name = st.text_input("Teamname", value=letzter_name, placeholder="Wird nach Runde 1 automatisch geladen...")
    
    st.divider()
    st.header(f"Runde {aktuelle_runde}")
    bestellmenge = st.number_input("Bestellmenge (Stück):", min_value=0, step=1)

    if st.button("Bestellung absenden"):
        # Vorwerte ermitteln
        alt_bestand = 40
        alt_gesamtkosten = 0
        
        for entry in reversed(all_data):
            current_id = entry.get("TeamID") or entry.get("Team ID")
            if current_id and str(current_id) == team_id:
                alt_bestand = entry.get("Lagerbestand_Ende", 40)
                alt_gesamtkosten = entry.get("Gesamtkosten_kumuliert", 0)
                break
        
        # --- BERECHNUNGSLOGIK ---
        nachfrage_liste = {1: 7, 2: 55, 3: 10, 4: 8, 5: 15, 6: 2, 7: 1}
        aktuelle_nachfrage = nachfrage_liste.get(aktuelle_runde, 0)
        
        bestand_vor_verkauf = alt_bestand + bestellmenge
        tatsaechlich_verkauft = min(bestand_vor_verkauf, aktuelle_nachfrage)
        fehlmenge = max(0, aktuelle_nachfrage - bestand_vor_verkauf)
        neuer_bestand = bestand_vor_verkauf - tatsaechlich_verkauft
        
        # Einzelausweis der Kosten
        fixkosten = 50 if bestellmenge > 0 else 0
        lagerkosten = neuer_bestand * 2
        fehlmengen_kosten = fehlmenge * 100
        
        kosten_diese_runde = fixkosten + lagerkosten + fehlmengen_kosten
        neue_gesamtkosten = alt_gesamtkosten + kosten_diese_runde

        # --- SPEICHERN ---
        # Die Spaltenreihenfolge im Sheet sollte sein: 
        # Runde, TeamID, Teamname, Bestellung, Fixkosten, Lagerkosten, Fehlmengen_Kosten, Bestand_Ende, Kosten_Runde, Gesamtkosten
        neue_zeile = [
            aktuelle_runde, 
            team_id, 
            team_name, 
            bestellmenge, 
            fixkosten, 
            lagerkosten, 
            fehlmengen_kosten, 
            neuer_bestand, 
            kosten_diese_runde, 
            neue_gesamtkosten
        ]
        teams_sheet.append_row(neue_zeile)
        
        st.success(f"Erfolgreich gespeichert! Ihr habt nun {neuer_bestand} Bikes im Lager.")
        st.info(f"Kosten dieser Runde: {fixkosten}€ Fix + {lagerkosten}€ Lager + {fehlmengen_kosten}€ Fehlmenge = {kosten_diese_runde}€")
        st.balloons()

    # Kleiner visueller Abstand
    st.write("---")

    # 2. Der Aktualisieren-Button unter dem Absende-Button
    if st.button("🔄 Neue Runde laden / Daten prüfen"):
        st.rerun()

elif mode == "Lehrer-Dashboard":
    st.header(f"📊 Auswertung Runde {aktuelle_runde}")
    
    if all_data:
        df = pd.DataFrame(all_data)
        st.subheader("Aktueller Stand aller Teams")
        st.dataframe(df)
        
        st.subheader("Finanzielle Entwicklung")
        # Achte darauf, dass der Spaltenname exakt "Gesamtkosten_kumuliert" heißt (oder wie im Sheet vergeben)
        # Falls du die Spalte im Sheet umbenannt hast, passe den Namen hier an:
        y_achse = "Gesamtkosten_kumuliert" if "Gesamtkosten_kumuliert" in df.columns else "Gesamtkosten"
        st.line_chart(df, x="Runde", y=y_achse, color="TeamID")
    else:
        st.info("Warten auf erste Abgaben der Teams...")

    st.divider()
    if st.button("Nächste Runde freischalten"):
        control_sheet.update(range_name='A1', values=[[aktuelle_runde + 1]])
        st.success(f"Runde {aktuelle_runde + 1} wurde gestartet!")
        st.rerun()
