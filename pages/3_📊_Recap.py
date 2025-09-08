import streamlit as st
from utils import get_designateur_actif_nom
import pandas as pd

import config

# --- Récupération des données ---
# --- Affichage du designateur ---
designateur_nom = get_designateur_actif_nom()
st.sidebar.markdown(f"### 👤 {designateur_nom}")
st.sidebar.markdown("---")

rencontres_df = st.session_state.get('rencontres_df', pd.DataFrame()).copy()
designations_df = st.session_state.get('designations_df', pd.DataFrame()).copy()

st.title("📊 Récapitulatif des Désignations")
st.markdown("RS_OVALE2-024 - Vue consolidée de toutes les rencontres et des désignations manuelles associées.")

if not rencontres_df.empty:
    # --- Pré-traitement et Fusion ---
    # Standardisation des noms de colonnes (déjà fait dans app.py, mais sans danger ici)
    for df in [rencontres_df, designations_df]:
        if "RENCONTRE NUMERO" in df.columns:
            df["RENCONTRE NUMERO"] = df["RENCONTRE NUMERO"].astype(str)

    if not designations_df.empty:
        cols_to_merge = ['RENCONTRE NUMERO', 'NOM', 'PRENOM', 'DPT DE RESIDENCE', 'FONCTION ARBITRE']
        existing_cols = [col for col in cols_to_merge if col in designations_df.columns]
        designations_subset_df = designations_df[existing_cols].rename(columns={
            'NOM': 'Arbitre Nom',
            'PRENOM': 'Arbitre Prénom',
            'DPT DE RESIDENCE': 'Arbitre Dpt Résidence',
            'FONCTION ARBITRE': 'Arbitre Fonction'
        })
    else:
        designations_subset_df = pd.DataFrame(columns=['RENCONTRE NUMERO', 'Arbitre Nom', 'Arbitre Prénom', 'Arbitre Dpt Résidence', 'Arbitre Fonction'])

    recap_df = pd.merge(rencontres_df, designations_subset_df, on="RENCONTRE NUMERO", how="left")

    # Remplacer les NaN (non-matchs) par des textes clairs
    cols_to_fill = ['Arbitre Nom', 'Arbitre Prénom', 'Arbitre Dpt Résidence', 'Arbitre Fonction']
    for col in cols_to_fill:
        if col in recap_df.columns:
            # CORRECTION: Convertir en type 'object' avant de remplir avec un string
            recap_df[col] = recap_df[col].astype(object).fillna("-")

    if 'Arbitre Dpt Résidence' in recap_df.columns:
        recap_df['Arbitre Dpt Résidence'] = recap_df['Arbitre Dpt Résidence'].apply(lambda x: str(int(x)).zfill(2) if pd.notna(x) and str(x) != '-' else '-')

    if config.COLUMN_MAPPING['rencontres_date'] in recap_df.columns:
        recap_df[config.COLUMN_MAPPING['rencontres_date']] = pd.to_datetime(recap_df[config.COLUMN_MAPPING['rencontres_date']], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')

    # --- Filtres ---
    st.header("Filtres")
    col1, col2 = st.columns(2)
    with col1:
        competitions = sorted(recap_df[config.COLUMN_MAPPING['rencontres_competition']].unique().tolist())
        selected_competitions = st.multiselect("Filtrer par compétition", options=competitions, placeholder="Choisissez une ou plusieurs compétitions")
    with col2:
        search_term = st.text_input("Rechercher un club ou un arbitre", "")

    filtered_df = recap_df
    if selected_competitions:
        filtered_df = filtered_df[filtered_df[config.COLUMN_MAPPING['rencontres_competition']].isin(selected_competitions)]
    if search_term:
        search_cols = [config.COLUMN_MAPPING['rencontres_locaux'], config.COLUMN_MAPPING['rencontres_visiteurs'], 'Arbitre Nom', 'Arbitre Prénom']
        mask = pd.concat([filtered_df[col].str.contains(search_term, case=False, na=False) for col in search_cols if col in filtered_df], axis=1).any(axis=1)
        filtered_df = filtered_df[mask]

    st.divider()

    # --- Affichage du Tableau ---
    st.header(f"{len(filtered_df)} Rencontres Trouvées")
    cols_to_show = [config.COLUMN_MAPPING['rencontres_date'], config.COLUMN_MAPPING['rencontres_competition'], config.COLUMN_MAPPING['rencontres_locaux'], config.COLUMN_MAPPING['rencontres_visiteurs'], 'Arbitre Nom', 'Arbitre Prénom', 'Arbitre Dpt Résidence', 'Arbitre Fonction']
    final_cols = [col for col in cols_to_show if col in filtered_df.columns]
    st.dataframe(filtered_df[final_cols], hide_index=True, use_container_width=True)

else:
    st.warning("Impossible de charger les données des rencontres.")
