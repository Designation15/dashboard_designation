import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os
from utils import (
    get_department_from_club_name_or_code,
    get_cp_from_club_name_or_code,
    highlight_designated_cells,
    extract_club_code_from_team_string,
    extract_club_name_from_team_string
)

# --- Configuration et chargement des données ---
RENCONTRES_URL = "https://docs.google.com/spreadsheets/d/1I8RGfNNdaO1wlrtFgIOFbOnzpKszwJTxdyhQ7rRD1bg/export?format=xlsx"
RENCONTRES_FFR_URL = "https://docs.google.com/spreadsheets/d/1ViKipszuqE5LPbTcFk2QvmYq4ZNQZVs9LbzrUVC4p4Y/export?format=xlsx"
DISPO_URL = "https://docs.google.com/spreadsheets/d/16-eSHsURF-H1zWx_a_Tu01E9AtmxjIXocpiR2t2ZNU4/export?format=xlsx"
ARBITRES_URL = "https://docs.google.com/spreadsheets/d/1bIUxD-GDc4V94nYoI_x2mEk0i_r9Xxnf02_Rn9YtoIc/export?format=xlsx"
CLUB_URL = "https://docs.google.com/spreadsheets/d/1GLWS4jOmwv-AOtkFZ5-b5JcjaSpBVlwqcuOCRRmEVPQ/export?format=xlsx"
DESIGNATIONS_URL = "https://docs.google.com/spreadsheets/d/1gaPIT5477GOLNfTU0ITwbjNK1TjuO8q-yYN2YasDezg/edit#gid=0"
SERVICE_ACCOUNT_FILE = 'designation-cle.json'

ROLE_ICONS = {
    "Arbitre de champ": "🧑‍⚖️",
    "Juge de touche 1": "🚩",
    "Juge de touche 2": "🚩",
    "4e/5e arbitre": "📋",
    "Représentant Fédéral": "👔",
    "default": "❓"
}

# --- Fonctions (inchangées) ---
@st.cache_resource(ttl=3600)
def get_gspread_client():
    try:
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        elif "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        else: return None
        return gspread.authorize(creds)
    except Exception: return None

def enregistrer_designation(client, rencontre_details, arbitre_details, dpt_terrain):
    try:
        spreadsheet = client.open_by_url(DESIGNATIONS_URL)
        worksheet = spreadsheet.get_worksheet(0)
        nouvelle_ligne = [
            rencontre_details.get("rencontres_date_dt", pd.NaT).strftime("%d/%m/%Y"),
            "Arbitre de champ",
            arbitre_details.get("Nom", "N/A"),
            arbitre_details.get("Prénom", "N/A"),
            arbitre_details.get("Département de Résidence", "N/A"), # DPT DE RESIDENCE
            arbitre_details.get("Numéro Affiliation", "N/A"), # NUMERO LICENCE
            rencontre_details.get("Structure Organisatrice Nom", "N/A"),
            rencontre_details.get("COMPETITION NOM", "N/A"),
            rencontre_details.get("RENCONTRE NUMERO", "N/A"),
            rencontre_details.get("LOCAUX", "N/A"),
            rencontre_details.get("VISITEURS", "N/A"),
            dpt_terrain
        ]
        worksheet.append_row(nouvelle_ligne)
        return True
    except Exception: return False

@st.cache_data
def load_static_data():
    categories_data = {
        'Niveau': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        'CATEGORIE': ['Internationaux', '2ème Division PRO', 'Nationale 1 et 2', 'Arbitres assistants PRO', 'Arbitres assistants NAT', 'Divisionnaires 1', 'Divisionnaires 2', 'Divisionnaires 3', 'Ligue 1', 'Ligue 2', 'Ligue 3', 'Ligue 4', 'Ligue 5', 'Mineurs 17 ans', 'Mineurs 16 ans', 'Mineurs 15 ans']
    }
    categories_df = pd.DataFrame(categories_data)
    competitions_data = {
        'NOM': ['Elite 1 Féminine', 'Elite 2 Féminine', 'Elite Alamercery', 'Elite Crabos', 'Espoirs Fédéraux', 'European Rugby Champions Cup', 'Excellence B - Championnat de France', 'Fédérale 1', 'Fédérale 2', 'Fédérale 3', 'Fédérale B - Championnat de France', 'Féminines Moins de 18 ans à XV - ELITE', 'Féminines Régionales à X', 'Féminines Régionales à X « moins de 18 ans »', 'Régional 1 U16', 'Régional 1 U19', 'Régional 2 U16', 'Régional 2 U19', 'Régional 3 U16', 'Régional 3 U19', 'Régionale 1 - Championnat Territorial', 'Régionale 2 - Championnat Territorial', 'Régionale 3 - Championnat Territorial', 'Réserves Elite', 'Réserves Régionales 1 - Championnat Territorial', 'Réserves Régionales 2 - Championnat Territorial'],
        'NIVEAU MIN': [6, 7, 7, 6, 6, 1, 9, 6, 7, 8, 9, 7, 13, 14, 15, 10, 15, 13, 15, 13, 9, 11, 13, 7, 11, 13],
        'NIVEAU MAX': [4, 6, 6, 4, 4, 1, 7, 6, 7, 8, 7, 6, 10, 13, 9, 9, 9, 9, 9, 9, 7, 9, 9, 9, 9, 11]
    }
    competitions_df = pd.DataFrame(competitions_data)
    return categories_df, competitions_df

@st.cache_data
def load_data(url):
    try:
        df = pd.read_excel(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception: return pd.DataFrame()

def get_arbitre_status_for_date(arbitre_affiliation, match_date, dispo_df):
    start_of_week = match_date - timedelta(days=match_date.weekday())
    saturday = start_of_week + timedelta(days=5)
    sunday = start_of_week + timedelta(days=6)
    weekend_dispo = dispo_df[(dispo_df['NO LICENCE'] == arbitre_affiliation) & (dispo_df['DATE_dt'].dt.date >= saturday.date()) & (dispo_df['DATE_dt'].dt.date <= sunday.date())]
    if weekend_dispo.empty: return "🤷‍♂️ Non renseignée", False
    match_day_status = weekend_dispo[weekend_dispo['DATE_dt'].dt.date == match_date.date()]
    if not match_day_status.empty:
        designation_val = match_day_status.iloc[0].get('DESIGNATION')
        designation_str = str(designation_val).strip()
        if pd.notna(designation_val) and designation_str != '' and designation_str != '0': return f"❌ Déjà désigné(e) sur : {designation_val}", False
    available_keywords = ['oui', 'we', 'samedi', 'dimanche']
    is_available = any(any(keyword in str(row.get('DISPONIBILITE', '')).lower() for keyword in available_keywords) for index, row in weekend_dispo.iterrows())
    if is_available: return "✅ Disponible", True
    else: return f"❓ Non disponible ({weekend_dispo.iloc[0].get('DISPONIBILITE', '')})", False

# --- Initialisation & Chargement ---
st.set_page_config(layout="wide")
st.title("✍️ Outil de Désignation Interactif")

if 'selected_match' not in st.session_state: st.session_state.selected_match = None
if 'previous_competition' not in st.session_state: st.session_state.previous_competition = None

gc = get_gspread_client()
categories_df, competitions_df = load_static_data()
rencontres_df = load_data(RENCONTRES_URL)
rencontres_ffr_df = load_data(RENCONTRES_FFR_URL)
dispo_df = load_data(DISPO_URL)
arbitres_df = load_data(ARBITRES_URL)
club_df = load_data(CLUB_URL)

# --- Pré-traitement des données ---
if "NUMERO DE RENCONTRE" in rencontres_df.columns:
    rencontres_df.rename(columns={"NUMERO DE RENCONTRE": "RENCONTRE NUMERO"}, inplace=True)
if 'rencontres_date_dt' not in rencontres_df.columns: rencontres_df['rencontres_date_dt'] = pd.to_datetime(rencontres_df["DATE EFFECTIVE"], errors='coerce', dayfirst=True)
if 'DATE_dt' not in dispo_df.columns: dispo_df['DATE_dt'] = pd.to_datetime(dispo_df['DATE'], errors='coerce', dayfirst=True)

if 'NUMERO RENCONTRE' in rencontres_ffr_df.columns and 'FONCTION ARBITRE' in rencontres_ffr_df.columns and 'RENCONTRE NUMERO' in rencontres_df.columns:
    roles_par_match = rencontres_ffr_df.groupby('NUMERO RENCONTRE')['FONCTION ARBITRE'].apply(list).reset_index()
    roles_par_match.rename(columns={'FONCTION ARBITRE': 'ROLES_FFR'}, inplace=True)
    rencontres_df['RENCONTRE NUMERO'] = rencontres_df['RENCONTRE NUMERO'].astype(str)
    roles_par_match['NUMERO RENCONTRE'] = roles_par_match['NUMERO RENCONTRE'].astype(str)
    rencontres_df = pd.merge(rencontres_df, roles_par_match, left_on='RENCONTRE NUMERO', right_on='NUMERO RENCONTRE', how='left')
    rencontres_df['ROLES_FFR'] = rencontres_df['ROLES_FFR'].apply(lambda x: x if isinstance(x, list) else [])
else:
    rencontres_df['ROLES_FFR'] = [[] for _ in range(len(rencontres_df))]

def select_match(match_numero): st.session_state.selected_match = match_numero

# --- Interface --- 
left_col, right_col = st.columns([2, 3])

with left_col:
    st.header("🗓️ Liste des Rencontres")
    competition_options = ["Toutes"] + sorted(competitions_df['NOM'].unique().tolist())
    competition_nom = st.selectbox("Filtrer par compétition", options=competition_options)
    
    if st.session_state.previous_competition != competition_nom:
        st.session_state.selected_match = None
        st.session_state.previous_competition = competition_nom

    if competition_nom == "Toutes":
        rencontres_filtrees_df = rencontres_df.copy()
        rencontres_filtrees_df = rencontres_filtrees_df.sort_values(by=['COMPETITION NOM', 'rencontres_date_dt'])
    else:
        rencontres_filtrees_df = rencontres_df[rencontres_df["COMPETITION NOM"] == competition_nom].copy()
        rencontres_filtrees_df = rencontres_filtrees_df.sort_values(by='rencontres_date_dt')
    
    unique_matches_df = rencontres_filtrees_df.drop_duplicates(subset=['RENCONTRE NUMERO'])

    if unique_matches_df.empty:
        st.warning("Aucune rencontre trouvée.")
    else:
        for index, rencontre in unique_matches_df.iterrows():
            with st.container(border=True):
                if competition_nom == "Toutes":
                    st.caption(rencontre['COMPETITION NOM'])
                st.subheader(f"{rencontre['LOCAUX']} vs {rencontre['VISITEURS']}")
                st.caption(f"{rencontre['rencontres_date_dt'].strftime('%d/%m/%Y')}")
                
                roles = rencontre.get('ROLES_FFR', [])
                if roles:
                    icon_str = " ".join([ROLE_ICONS.get(role, ROLE_ICONS['default']) for role in roles])
                    st.markdown(f"**Rôles pourvus :** {icon_str}")
                
                st.button("Sélectionner", key=f"select_{rencontre['RENCONTRE NUMERO']}", on_click=select_match, args=(rencontre['RENCONTRE NUMERO'],))

with right_col:
    if 'selected_match' not in st.session_state or st.session_state.selected_match is None:
        st.info("⬅️ Sélectionnez un match dans la liste de gauche pour commencer.")
    else:
        selected_match_numero = st.session_state.selected_match
        rencontre_details = rencontres_df[rencontres_df['RENCONTRE NUMERO'] == selected_match_numero].iloc[0]
        date_rencontre = rencontre_details['rencontres_date_dt']

        st.header(f"🎯 {rencontre_details['LOCAUX']} vs {rencontre_details['VISITEURS']}")
        
        st.subheader("Désignations Actuelles")
        if 'NUMERO RENCONTRE' in rencontres_ffr_df.columns:
            designations_actuelles_df = rencontres_ffr_df[rencontres_ffr_df['NUMERO RENCONTRE'].astype(str) == str(selected_match_numero)]
            if not designations_actuelles_df.empty:
                cols_to_show = ["Nom", "PRENOM", "DPT DE RESIDENCE", "FONCTION ARBITRE"]
                existing_cols = [col for col in cols_to_show if col in designations_actuelles_df.columns]
                st.dataframe(designations_actuelles_df[existing_cols], hide_index=True, use_container_width=True)
            else:
                st.info("Aucune désignation existante pour ce match.")
        st.divider()

        st.subheader("Options de Filtrage")
        filter_mode = st.radio("Choisir le mode de filtrage :", ("Filtres stricts (recommandé)", "Aucun filtre (sauf appartenance club)"), horizontal=True)
        st.divider()

        st.subheader("Chercher un Arbitre")

        # --- Processus de filtrage ---
        locaux_code = extract_club_code_from_team_string(rencontre_details["LOCAUX"])
        visiteurs_code = extract_club_code_from_team_string(rencontre_details["VISITEURS"])
        arbitres_filtres = arbitres_df[~arbitres_df['Code Club'].astype(str).isin([str(locaux_code), str(visiteurs_code)])]

        # Toujours fusionner pour avoir la colonne 'Niveau' disponible pour le tri
        arbitres_filtres = pd.merge(arbitres_filtres, categories_df, left_on='Catégorie', right_on='CATEGORIE', how='left')

        if filter_mode == "Filtres stricts (recommandé)":
            competition_info = competitions_df[competitions_df['NOM'] == rencontre_details["COMPETITION NOM"]].iloc[0]
            niveau_min, niveau_max = (competition_info['NIVEAU MIN'], competition_info['NIVEAU MAX'])
            if niveau_min > niveau_max: niveau_min, niveau_max = niveau_max, niveau_min
            arbitres_filtres = arbitres_filtres[arbitres_filtres['Niveau'].between(niveau_min, niveau_max)]

            dpt_locaux = get_department_from_club_name_or_code(rencontre_details["LOCAUX"], club_df, {"club_nom": "Nom", "club_code": "Code", "club_dpt": "DPT", "club_cp": "CP"})
            if dpt_locaux and dpt_locaux != "Non trouvé":
                arbitres_filtres = arbitres_filtres[arbitres_filtres['Département de Résidence'].astype(str) != str(dpt_locaux)]

        arbitres_filtres = arbitres_filtres.sort_values(by='Niveau', ascending=True)

        if arbitres_filtres.empty:
            st.warning("Aucun arbitre trouvé avec les filtres actuels.")
        else:
            st.write(f"{len(arbitres_filtres)} arbitres trouvés :")
            for index, arbitre in arbitres_filtres.iterrows():
                status_text, is_designable = get_arbitre_status_for_date(arbitre['Numéro Affiliation'], date_rencontre, dispo_df)
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"**{arbitre['Nom']} {arbitre['Prénom']}**")
                        st.caption(f"Catégorie : {arbitre.get('Catégorie', 'N/A')} (Niveau {arbitre.get('Niveau', 'N/A')})")
                    with col2:
                        if is_designable: st.success(status_text, icon="✅")
                        else: st.warning(status_text, icon="⚠️")
                    with col3:
                        button_key = f"designate_{selected_match_numero}_{arbitre['Numéro Affiliation']}"
                        if st.button("Désigner", key=button_key, disabled=not is_designable, use_container_width=True):
                            if gc:
                                with st.spinner("Enregistrement..."):
                                    success = enregistrer_designation(gc, rencontre_details, arbitre, dpt_locaux)
                                    if success: st.success("Désignation enregistrée !"); st.rerun()
                                    else: st.error("Échec de l'enregistrement.")
                            else: st.error("Client Google Sheets non authentifié.")