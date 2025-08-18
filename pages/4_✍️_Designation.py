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
DESIGNATIONS_URL = "https://docs.google.com/spreadsheets/d/1gaPIT5477GOLNfTU0ITwbjNK1TjuO8q-yYN2YasDezg/export?format=xlsx"
SERVICE_ACCOUNT_FILE = 'designation-cle.json'

ROLE_ICONS = {
    "Arbitre de champ": "🧑‍⚖️",
    "Arbitre Assistant 1": "🚩",
    "Arbitre Assistant 2": "🚩",
    "4e/5e arbitre": "📋",
    "Représentant Fédéral": "👔",
    "default": "❓"
}

ALL_ROLES = ["Arbitre de champ", "Arbitre Assistant 1", "Arbitre Assistant 2"]

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

def enregistrer_designation(client, rencontre_details, arbitre_details, dpt_terrain, role):
    try:
        spreadsheet = client.open_by_url(DESIGNATIONS_URL)
        worksheet = spreadsheet.get_worksheet(0)
        nouvelle_ligne = [
            rencontre_details.get("rencontres_date_dt", pd.NaT).strftime("%d/%m/%Y"),
            role,
            arbitre_details.get("Nom", "N/A"),
            arbitre_details.get("Prénom", "N/A"),
            arbitre_details.get("Département de Résidence", "N/A"),
            arbitre_details.get("Numéro Affiliation", "N/A"), # Ajout du numéro de licence
            rencontre_details.get("Structure Organisatrice Nom", "N/A"),
            rencontre_details.get("COMPETITION NOM", "N/A"),
            rencontre_details.get("RENCONTRE NUMERO", "N/A"),
            rencontre_details.get("LOCAUX", "N/A"),
            rencontre_details.get("VISITEURS", "N/A"),
            dpt_terrain
        ]
        worksheet.append_row(nouvelle_ligne)
        return True
    except Exception as e:
        st.error(f"Erreur Google Sheets : {e}")
        return False

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
        if df.empty:
            st.warning(f"La feuille DESIGNATIONS est vide")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erreur de chargement {url} : {str(e)}")
        return pd.DataFrame()

def load_designations_from_sheets():
    try:
        gc = get_gspread_client()
        if gc:
            spreadsheet = gc.open_by_url(DESIGNATIONS_URL)
            worksheet = spreadsheet.get_worksheet(0)
            return pd.DataFrame(worksheet.get_all_records())
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur Google Sheets : {str(e)}")
        return pd.DataFrame()

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
# Chargement via API Google Sheets directement
designations_df = load_designations_from_sheets()
if designations_df.empty:
    # Fallback sur l'ancienne méthode
    designations_df = load_data(DESIGNATIONS_URL)
rencontres_ffr_df = load_data(RENCONTRES_FFR_URL)
dispo_df = load_data(DISPO_URL)
arbitres_df = load_data(ARBITRES_URL)
club_df = load_data(CLUB_URL)

# --- Pré-traitement et Fusion des Données de Désignation ---
for df in [rencontres_df, rencontres_ffr_df, designations_df]:
    if "NUMERO RENCONTRE" in df.columns:
        df.rename(columns={"NUMERO RENCONTRE": "RENCONTRE NUMERO"}, inplace=True)
    if "RENCONTRE NUMERO" in df.columns:
        df["RENCONTRE NUMERO"] = df["RENCONTRE NUMERO"].astype(str)


ffr_cols = {'RENCONTRE NUMERO', 'FONCTION ARBITRE', 'NOM', 'PRENOM', 'DPT DE RESIDENCE'}
manual_cols = {'RENCONTRE NUMERO', 'FONCTION ARBITRE', 'NOM', 'PRENOM', 'DPT DE RESIDENCE'}

# Harmonisation des noms de colonnes dans rencontres_ffr_df
rencontres_ffr_df.rename(columns={
    "NUMERO RENCONTRE": "RENCONTRE NUMERO",
    "Nom": "NOM"
}, inplace=True)



if ffr_cols.issubset(rencontres_ffr_df.columns) and manual_cols.issubset(designations_df.columns):
    designations_combinees_df = pd.concat([
        rencontres_ffr_df[list(ffr_cols)],
        designations_df[list(manual_cols)]
    ], ignore_index=True)
else:
    designations_combinees_df = pd.DataFrame(columns=list(ffr_cols))

if 'rencontres_date_dt' not in rencontres_df.columns: rencontres_df['rencontres_date_dt'] = pd.to_datetime(rencontres_df["DATE EFFECTIVE"], errors='coerce', dayfirst=True)
if 'DATE_dt' not in dispo_df.columns: dispo_df['DATE_dt'] = pd.to_datetime(dispo_df['DATE'], errors='coerce', dayfirst=True)

if 'RENCONTRE NUMERO' in designations_combinees_df.columns and 'FONCTION ARBITRE' in designations_combinees_df.columns:
    roles_par_match = designations_combinees_df.groupby('RENCONTRE NUMERO')['FONCTION ARBITRE'].apply(list).reset_index()
    roles_par_match.rename(columns={'FONCTION ARBITRE': 'ROLES'}, inplace=True)
    rencontres_df = pd.merge(rencontres_df, roles_par_match, on='RENCONTRE NUMERO', how='left')
    rencontres_df['ROLES'] = rencontres_df['ROLES'].apply(lambda x: x if isinstance(x, list) else [])
else:
    rencontres_df['ROLES'] = [[] for _ in range(len(rencontres_df))]

def select_match(match_numero): st.session_state.selected_match = match_numero
#st.write("Contenu de designations_combinees_df :")
#st.dataframe(designations_combinees_df)

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
                
                roles = rencontre.get('ROLES', [])
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
        
        col_refresh, _ = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 Rafraîchir les désignations", help="Met à jour uniquement les désignations manuelles"):
                # Clear le cache pour forcer le rechargement
                st.cache_data.clear()
                # Recharger toutes les données nécessaires
                designations_df = load_data(DESIGNATIONS_URL)
                rencontres_ffr_df = load_data(RENCONTRES_FFR_URL)
                # Reconstruire les données combinées
                if ffr_cols.issubset(rencontres_ffr_df.columns) and manual_cols.issubset(designations_df.columns):
                    designations_combinees_df = pd.concat([
                        rencontres_ffr_df[list(ffr_cols)],
                        designations_df[list(manual_cols)]
                    ], ignore_index=True)
                # Forcer le recalcul des rôles
                roles_par_match = designations_combinees_df.groupby('RENCONTRE NUMERO')['FONCTION ARBITRE'].apply(list).reset_index()
                roles_par_match.rename(columns={'FONCTION ARBITRE': 'ROLES'}, inplace=True)
                rencontre_details = pd.merge(rencontre_details.to_frame().T, roles_par_match, on='RENCONTRE NUMERO', how='left')
                st.rerun()
        
        st.subheader("Désignations Actuelles")
        roles_actuels = rencontre_details.get('ROLES', [])
        if roles_actuels:
            designations_actuelles_df = designations_combinees_df[designations_combinees_df['RENCONTRE NUMERO'].astype(str) == str(selected_match_numero)]
            cols_to_show = ["NOM", "PRENOM", "DPT DE RESIDENCE", "FONCTION ARBITRE"]
            
            # Afficher chaque désignation avec un bouton de suppression si désignation manuelle
            for idx, row in designations_actuelles_df.iterrows():
                col1, col2 = st.columns([4, 1])
                with col1:
                    # Formatage du département sur 2 caractères
                    dpt = str(row['DPT DE RESIDENCE']).zfill(2)[:2]
                    st.write(f"{row['NOM']} {row['PRENOM']} ({dpt}) - {row['FONCTION ARBITRE']}")
                with col2:
                    # Vérifier si c'est une désignation manuelle (présente dans designations_df)
                    is_manual = any(
                        (str(d_row.get('RENCONTRE NUMERO', '')) == str(selected_match_numero) and
                         str(d_row.get('NOM', '')) == str(row['NOM']) and
                         str(d_row.get('PRENOM', '')) == str(row['PRENOM']) and
                         str(d_row.get('FONCTION ARBITRE', '')) == str(row['FONCTION ARBITRE']))
                        for _, d_row in designations_df.iterrows()
                    )
                    if is_manual and st.button("Supprimer", key=f"delete_{idx}"):
                        if st.session_state.get(f"confirm_delete_{idx}", False):
                            # Suppression dans Google Sheets
                            try:
                                gc = get_gspread_client()
                                if gc:
                                    spreadsheet = gc.open_by_url(DESIGNATIONS_URL)
                                    worksheet = spreadsheet.get_worksheet(0)
                                    records = worksheet.get_all_records()
                                    for i, record in enumerate(records, start=2):
                                        if (str(record.get('RENCONTRE NUMERO', '')) == str(selected_match_numero) and \
                                           str(record.get('NOM', '')) == str(row['NOM']) and \
                                           str(record.get('PRENOM', '')) == str(row['PRENOM']) and \
                                           str(record.get('FONCTION ARBITRE', '')) == str(row['FONCTION ARBITRE'])):
                                            worksheet.delete_rows(i)
                                            st.success("Désignation supprimée !")
                                            st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de la suppression : {e}")
                        else:
                            st.session_state[f"confirm_delete_{idx}"] = True
                            st.warning("Confirmez la suppression en cliquant à nouveau")
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

        # Section d'affichage des arbitres
        if arbitres_filtres.empty:
            st.warning("Aucun arbitre trouvé avec les filtres actuels.")
        else:
            st.write(f"{len(arbitres_filtres)} arbitres trouvés")
            
            # Vérification des colonnes requises
            required_columns = ['Nom', 'Prénom', 'Numéro Affiliation', 'Catégorie', 'Niveau']
            if not all(col in arbitres_filtres.columns for col in required_columns):
                st.error(f"Colonnes manquantes dans arbitres_filtres. Requises: {required_columns}")
                st.write("Colonnes disponibles:", arbitres_filtres.columns.tolist())
                st.stop()
            
            # Afficher les arbitres
            roles_disponibles = [role for role in ALL_ROLES if role not in roles_actuels]
            
            for index, arbitre in arbitres_filtres.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([2, 1])
                    
                    # Colonne de gauche - Infos arbitre
                    with col1:
                        # Vérifier si l'arbitre est déjà désigné
                        est_deja_designe = False
                        if not designations_df.empty and 'NUMERO LICENCE' in designations_df.columns:
                            est_deja_designe = not designations_df[designations_df['NUMERO LICENCE'].astype(str) == str(arbitre['Numéro Affiliation'])].empty
                        
                        # Ajout icône JT si applicable
                        jt_icon = " ⚑" if str(arbitre.get('JT', '')).strip().upper() == 'OUI' else ""
                        nom_affichage = f"**{arbitre['Nom']} {arbitre['Prénom']}{jt_icon}**"
                        if est_deja_designe:
                            st.success("✏️ Désignation MANUELLE", icon="✏️")
                            if jt_icon:
                                st.caption("Arbitre JT (Juge de Touche)")
                            # Récupérer les infos de la rencontre où l'arbitre est désigné
                            designation_info = designations_df[
                                (designations_df['NUMERO LICENCE'].astype(str) == str(arbitre['Numéro Affiliation']))
                            ].iloc[0]
                            rencontre_date = pd.to_datetime(designation_info['DATE'], dayfirst=True, errors='coerce')
                            if not pd.isna(rencontre_date):
                                st.caption(f"📅 Désigné le {rencontre_date.strftime('%d/%m/%Y')} sur {designation_info.get('LOCAUX', '?')} vs {designation_info.get('VISITEURS', '?')}")
                        
                        st.write(nom_affichage)
                        st.caption(f"Catégorie : {arbitre['Catégorie']} (Niveau {arbitre['Niveau']}) | Département: {arbitre['Département de Résidence']}")
                    
                    # Colonne de droite - Statut et actions
                    with col2:
                        try:
                            status_text, is_designable = get_arbitre_status_for_date(
                                arbitre['Numéro Affiliation'], 
                                date_rencontre, 
                                dispo_df
                            )
                            
                            if is_designable:
                                st.success(status_text, icon="✅")
                            else:
                                st.warning(status_text, icon="⚠️")
                            
                            if is_designable and roles_disponibles:
                                role_key = f"role_{selected_match_numero}_{arbitre['Numéro Affiliation']}"
                                selected_role = st.selectbox(
                                    "Choisir un rôle", 
                                    options=roles_disponibles, 
                                    key=role_key, 
                                    label_visibility="collapsed"
                                )
                                
                                button_key = f"designate_{selected_match_numero}_{arbitre['Numéro Affiliation']}"
                                if st.button("Valider", key=button_key, use_container_width=True):
                                    if gc:
                                        with st.spinner("Enregistrement..."):
                                            success = enregistrer_designation(gc, rencontre_details, arbitre, dpt_locaux, selected_role)
                                            if success:
                                                st.toast("Désignation enregistrée !", icon="✅")
                                                st.rerun()
                                            else:
                                                st.error("Échec de l'enregistrement.")
                                    else:
                                        st.error("Client Google Sheets non authentifié")
                            elif not roles_disponibles:
                                st.info("Complet")
                        except Exception as e:
                            st.error(f"Erreur lors de l'affichage du statut: {str(e)}")
