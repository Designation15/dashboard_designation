import streamlit as st
import pandas as pd

import config

# --- Récupération des données ---
rencontres_df = st.session_state.get('rencontres_df', pd.DataFrame()).copy()
designations_df = st.session_state.get('designations_df', pd.DataFrame()).copy()

st.title("📊 Récapitulatif des Désignations")
st.markdown("RS_OVALE2-024 - Vue filtrée  de toutes les rencontres a designées.")

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

    # --- Filtre par défaut ---
    st.header("Filtre")
    
    # Liste des compétitions à filtrer par défaut
    competitions_filtre_defaut = [
        "Fédérale 3",
        "Espoirs Fédéraux",
        "National U16",
        "National U18",
        "Gauderman",
        "Excellence B - Championnat de France",
        "Fédérale B - Championnat de France",
        "Fédérale 1 Féminine",
        "Fédérale 2 féminine",
        "Fédérale 2 Féminine – IDF/HDF",
        "Féminines Régionales à X",
        "Régionale 1 - Championnat Territorial",
        "Réserves Régionales 1 - Championnat Territorial",
        "Régionale 2 - Championnat Territorial",
        "Réserves Régionales 2 - Championnat Territorial",
        "Régionale 3 - Championnat Territorial",
        "Réserves Régionales 3 - Championnat Territorial",
        "Régional 1 U19",
        "Régional 2 U19",
        "Régional 3 U19",
        "Féminines Régionales à X « moins de 18 ans »",
        "Féminines Moins de 18 ans à XV - ELITE",
        "Régional 1 U16",
        "Régional 2 U16",
        "Régional 3 U16",
        "Championnat Territorial des Clubs + 18 ans Féminin à 7",
        "Championnat Territorial des Clubs - 18 ans Féminin à 7",
        "Matchs d'échanges",
        "Loisirs"
    ]
    
    # Bouton toggle pour activer/désactiver le filtre par défaut
    filtre_actif = st.checkbox("Activer le filtre par compétitions", value=True)
    
    filtered_df = recap_df
    if filtre_actif:
        filtered_df = filtered_df[filtered_df[config.COLUMN_MAPPING['rencontres_competition']].isin(competitions_filtre_defaut)]

    st.divider()

    # --- Affichage du Tableau ---
    st.header(f"{len(filtered_df)} Rencontres Trouvées")
    cols_to_show = [config.COLUMN_MAPPING['rencontres_date'], config.COLUMN_MAPPING['rencontres_competition'], config.COLUMN_MAPPING['rencontres_locaux'], config.COLUMN_MAPPING['rencontres_visiteurs'], 'Arbitre Nom', 'Arbitre Prénom', 'Arbitre Dpt Résidence', 'Arbitre Fonction']
    final_cols = [col for col in cols_to_show if col in filtered_df.columns]
    st.dataframe(filtered_df[final_cols], hide_index=True, use_container_width=True)

else:
    st.warning("Impossible de charger les données des rencontres.")
