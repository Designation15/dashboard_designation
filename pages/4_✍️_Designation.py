import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import (
    get_department_from_club_name_or_code,
    get_cp_from_club_name_or_code,
    highlight_designated_cells,
    extract_club_code_from_team_string,
    extract_club_name_from_team_string
)

# --- Configuration et chargement des données ---
RENCONTRES_URL = "https://docs.google.com/spreadsheets/d/1I8RGfNNdaO1wlrtFgIOFbOnzpKszwJTxdyhQ7rRD1bg/export?format=xlsx"
DISPO_URL = "https://docs.google.com/spreadsheets/d/16-eSHsURF-H1zWx_a_Tu01E9AtmxjIXocpiR2t2ZNU4/export?format=xlsx"
ARBITRES_URL = "https://docs.google.com/spreadsheets/d/1bIUxD-GDc4V94nYoI_x2mEk0i_r9Xxnf02_Rn9YtoIc/export?format=xlsx"
CLUB_URL = "https://docs.google.com/spreadsheets/d/1GLWS4jOmwv-AOtkFZ5-b5JcjaSpBVlwqcuOCRRmEVPQ/export?format=xlsx"

COLUMN_MAPPING = {
    "rencontres_date": "DATE EFFECTIVE",
    "rencontres_competition": "COMPETITION NOM",
    "rencontres_locaux": "LOCAUX",
    "rencontres_visiteurs": "VISITEURS",
    "dispo_date": "DATE",
    "dispo_disponibilite": "DISPONIBILITE",
    "dispo_licence": "NO LICENCE",
    "dispo_designation": "DESIGNATION",
    "arbitres_affiliation": "Numéro Affiliation",
    "arbitres_nom": "Nom",
    "arbitres_prenom": "Prénom",
    "arbitres_categorie": "Catégorie",
    "arbitres_club_code": "Code Club",
    "arbitres_dpt_residence": "Département de Résidence",
    "club_nom": "Nom",
    "club_cp": "CP",
    "club_code": "CODE",
    "categories_nom": "CATEGORIE",
    "categories_niveau": "Niveau",
    "competitions_nom": "NOM",
    "competitions_niveau_min": "NIVEAU MIN",
    "competitions_niveau_max": "NIVEAU MAX",
}

@st.cache_data
def load_static_data():
    categories_data = {
        'Niveau': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        'CATEGORIE': [
            'Internationaux', '2ème Division PRO', 'Nationale 1 et 2', 
            'Arbitres assistants PRO', 'Arbitres assistants NAT', 'Divisionnaires 1', 
            'Divisionnaires 2', 'Divisionnaires 3', 'Ligue 1', 'Ligue 2', 'Ligue 3', 
            'Ligue 4', 'Ligue 5', 'Mineurs 17 ans', 'Mineurs 16 ans', 'Mineurs 15 ans'
        ]
    }
    categories_df = pd.DataFrame(categories_data)
    competitions_data = {
        'NOM': [
            'Elite 1 Féminine', 'Elite 2 Féminine', 'Elite Alamercery', 'Elite Crabos', 
            'Espoirs Fédéraux', 'European Rugby Champions Cup', 'Excellence B - Championnat de France', 
            'Fédérale 1', 'Fédérale 2', 'Fédérale 3', 'Fédérale B - Championnat de France', 
            'Féminines Moins de 18 ans à XV - ELITE', 'Féminines Régionales à X', 
            'Féminines Régionales à X « moins de 18 ans »', 'Régional 1 U16', 'Régional 1 U19', 
            'Régional 2 U16', 'Régional 2 U19', 'Régional 3 U16', 'Régional 3 U19', 
            'Régionale 1 - Championnat Territorial', 'Régionale 2 - Championnat Territorial', 
            'Régionale 3 - Championnat Territorial', 'Réserves Elite', 
            'Réserves Régionales 1 - Championnat Territorial', 'Réserves Régionales 2 - Championnat Territorial'
        ],
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
    except Exception as e:
        st.error(f"Impossible de charger les données depuis {url}. Erreur: {e}")
        return pd.DataFrame()

# --- Chargement des données ---
categories_df, competitions_df = load_static_data()
rencontres_df = load_data(RENCONTRES_URL)
dispo_df = load_data(DISPO_URL)
arbitres_df = load_data(ARBITRES_URL)
club_df = load_data(CLUB_URL)

# Convertir la colonne de date des rencontres en datetime dès le chargement
if not rencontres_df.empty:
    rencontres_df['rencontres_date_dt'] = pd.to_datetime(rencontres_df[COLUMN_MAPPING['rencontres_date']], errors='coerce', dayfirst=True)

# --- Application ---
st.title("✍️ Outil d'aide à la désignation")

st.header("1. Sélection de la rencontre")
competition_nom = st.selectbox(
    "Choisissez une compétition",
    options=competitions_df[COLUMN_MAPPING['competitions_nom']].unique(),
    help="Filtrez les rencontres en fonction de la compétition."
)

rencontres_filtrees_df = rencontres_df[rencontres_df[COLUMN_MAPPING['rencontres_competition']] == competition_nom].copy()
if not rencontres_filtrees_df.empty:
    rencontres_filtrees_df = rencontres_filtrees_df.sort_values(by='rencontres_date_dt')
    rencontres_filtrees_df['display'] = rencontres_filtrees_df.apply(
        lambda x: f"{x['rencontres_date_dt'].strftime('%d/%m/%Y')} - {x[COLUMN_MAPPING['rencontres_locaux']]} vs {x[COLUMN_MAPPING['rencontres_visiteurs']]}",
        axis=1
    )
    option_selectionnee = st.selectbox(
        "Choisissez une rencontre",
        options=rencontres_filtrees_df['display']
    )
    st.divider()

    if option_selectionnee:
        st.header("2. Détails de la rencontre")
        rencontre_details = rencontres_filtrees_df[rencontres_filtrees_df['display'] == option_selectionnee].iloc[0]
        locaux = rencontre_details[COLUMN_MAPPING['rencontres_locaux']]
        visiteurs = rencontre_details[COLUMN_MAPPING['rencontres_visiteurs']]
        date_rencontre = rencontre_details['rencontres_date_dt']

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**📅 Date :** {date_rencontre.strftime('%d/%m/%Y')}")
            st.write(f"**🏆 Compétition :** {rencontre_details[COLUMN_MAPPING['rencontres_competition']]}")
        with col2:
            st.write(f"**🏟️ Domicile :** {locaux}")
            st.write(f"**✈️ Visiteur :** {visiteurs}")
        st.divider()

        st.header("3. Arbitres disponibles et qualifiés")
        
        # --- Processus de filtrage ---
        with st.expander("🔍 Suivi du filtrage des arbitres", expanded=True):
            # 1. Filtrage par niveau
            competition_info = competitions_df[competitions_df[COLUMN_MAPPING['competitions_nom']] == competition_nom].iloc[0]
            niveau_min, niveau_max = (competition_info[COLUMN_MAPPING['competitions_niveau_min']], competition_info[COLUMN_MAPPING['competitions_niveau_max']])
            if niveau_min > niveau_max: niveau_min, niveau_max = niveau_max, niveau_min

            arbitres_df_avec_niveau = pd.merge(arbitres_df, categories_df, left_on=COLUMN_MAPPING['arbitres_categorie'], right_on=COLUMN_MAPPING['categories_nom'], how='left')
            arbitres_qualifies_niveau = arbitres_df_avec_niveau[arbitres_df_avec_niveau[COLUMN_MAPPING['categories_niveau']].between(niveau_min, niveau_max)]
            st.info(f"**Étape 1 : Filtrage par niveau**\n- Niveau requis : Entre {niveau_min} et {niveau_max}\n- Arbitres trouvés : **{len(arbitres_qualifies_niveau)}**")

            # 2. Filtrage par neutralité
            dpt_locaux = get_department_from_club_name_or_code(locaux, club_df, COLUMN_MAPPING)
            dpt_visiteurs = get_department_from_club_name_or_code(visiteurs, club_df, COLUMN_MAPPING)
            dpts_to_exclude = [d for d in [dpt_locaux, dpt_visiteurs] if d and d != "Non trouvé"]
            
            arbitres_apres_neutralite = arbitres_qualifies_niveau
            if dpts_to_exclude:
                arbitres_apres_neutralite = arbitres_qualifies_niveau[~arbitres_qualifies_niveau[COLUMN_MAPPING['arbitres_dpt_residence']].astype(str).isin(dpts_to_exclude)]
            st.info(f"**Étape 2 : Filtrage par neutralité**\n- Départements à exclure : {dpts_to_exclude}\n- Arbitres restants : **{len(arbitres_apres_neutralite)}**")

            # 3. Recherche de disponibilités sur la plage de dates des rencontres
            # Assurez-vous que rencontres_df n'est pas vide avant d'accéder à 'rencontres_date_dt'
            if not rencontres_df.empty:
                min_rencontre_date = rencontres_df['rencontres_date_dt'].min()
                max_rencontre_date = rencontres_df['rencontres_date_dt'].max()
            else:
                min_rencontre_date = datetime.now().date() # Fallback
                max_rencontre_date = datetime.now().date() + timedelta(days=7) # Fallback

            st.info(f"**Étape 3 : Filtrage des disponibilités sur la plage des rencontres**\n- Plage de dates des rencontres : du {min_rencontre_date.strftime('%d/%m/%Y')} au {max_rencontre_date.strftime('%d/%m/%Y')}")

            dispo_df['DATE EFFECTIVE'] = pd.to_datetime(dispo_df[COLUMN_MAPPING['dispo_date']], errors='coerce')
            
            # Debug: Afficher les dates uniques dans dispo_df après conversion
            st.write("Dates uniques dans dispo_df (après conversion) :", dispo_df['DATE EFFECTIVE'].dt.strftime('%d/%m/%Y').unique())

            dispo_cols_needed = [COLUMN_MAPPING['dispo_licence'], COLUMN_MAPPING['dispo_disponibilite'], COLUMN_MAPPING['dispo_designation'], 'DATE EFFECTIVE']
            
            # Filtrer les disponibilités sur la plage de dates des rencontres
            dispo_filtered_by_rencontres_range = dispo_df[
                (dispo_df['DATE EFFECTIVE'].dt.date >= min_rencontre_date.date()) & 
                (dispo_df['DATE EFFECTIVE'].dt.date <= max_rencontre_date.date())
            ][dispo_cols_needed]
            
            # Debug: Afficher les dates uniques dans dispo_filtered_by_rencontres_range
            st.write("Dates uniques dans dispo_filtered_by_rencontres_range :", dispo_filtered_by_rencontres_range['DATE EFFECTIVE'].dt.strftime('%d/%m/%Y').unique())

            st.write("**Contenu de dispo_filtered_by_rencontres_range (premières lignes) :**")
            st.dataframe(dispo_filtered_by_rencontres_range.head())
            st.write(f"Nombre de lignes dans dispo_filtered_by_rencontres_range : {len(dispo_filtered_by_rencontres_range)}")

            # Debug: Vérifier les valeurs uniques des clés de fusion
            st.write(f"Unique '{COLUMN_MAPPING['arbitres_affiliation']}' in arbitres_apres_neutralite: {arbitres_apres_neutralite[COLUMN_MAPPING['arbitres_affiliation']].nunique()}")
            st.write(f"Unique '{COLUMN_MAPPING['dispo_licence']}' in dispo_filtered_by_rencontres_range: {dispo_filtered_by_rencontres_range[COLUMN_MAPPING['dispo_licence']].nunique()}")

            arbitres_avec_dispo = pd.merge(
                arbitres_apres_neutralite, 
                dispo_filtered_by_rencontres_range, 
                left_on=COLUMN_MAPPING['arbitres_affiliation'], 
                right_on=COLUMN_MAPPING['dispo_licence'], 
                how='left'
            )
            st.info(f"**Étape 4 : Fusion avec les disponibilités filtrées**\n- Arbitres avec données de dispo (ou non) : **{len(arbitres_avec_dispo)}**")
            st.write("Colonnes de arbitres_avec_dispo après fusion:", arbitres_avec_dispo.columns.tolist())
            st.write("**Contenu de arbitres_avec_dispo (premières lignes) :**")
            st.dataframe(arbitres_avec_dispo.head())
            if COLUMN_MAPPING['dispo_disponibilite'] in arbitres_avec_dispo.columns:
                st.write("Valeurs uniques dans la colonne 'DISPONIBILITE' après fusion :", arbitres_avec_dispo[COLUMN_MAPPING['dispo_disponibilite']].unique())
            else:
                st.write(f"La colonne '{COLUMN_MAPPING['dispo_disponibilite']}' n'est pas présente dans arbitres_avec_dispo après fusion.")

        # --- Affichage de la grille ---
        if arbitres_avec_dispo.empty:
            st.warning("Aucun arbitre qualifié trouvé pour cette rencontre.", icon="⚠️")
        elif COLUMN_MAPPING['dispo_disponibilite'] not in arbitres_avec_dispo.columns or arbitres_avec_dispo[COLUMN_MAPPING['dispo_disponibilite']].isnull().all():
            st.warning("Aucune information de disponibilité pour les arbitres qualifiés sur la plage de dates des rencontres.", icon="📅")
            st.write("Liste des arbitres qualifiés (sans information de disponibilité) :")
            st.dataframe(arbitres_apres_neutralite[[COLUMN_MAPPING['arbitres_nom'], COLUMN_MAPPING['arbitres_prenom'], COLUMN_MAPPING['arbitres_categorie']]], hide_index=True, use_container_width=True)
        else:
            # Générer toutes les dates dans la plage des rencontres pour les colonnes de la grille
            all_dates_in_range = [min_rencontre_date + timedelta(days=x) for x in range((max_rencontre_date - min_rencontre_date).days + 1)]
            ordered_columns_for_grid = [d.strftime('%d/%m/%Y') for d in all_dates_in_range]

            arbitres_avec_dispo['DATE_AFFICHAGE'] = arbitres_avec_dispo['DATE EFFECTIVE'].dt.strftime('%d/%m/%Y')
            
            grille_dispo = arbitres_avec_dispo.pivot_table(
                index=[COLUMN_MAPPING['arbitres_nom'], COLUMN_MAPPING['arbitres_prenom'], COLUMN_MAPPING['arbitres_categorie']],
                columns='DATE_AFFICHAGE',
                values=[COLUMN_MAPPING['dispo_disponibilite'], COLUMN_MAPPING['dispo_designation']],
                aggfunc='first'
            )
            
            display_grille = grille_dispo[COLUMN_MAPPING['dispo_disponibilite']].fillna('Non renseigné')
            
            # S'assurer que toutes les colonnes attendues sont présentes, même si vides
            for col in ordered_columns_for_grid:
                if col not in display_grille.columns:
                    display_grille[col] = '-' # Ou une autre valeur par défaut
            
            st.dataframe(display_grille[ordered_columns_for_grid].style.apply(highlight_designated_cells, grille_dispo=grille_dispo, column_mapping=COLUMN_MAPPING, axis=None), use_container_width=True)

else:
    st.warning("Aucune rencontre trouvée pour cette compétition.")