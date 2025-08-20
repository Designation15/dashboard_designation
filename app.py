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

if st.sidebar.button("🔄 Rafraîchir les données", help="Recharge toutes les données depuis les fichiers sources"):
    st.session_state.data_loaded = False
    st.rerun()
