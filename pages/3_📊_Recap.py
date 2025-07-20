import streamlit as st
import pandas as pd

# --- Configuration ---
RENCONTRES_URL = "https://docs.google.com/spreadsheets/d/1I8RGfNNdaO1wlrtFgIOFbOnzpKszwJTxdyhQ7rRD1bg/export?format=xlsx"
DESIGNATIONS_URL = "https://docs.google.com/spreadsheets/d/1gaPIT5477GOLNfTU0ITwbjNK1TjuO8q-yYN2YasDezg/export?format=xlsx"

# --- Fonctions de chargement ---
@st.cache_data(ttl=600)
def load_data(url):
    try:
        df = pd.read_excel(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Impossible de charger les données depuis {url}. Erreur: {e}")
        return pd.DataFrame()

# --- Initialisation ---
st.set_page_config(layout="wide")
st.title("📊 Récapitulatif des Désignations")
st.markdown("Vue consolidée de toutes les rencontres et des désignations manuelles associées.")

# --- Chargement des données ---
rencontres_df = load_data(RENCONTRES_URL)
designations_df = load_data(DESIGNATIONS_URL)

# --- Pré-traitement et Fusion ---
if not rencontres_df.empty:
    # Standardisation des noms de colonnes pour la fusion
    for df in [rencontres_df, designations_df]:
        if "NUMERO DE RENCONTRE" in df.columns:
            df.rename(columns={"NUMERO DE RENCONTRE": "RENCONTRE NUMERO"}, inplace=True)
        if "RENCONTRE NUMERO" in df.columns:
            df["RENCONTRE NUMERO"] = df["RENCONTRE NUMERO"].astype(str)

    # Sélectionner les colonnes pertinentes du fichier de désignations
    if not designations_df.empty:
        cols_to_merge = ['RENCONTRE NUMERO', 'NOM', 'PRENOM', 'DPT DE RESIDENCE', 'FONCTION ARBITRE']
        existing_cols = [col for col in cols_to_merge if col in designations_df.columns]
        designations_subset_df = designations_df[existing_cols]
        # Renommer pour clarté après la fusion
        designations_subset_df = designations_subset_df.rename(columns={
            'NOM': 'Arbitre Nom',
            'PRENOM': 'Arbitre Prénom',
            'DPT DE RESIDENCE': 'Arbitre Dpt Résidence',
            'FONCTION ARBITRE': 'Arbitre Fonction'
        })
    else:
        designations_subset_df = pd.DataFrame(columns=['RENCONTRE NUMERO'])

    # Jointure à gauche pour garder toutes les rencontres
    recap_df = pd.merge(rencontres_df, designations_subset_df, on="RENCONTRE NUMERO", how="left")

    # Remplacer les NaN (non-matchs) par des textes clairs
    for col in ['Arbitre Nom', 'Arbitre Prénom', 'Arbitre Dpt Résidence', 'Arbitre Fonction']:
        if col in recap_df.columns:
            recap_df[col].fillna("-", inplace=True)

    # --- Filtres ---
    st.header("Filtres")
    col1, col2 = st.columns(2)
    with col1:
        competitions = ["Toutes"] + sorted(recap_df['COMPETITION NOM'].unique().tolist())
        selected_competition = st.selectbox("Filtrer par compétition", options=competitions)
    with col2:
        search_term = st.text_input("Rechercher un club ou un arbitre", "")

    # Application des filtres
    filtered_df = recap_df
    if selected_competition != "Toutes":
        filtered_df = filtered_df[filtered_df['COMPETITION NOM'] == selected_competition]
    if search_term:
        # Recherche sur plusieurs colonnes
        search_cols = ['LOCAUX', 'VISITEURS', 'Arbitre Nom', 'Arbitre Prénom']
        mask = pd.concat([filtered_df[col].str.contains(search_term, case=False, na=False) for col in search_cols], axis=1).any(axis=1)
        filtered_df = filtered_df[mask]

    st.divider()

    # --- Affichage du Tableau ---
    st.header(f"{len(filtered_df)} Rencontres Trouvées")
    cols_to_show = ['DATE EFFECTIVE', 'COMPETITION NOM', 'LOCAUX', 'VISITEURS', 'Arbitre Nom', 'Arbitre Prénom', 'Arbitre Dpt Résidence', 'Arbitre Fonction']
    final_cols = [col for col in cols_to_show if col in filtered_df.columns]
    st.dataframe(filtered_df[final_cols], hide_index=True, use_container_width=True)

else:
    st.warning("Impossible de charger les données des rencontres.")
