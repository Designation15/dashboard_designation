import re
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import timedelta
import config

@st.cache_data
def load_data(url):
    """
    Charge des données depuis une URL Excel, avec gestion du cache et des erreurs.
    """
    try:
        df = pd.read_excel(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Impossible de charger les données depuis {url}. Erreur: {e}")
        return pd.DataFrame()

@st.cache_resource(ttl=3600)
def get_gspread_client():
    try:
        if os.path.exists(config.SERVICE_ACCOUNT_FILE):
            creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        elif "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        else: return None
        return gspread.authorize(creds)
    except Exception: return None

def enregistrer_designation(client, designation_url, rencontre_details, arbitre_details, dpt_terrain, role):
    try:
        spreadsheet = client.open_by_url(designation_url)
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

def load_designations_from_sheets(client, designation_url):
    try:
        if client:
            spreadsheet = client.open_by_url(designation_url)
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

def update_google_sheet(client, sheet_url, df_new):
    try:
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.get_worksheet(0)
        worksheet.clear()
        for col in df_new.select_dtypes(include=['datetime64', 'datetime64[ns]']).columns:
            df_new[col] = df_new[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        data_to_write = df_new.astype(object).where(pd.notna(df_new), None).values.tolist()
        worksheet.update([df_new.columns.values.tolist()] + data_to_write)
        st.success(f"Feuille Google Sheet mise à jour avec succès pour l'URL : {sheet_url}")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Erreur : Feuille Google Sheet introuvable pour l'URL : {sheet_url}. Vérifiez l'ID et les permissions.")
        return False
    except gspread.exceptions.APIError as e:
        st.error(f"Erreur API Google Sheets lors de la mise à jour ({sheet_url}) : {e.response.text}")
        return False
    except Exception as e:
        st.error(f"Erreur inattendue lors de la mise à jour de la feuille Google Sheet ({sheet_url}) : {e}")
        return False

def clear_sheet_except_header(client, sheet_url):
    try:
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.get_worksheet(0)
        header = worksheet.row_values(1)
        worksheet.clear()
        worksheet.update([header])
        st.success(f"Toutes les lignes (sauf l'en-tête) ont été effacées de la feuille : {sheet_url}")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Erreur : Feuille Google Sheet introuvable pour l'URL : {sheet_url}. Vérifiez l'ID et les permissions.")
        return False
    except gspread.exceptions.APIError as e:
        st.error(f"Erreur API Google Sheets lors de l'effacement ({sheet_url}) : {e.response.text}")
        return False
    except Exception as e:
        st.error(f"Erreur inattendue lors de l'effacement de la feuille Google Sheet ({sheet_url}) : {e}")
        return False

def extract_club_name_from_team_string(team_string):
    """
    Extrait le nom du club d'une chaîne d'équipe (sans le code entre parenthèses)
    Ex: "STADE ROCHELAIS (SRO)" -> "STADE ROCHELAIS"
    """
    match = re.search(r'^(.*?)\s*(\(\w+\))?$', str(team_string))
    if match:
        return match.group(1).strip()
    return str(team_string).strip()

def extract_club_code_from_team_string(team_string):
    """
    Extrait le code club entre parenthèses d'une chaîne d'équipe
    Ex: "STADE ROCHELAIS (SRO)" -> "SRO"
    Ex: "A C BOBIGNY 93 RUGBY (4581E)" -> "4581E"
    """
    match = re.search(r'\((.*?)\)', str(team_string))
    if match:
        return match.group(1).strip()
    return None

def get_department_from_club_name(club_name_full, club_df, column_mapping):
    """
    Récupère le département à partir du nom du club (méthode originale)
    """
    extracted_name = extract_club_name_from_team_string(club_name_full)
    club_df[column_mapping['club_nom']] = club_df[column_mapping['club_nom']].astype(str)
    matching_clubs = club_df[club_df[column_mapping['club_nom']].str.contains(extracted_name, case=False, na=False)]
    if not matching_clubs.empty:
        # Prioritize exact match if available
        exact_match = matching_clubs[matching_clubs[column_mapping['club_nom']] == extracted_name]
        if not exact_match.empty:
            best_match = exact_match.iloc[0]
        else:
            # If no exact match, use the longest name as a heuristic
            best_match = matching_clubs.loc[matching_clubs[column_mapping['club_nom']].str.len().idxmax()]
        
        cp = str(best_match[column_mapping['club_cp']])
        if len(cp) >= 2:
            return cp[:2]
    return "Non trouvé"

def get_department_from_club_code(club_code, club_df, column_mapping):
    """
    Récupère le département à partir du code club (nouvelle méthode plus précise)
    """
    if not club_code:
        return None
    
    # La colonne du code club dans club_df est 'Code'
    club_code_col = 'Code' # As specified by user
    if club_code_col not in club_df.columns:
        return None
    
    # Recherche par code club exact
    matching_club = club_df[club_df[column_mapping['club_code']] == club_code]
    
    if not matching_club.empty:
        cp = str(matching_club.iloc[0][column_mapping['club_cp']])
        if len(cp) >= 2:
            return cp[:2]
    return None

def get_department_from_club_name_or_code(club_name_full, club_df, column_mapping):
    """
    Fonction combinée qui essaie d'abord par code, puis par nom
    """
    # Tentative 1 : Par code club
    club_code = extract_club_code_from_team_string(club_name_full)
    if club_code:
        dept_by_code = get_department_from_club_code(club_code, club_df, column_mapping)
        if dept_by_code:
            return dept_by_code
    
    # Tentative 2 : Par nom (fallback)
    return get_department_from_club_name(club_name_full, club_df, column_mapping)

def get_cp_from_club_name(club_name_full, club_df, column_mapping):
    """
    Récupère le code postal complet à partir du nom du club
    """
    extracted_name = extract_club_name_from_team_string(club_name_full)
    club_df[column_mapping['club_nom']] = club_df[column_mapping['club_nom']].astype(str)
    matching_clubs = club_df[club_df[column_mapping['club_nom']].str.contains(extracted_name, case=False, na=False)]
    if not matching_clubs.empty:
        best_match = matching_clubs.loc[matching_clubs[column_mapping['club_nom']].str.len().idxmax()]
        return str(best_match[column_mapping['club_cp']])
    return "Non trouvé"

def get_cp_from_club_code(club_code, club_df, column_mapping):
    """
    Récupère le code postal complet à partir du code club
    """
    if not club_code:
        return "Non trouvé"
    
    club_code_col = 'Code' # As specified by user
    if club_code_col not in club_df.columns:
        return "Non trouvé"
    
    # Recherche par code club exact
    matching_club = club_df[club_df[column_mapping['club_code']] == club_code]
    
    if not matching_club.empty:
        return str(matching_club.iloc[0][column_mapping['club_cp']])
    return "Non trouvé"

def get_cp_from_club_name_or_code(club_name_full, club_df, column_mapping):
    """
    Fonction combinée pour récupérer le CP qui essaie d'abord par code, puis par nom
    """
    # Tentative 1 : Par code club
    club_code = extract_club_code_from_team_string(club_name_full)
    if club_code:
        cp_by_code = get_cp_from_club_code(club_code, club_df, column_mapping)
        if cp_by_code != "Non trouvé":
            return cp_by_code
    
    # Tentative 2 : Par nom (fallback)
    return get_cp_from_club_name(club_name_full, club_df, column_mapping)

def highlight_designated_cells(df_to_style, grille_dispo, column_mapping):
    """
    Met en évidence les cellules selon la disponibilité et les désignations
    - Fond vert pour les disponibilités "OUI"
    - Fond rouge pour les disponibilités "NON" 
    - Icône 🏈 pour les arbitres désignés (qui ont un match)
    """
    # Crée une matrice de style vide de la même taille que le df à styler.
    style_matrix = pd.DataFrame('', index=df_to_style.index, columns=df_to_style.columns)
    
    # Récupère la partie "DESIGNATION" de la grille complète.
    designation_data = grille_dispo[column_mapping['dispo_designation']]
    
    # Récupère la partie "DISPONIBILITE" de la grille complète.
    disponibilite_data = grille_dispo[column_mapping['dispo_disponibilite']]
    
    # Crée un masque booléen où la désignation est 1 (en remplissant les non-valeurs par 0).
    mask_designated = (designation_data.fillna(0) == 1)
    
    # Crée des masques pour les disponibilités "OUI" et "NON" - colonne par colonne
    mask_dispo_oui = pd.DataFrame(False, index=disponibilite_data.index, columns=disponibilite_data.columns)
    mask_dispo_non = pd.DataFrame(False, index=disponibilite_data.index, columns=disponibilite_data.columns)
    
    for col in disponibilite_data.columns:
        mask_dispo_oui[col] = disponibilite_data[col].fillna('').astype(str).str.upper() == 'OUI'
        mask_dispo_non[col] = disponibilite_data[col].fillna('').astype(str).str.upper() == 'NON'
    
    # Applique les styles aux colonnes communes (colonnes de date seulement)
    date_columns = [col for col in df_to_style.columns if col not in [
        column_mapping['arbitres_nom'],
        column_mapping['arbitres_prenom'], 
        column_mapping['arbitres_categorie'],
        'Club',
        'Nbr matchs\nà arbitrer'
    ]]
    
    common_cols = style_matrix.columns.intersection(date_columns)
    
    # Applique le fond vert pour les disponibilités "OUI"
    style_matrix.loc[:, common_cols] = style_matrix.loc[:, common_cols].mask(
        mask_dispo_oui[common_cols], 'background-color: #C8E6C9'  # Vert clair
    )
    
    # Applique le fond rouge pour les disponibilités "NON"
    style_matrix.loc[:, common_cols] = style_matrix.loc[:, common_cols].mask(
        mask_dispo_non[common_cols], 'background-color: #FFCDD2'  # Rouge clair
    )
    
    # Pour les arbitres désignés, on ajoute l'icône 🏈 au lieu du fond orange
    # On modifie directement le DataFrame affiché pour ajouter l'icône
    for col in common_cols:
        df_to_style.loc[mask_designated[col], col] = '🏈'
    
    return style_matrix
