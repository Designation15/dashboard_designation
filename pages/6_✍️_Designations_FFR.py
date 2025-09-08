import streamlit as st
import pandas as pd
import numpy as np

# Importations centralisées
from utils import load_data, get_designateur_actif_nom
import config

# --- Affichage du designateur ---
designateur_nom = get_designateur_actif_nom()
st.sidebar.markdown(f"### 👤 {designateur_nom}")
st.sidebar.markdown("---")

@st.cache_data(ttl=300)
def load_all_data():
    """Charge et fusionne toutes les données nécessaires pour l'analyse FFR."""
    rencontres_df = load_data(config.RENCONTRES_FFR_URL)
    arbitres_df = load_data(config.ARBITRES_URL)
    club_df = load_data(config.CLUB_URL)
    categories_df = config.load_static_categories()
    competitions_df = config.load_static_competitions()
    competitions_df.rename(columns={'NOM': 'COMPETITION_NAME_FOR_MERGE'}, inplace=True)
    
    for df in [rencontres_df, arbitres_df, club_df]:
        df.columns = df.columns.str.strip()

    if 'CP' in club_df.columns:
        club_df['DPT_from_CP'] = club_df['CP'].astype(str).str.zfill(5).str[:2]
    else:
        club_df['DPT_from_CP'] = pd.NA

    if 'NOM' in rencontres_df.columns and 'Nom' not in rencontres_df.columns:
        rencontres_df.rename(columns={'NOM': 'Nom'}, inplace=True)

    # --- Robust Merge Logic ---
    arbitres_cols_to_merge = ['Numéro Affiliation', 'Catégorie', 'DPT DE RESIDENCE']
    existing_arbitres_cols = [col for col in arbitres_cols_to_merge if col in arbitres_df.columns]
    merged_df = pd.merge(rencontres_df, arbitres_df[existing_arbitres_cols], left_on='NUMERO LICENCE', right_on='Numéro Affiliation', how='left')
    # --- End Robust Merge ---

    merged_df = pd.merge(merged_df, categories_df, left_on='Catégorie', right_on='CATEGORIE', how='left')
    merged_df = pd.merge(merged_df, competitions_df, left_on='COMPETITION NOM', right_on='COMPETITION_NAME_FOR_MERGE', how='left')

    if 'LOCAUX' in merged_df.columns and 'Code' in club_df.columns:
        merged_df['LOCAUX_CODE'] = merged_df['LOCAUX'].str.extract(r'\((.*?)\)').fillna('0').astype(str)
        club_df['Code'] = club_df['Code'].astype(str)
        merged_df = pd.merge(merged_df, club_df[['Code', 'DPT_from_CP', 'CP']], left_on='LOCAUX_CODE', right_on='Code', how='left')
        merged_df.rename(columns={'DPT_from_CP': 'DPT_LOCAUX', 'CP': 'CP_LOCAUX'}, inplace=True)
    
    if 'DPT_LOCAUX' not in merged_df.columns: merged_df['DPT_LOCAUX'] = pd.NA
    if 'CP_LOCAUX' not in merged_df.columns: merged_df['CP_LOCAUX'] = pd.NA
    
    final_numeric_cols = ['Niveau', 'NIVEAU MIN', 'NIVEAU MAX', 'DPT DE RESIDENCE', 'DPT_LOCAUX', 'CP_LOCAUX']
    for col in final_numeric_cols:
        if col in merged_df.columns:
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce')

    return merged_df

# --- Fonctions de vérification ---
def apply_styling(row):
    if "Neutralité" in row["Statut"]:
        return ['background-color: #FFDDC1'] * len(row)
    if "Compétence" in row["Statut"]:
        return ['background-color: #FFC0CB'] * len(row)
    return [''] * len(row)

# --- Chargement des données ---
data_df = load_all_data()

# --- Application ---
st.title("✍️ Désignations FFR - Analyse Avancée")

if not data_df.empty:
    st.sidebar.header("Filtres")
    competitions = sorted([str(c) for c in data_df["COMPETITION NOM"].dropna().unique()])
    selected_competition = st.sidebar.multiselect("Filtrer par Compétition", options=competitions, default=[])
    search_term = st.sidebar.text_input("Rechercher un club ou un arbitre")

    filtered_df = data_df.copy()
    if selected_competition:
        filtered_df = filtered_df[filtered_df["COMPETITION NOM"].isin(selected_competition)]
    if search_term:
        search_mask = (
            filtered_df["LOCAUX"].str.contains(search_term, case=False, na=False) |
            filtered_df["VISITEURS"].str.contains(search_term, case=False, na=False) |
            filtered_df["Nom"].str.contains(search_term, case=False, na=False) | 
            filtered_df["PRENOM"].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[search_mask]

    # --- Calcul du Statut (version vectorisée) ---
    is_main_ref = filtered_df["FONCTION ARBITRE"] == "Arbitre de champ"
    
    # 1. Vérification de la Neutralité
    dpt_residence = pd.to_numeric(filtered_df["DPT DE RESIDENCE"], errors='coerce')
    dpt_locaux = pd.to_numeric(filtered_df["DPT_LOCAUX"], errors='coerce')
    is_same_dpt = dpt_residence == dpt_locaux
    neutrality_statut = np.where(is_main_ref & is_same_dpt, "⚠️ Neutralité", "")

    # 2. Vérification de la Compétence
    niveau = pd.to_numeric(filtered_df['Niveau'], errors='coerce')
    niveau_min = pd.to_numeric(filtered_df['NIVEAU MIN'], errors='coerce')
    niveau_max = pd.to_numeric(filtered_df['NIVEAU MAX'], errors='coerce')
    borne_inf = np.minimum(niveau_min, niveau_max)
    borne_sup = np.maximum(niveau_min, niveau_max)
    is_not_competent = ~niveau.between(borne_inf, borne_sup)
    competence_statut = np.where(is_main_ref & is_not_competent, "❌ Compétence", "")

    # 3. Combinaison des statuts
    statut_final = pd.Series(neutrality_statut) + " " + pd.Series(competence_statut)
    filtered_df["Statut"] = statut_final.str.strip().replace("", "✅ OK")


    st.header("Statistiques des Désignations")
    total_matchs = filtered_df["NUMERO RENCONTRE"].nunique()
    total_postes = len(filtered_df)
    postes_designes = len(filtered_df[filtered_df["Nom"].notna()])
    postes_a_designer = total_postes - postes_designes

    col1, col2, col3 = st.columns(3)
    col1.metric("Matchs Uniques", total_matchs)
    col2.metric("Postes d'Arbitres Pourvus", f"{postes_designes}/{total_postes}")
    col3.metric("Postes à Pourvoir", postes_a_designer)

    st.divider()

    st.header("Détails des Désignations")
    colonnes_a_afficher = [
        "Statut", "COMPETITION NOM", "LOCAUX", "VISITEURS", "DPT_LOCAUX", "CP_LOCAUX",
        "FONCTION ARBITRE", "Nom", "PRENOM", "DPT DE RESIDENCE", "Catégorie", "Niveau", "NIVEAU MIN", "NIVEAU MAX"
    ]
    
    colonnes_finales = [col for col in colonnes_a_afficher if col in filtered_df.columns]

    st.dataframe(
        filtered_df[colonnes_finales].style.apply(apply_styling, axis=1).format(
            {
                "DPT DE RESIDENCE": "{:.0f}",
                "Niveau": "{:.0f}",
                "NIVEAU MIN": "{:.0f}",
                "NIVEAU MAX": "{:.0f}",
                "DPT_LOCAUX": "{:.0f}",
                "CP_LOCAUX": "{:.0f}"
            },
            na_rep="-"
        ),
        hide_index=True, 
        use_container_width=True
    )

else:
    st.warning("Aucune donnée n'a pu être chargée.")
