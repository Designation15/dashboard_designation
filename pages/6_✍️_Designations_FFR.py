import streamlit as st
import pandas as pd

# --- Configuration et chargement des données ---
RENCONTRES_FFR_URL = "https://docs.google.com/spreadsheets/d/1ViKipszuqE5LPbTcFk2QvmYq4ZNQZVs9LbzrUVC4p4Y/export?format=xlsx"

@st.cache_data(ttl=300) # Cache les données pour 5 minutes
def load_data(url):
    try:
        df = pd.read_excel(url)
        df.columns = df.columns.str.strip()
        # Remplacer les valeurs NaN ou "A DESIGNER" dans les colonnes d'arbitres pour un comptage fiable
        for col in ["NOM", "PRENOM", "FONCTION ARBITRE"]:
            if col in df.columns:
                df[col] = df[col].fillna("A DESIGNER")
                df[col] = df[col].replace("", "A DESIGNER")
        return df
    except Exception as e:
        st.error(f"Impossible de charger les données depuis {url}. Erreur: {e}")
        return pd.DataFrame()

# --- Chargement des données ---
rencontres_ffr_df = load_data(RENCONTRES_FFR_URL)

# --- Application ---
st.set_page_config(layout="wide")
st.title("✍️ Désignations FFR")

if not rencontres_ffr_df.empty:
    # --- Barre latérale de filtres ---
    st.sidebar.header("Filtres")

    # Filtre par compétition
    competitions = sorted([str(c) for c in rencontres_ffr_df["COMPETITION NOM"].dropna().unique()])
    selected_competition = st.sidebar.multiselect(
        "Filtrer par Compétition",
        options=competitions,
        default=[]
    )

    # Barre de recherche
    search_term = st.sidebar.text_input(
        "Rechercher un club ou un arbitre"
    )

    # Application des filtres
    filtered_df = rencontres_ffr_df.copy()
    if selected_competition:
        filtered_df = filtered_df[filtered_df["COMPETITION NOM"].isin(selected_competition)]

    if search_term:
        # Recherche insensible à la casse dans plusieurs colonnes
        search_mask = (
            filtered_df["LOCAUX"].str.contains(search_term, case=False, na=False) |
            filtered_df["VISITEURS"].str.contains(search_term, case=False, na=False) |
            filtered_df["Nom"].str.contains(search_term, case=False, na=False) |
            filtered_df["PRENOM"].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[search_mask]

    # --- Indicateurs Clés ---
    st.header("Statistiques des Désignations")
    
    total_matchs = filtered_df["NUMERO RENCONTRE"].nunique()
    total_postes = len(filtered_df)
    postes_designes = len(filtered_df[filtered_df["Nom"] != "A DESIGNER"])
    postes_a_designer = total_postes - postes_designes

    col1, col2, col3 = st.columns(3)
    col1.metric("Matchs Uniques", total_matchs)
    col2.metric("Postes d'Arbitres Pourvus", f"{postes_designes}/{total_postes}")
    col3.metric("Postes à Pourvoir", postes_a_designer)

    st.divider()

    # --- Affichage du tableau filtré ---
    st.header("Détails des Désignations")
    
    colonnes_a_afficher = [
        "COMPETITION NOM",
        "DATE",
        "LOCAUX",
        "VISITEURS",
        "FONCTION ARBITRE",
        "NOM",
        "PRENOM",
        "DPT DE RESIDENCE",
        "TERRAIN CODE POSTAL"
    ]
    
    colonnes_existantes = [col for col in colonnes_a_afficher if col in filtered_df.columns]
    
    st.dataframe(filtered_df[colonnes_existantes], hide_index=True, use_container_width=True)

else:
    st.warning("Aucune donnée de rencontre FFR n'a pu être chargée.")
