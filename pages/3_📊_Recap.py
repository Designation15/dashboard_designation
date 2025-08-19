import streamlit as st
import pandas as pd

# Importations centralisées
from utils import load_data
import config

# --- Initialisation ---
st.title("📊 Récapitulatif des Désignations")
st.markdown("RS_OVALE2-024 - Vue consolidée de toutes les rencontres et des désignations manuelles associées.")

if st.button("Rafraîchir les Données", type="primary"):
    st.cache_data.clear()
    st.rerun()

# --- Chargement des données ---
rencontres_df = load_data(config.RENCONTRES_URL)
designations_df = load_data(config.DESIGNATIONS_URL)

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

    # Formater la colonne du département de l'arbitre
    if 'Arbitre Dpt Résidence' in recap_df.columns:
        recap_df['Arbitre Dpt Résidence'] = recap_df['Arbitre Dpt Résidence'].apply(lambda x: str(int(x)).zfill(2) if pd.notna(x) and str(x) != '-' else '-')

    # Formater la date au format FR
    if 'DATE EFFECTIVE' in recap_df.columns:
        recap_df['DATE EFFECTIVE'] = pd.to_datetime(recap_df['DATE EFFECTIVE'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')

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