import streamlit as st
import pandas as pd
import config
from utils import load_data, get_gspread_client, load_designations_from_sheets

def initialize_data():
    """Charge et pré-traite toutes les données une seule fois par session."""
    if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
        with st.spinner("Chargement et préparation des données..."):
            gc = get_gspread_client()
            st.session_state.categories_df = config.load_static_categories()
            st.session_state.competitions_df = config.load_static_competitions()
            st.session_state.rencontres_df = load_data(config.RENCONTRES_URL)
            st.session_state.dispo_df = load_data(config.DISPO_URL)
            st.session_state.arbitres_df = load_data(config.ARBITRES_URL)
            st.session_state.club_df = load_data(config.CLUB_URL)
            st.session_state.rencontres_ffr_df = load_data(config.RENCONTRES_FFR_URL)
            
            designations_df = load_designations_from_sheets(gc, config.DESIGNATIONS_URL) if gc else pd.DataFrame()
            if designations_df.empty:
                designations_df = load_data(config.DESIGNATIONS_URL)
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
                st.metric(
                    label="Rencontres-024",
                    value=f"{len(df)} matchs",
                    delta=f"{min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}" if pd.notna(min_date) and pd.notna(max_date) else "Dates non disponibles"
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
            if date_col in df.columns:
                dates = pd.to_datetime(df[date_col], errors='coerce')
                min_date = dates.min()
                max_date = dates.max()
                st.metric(
                    label="Disponibilités-022",
                    value=f"{len(df)} entrées",
                    delta=f"{min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}" if pd.notna(min_date) and pd.notna(max_date) else "Dates non disponibles"
                )
            else:
                st.metric("Disponibilités", f"{len(df)} entrées", "Colonne date manquante")
        else:
            st.metric("Disponibilités", "0 entrée", "Données non chargées")

# --- Configuration de la page et initialisation ---
st.set_page_config(
    page_title="Aide à la Désignation d'Arbitres",
    page_icon="🏉",
    layout="wide"
)

initialize_data()

# --- Interface Principale ---
st.title("Bienvenue dans l'outil d'aide à la désignation d'arbitres")
st.write("Utilisez le menu sur la gauche pour naviguer entre les différentes pages.")

# Afficher les tuiles d'information sur les données
display_data_tiles()

st.divider()

if st.sidebar.button("🔄 Rafraîchir les données", help="Recharge toutes les données depuis les fichiers sources"):
    st.session_state.data_loaded = False
    st.rerun()
