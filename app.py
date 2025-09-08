import streamlit as st
import pandas as pd
import config
from utils import load_data, get_gspread_client, load_designations_from_sheets, get_designateur_actif_config, get_designateur_actif_nom

def load_designateurs_config():
    """Charge la configuration des designateurs depuis le fichier JSON."""
    try:
        import json
        with open('designateurs_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Fichier de configuration des designateurs introuvable.")
        return None
    except json.JSONDecodeError:
        st.error("Erreur de format dans le fichier de configuration des designateurs.")
        return None

def initialize_data():
    """Charge et pré-traite toutes les données une seule fois par session."""
    if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
        with st.spinner("Chargement et préparation des données..."):
            # Charger la configuration des designateurs
            config_data = load_designateurs_config()
            if not config_data:
                return
            
            # Récupérer le designateur actif configuré
            designateur_config = get_designateur_actif_config()
            if not designateur_config:
                st.error("Configuration du designateur introuvable.")
                return
            
            gc = get_gspread_client()
            st.session_state.categories_df = config.load_static_categories()
            st.session_state.competitions_df = config.load_static_competitions()
            
            # Charger les données spécifiques au designateur
            st.session_state.rencontres_df = load_data(designateur_config['rencontres_url'])
            st.session_state.dispo_df = load_data(designateur_config['dispo_url'])
            st.session_state.rencontres_ffr_df = load_data(designateur_config['rencontres_ovale_url'])
            
            # Charger les données partagées
            st.session_state.arbitres_df = load_data(config_data['fichiers_partages']['arbitres_url'])
            st.session_state.club_df = load_data(config_data['fichiers_partages']['club_url'])
            
            # Charger les désignations du designateur
            designations_df = load_designations_from_sheets(gc, designateur_config['designations_url']) if gc else pd.DataFrame()
            if designations_df.empty:
                designations_df = load_data(designateur_config['designations_url'])
            st.session_state.designations_df = designations_df

            # --- Pré-traitement centralisé ---
            for df_key in ['rencontres_df', 'rencontres_ffr_df', 'designations_df']:
                if df_key in st.session_state:
                    df = st.session_state[df_key]
                    if not df.empty:
                        if "NUMERO DE RENCONTRE" in df.columns:
                            df.rename(columns={"NUMERO DE RENCONTRE": "RENCONTRE NUMERO"}, inplace=True)
                        if "RENCONTRE NUMERO" in df.columns:
                            df["RENCONTRE NUMERO"] = df["RENCONTRE NUMERO"].astype(str)
            
            # Conversion des dates
            if not st.session_state.rencontres_df.empty:
                 # CORRECTION: retrait de dayfirst=True qui est incorrect pour ce format de date
                st.session_state.rencontres_df['rencontres_date_dt'] = pd.to_datetime(st.session_state.rencontres_df[config.COLUMN_MAPPING['rencontres_date']], errors='coerce')
            if not st.session_state.dispo_df.empty:
                 st.session_state.dispo_df['DATE_dt'] = pd.to_datetime(st.session_state.dispo_df[config.COLUMN_MAPPING['dispo_date']], errors='coerce')

            st.session_state.data_loaded = True

def display_data_tiles():
    """Affiche des tuiles d'information sur les données chargées."""
    st.subheader("📊 Informations sur les données")
    
    col1, col2, col3 = st.columns(3)
    
    # Tuile pour RENCONTRES_URL
    with col1:
        df = st.session_state.rencontres_df
        if not df.empty:
            date_col = config.COLUMN_MAPPING['rencontres_date']
            if date_col in df.columns:
                dates = pd.to_datetime(df[date_col], errors='coerce')
                min_date = dates.min()
                max_date = dates.max()
                
                # Calculer le nombre de matchs sans arbitres désignés (colonne C vide)
                matchs_sans_arbitres = 0
                # Vérifier la 3ème colonne (index 2) qui correspond à la colonne C
                if len(df.columns) > 2:
                    colonne_c = df.columns[2]  # Colonne C (3ème colonne)
                    matchs_sans_arbitres = sum(
                        1 for valeur in df[colonne_c] 
                        if pd.isna(valeur) or str(valeur).strip() == ''
                    )
                
                delta_text = f"{min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}" if pd.notna(min_date) and pd.notna(max_date) else "Dates non disponibles"
                
                st.metric(
                    label="Rencontres",
                    value=f"{matchs_sans_arbitres} désignations",
                    delta=delta_text
                )
            else:
                st.metric("Rencontres", f"{len(df)} matchs", "Colonne date manquante")
        else:
            st.metric("Rencontres", "0 match", "Données non chargées")
    
    # Tuile pour DESIGNATIONS_URL
    with col2:
        df = st.session_state.designations_df
        if not df.empty:
            matchs_uniques = df['RENCONTRE NUMERO'].nunique() if 'RENCONTRE NUMERO' in df.columns else 0
            
            # Extraction des dates si la colonne DATE existe
            date_info = ""
            if 'DATE' in df.columns:
                dates = pd.to_datetime(df['DATE'], errors='coerce', dayfirst=True)
                valid_dates = dates.dropna()
                if not valid_dates.empty:
                    min_date = valid_dates.min()
                    max_date = valid_dates.max()
                    date_info = f"{min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}"
            
            delta_text = f"{matchs_uniques} matchs"
            if date_info:
                delta_text = f"{date_info}"
            
            st.metric(
                label="Désignations manuelles",
                value=f"{len(df)} désignations",
                delta=delta_text
            )
        else:
            st.metric("Désignations manuelles", "0 désignation", "En attente de données")
    
    # Tuile pour DISPO_URL
    with col3:
        df = st.session_state.dispo_df
        if not df.empty:
            date_col = config.COLUMN_MAPPING['dispo_date']
            dispo_col = config.COLUMN_MAPPING['dispo_disponibilite']
            licence_col = config.COLUMN_MAPPING['dispo_licence']
            
            if date_col in df.columns and dispo_col in df.columns and licence_col in df.columns:
                dates = pd.to_datetime(df[date_col], errors='coerce')
                min_date = dates.min()
                max_date = dates.max()
                
                # Récupérer les dates des rencontres (jours avec matchs à désigner)
                rencontres_dates = []
                if not st.session_state.rencontres_df.empty:
                    renc_date_col = config.COLUMN_MAPPING['rencontres_date']
                    if renc_date_col in st.session_state.rencontres_df.columns:
                        rencontres_dates = pd.to_datetime(st.session_state.rencontres_df[renc_date_col], errors='coerce').dropna().dt.date.unique()
                
                # Filtrer les disponibilités uniquement sur les jours de match
                df_clean = df.copy()
                df_clean['date_clean'] = pd.to_datetime(df_clean[date_col], errors='coerce')
                df_clean = df_clean.dropna(subset=['date_clean'])
                df_clean['date_only'] = df_clean['date_clean'].dt.date
                
                # Garder seulement les entrées correspondant aux jours de match
                df_match_days = df_clean[df_clean['date_only'].isin(rencontres_dates)]
                
                # Compter le nombre d'arbitres uniques avec au moins 1 "OUI" sur les jours de match
                arbitres_disponibles = set()
                if not df_match_days.empty:
                    arbitres_avec_oui = df_match_days[df_match_days[dispo_col].str.upper() == 'OUI']
                    if not arbitres_avec_oui.empty:
                        arbitres_disponibles = set(arbitres_avec_oui[licence_col].unique())
                
                nb_arbitres_disponibles = len(arbitres_disponibles)
                
                # Afficher les 2 prochaines dates de match avec disponibilités
                today = pd.Timestamp.now().date()
                future_dates = [d for d in rencontres_dates if d >= today]
                future_dates.sort()
                
                disponibilites_info = []
                for date in future_dates[:2]:  # Limité à 2 dates
                    dispo_date = df_clean[df_clean['date_only'] == date]
                    oui_date = dispo_date[dispo_date[dispo_col].str.upper() == 'OUI']
                    nb_dispo = len(oui_date[licence_col].unique()) if not oui_date.empty else 0
                    disponibilites_info.append(f"{date.strftime('%d/%m')}: {nb_dispo}✅")
                
                delta_text = " - ".join(disponibilites_info) if disponibilites_info else f"{min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}" if pd.notna(min_date) and pd.notna(max_date) else "Dates non disponibles"
                
                st.metric(
                    label="Disponibilités",
                    value=f"{nb_arbitres_disponibles} arbitres",
                    delta=delta_text
                )
            else:
                st.metric("Disponibilités", f"{len(df)} entrées", "Colonne manquante")
        else:
            st.metric("Disponibilités", "0 entrée", "Données non chargées")

# --- Configuration de la page et initialisation ---
st.set_page_config(
    page_title="Aide à la Désignation d'Arbitres",
    page_icon="🏉",
    layout="wide"
)

# Récupérer le nom du designateur actif
designateur_nom = get_designateur_actif_nom()

# Afficher le nom du designateur en haut à gauche
st.sidebar.markdown(f"### 👤 {designateur_nom}")
st.sidebar.markdown("---")

initialize_data()

# --- Interface Principale ---
st.title("Bienvenue dans l'outil d'aide à la désignation d'arbitres")
st.write(f"Designateur : **{designateur_nom}**")
st.write("Utilisez le menu sur la gauche pour naviguer entre les différentes pages.")

# Afficher les tuiles d'information sur les données
display_data_tiles()

st.divider()

if st.sidebar.button("🔄 Rafraîchir les données", help="Recharge toutes les données depuis les fichiers sources"):
    st.session_state.data_loaded = False
    st.rerun()
