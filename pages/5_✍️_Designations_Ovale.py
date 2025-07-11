import streamlit as st
import pandas as pd

# --- Configuration et chargement des données ---
RENCONTRES_FFR_URL = "https://docs.google.com/spreadsheets/d/1ViKipszuqE5LPbTcFk2QvmYq4ZNQZVs9LbzrUVC4p4Y/export?format=xlsx"

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
rencontres_ffr_df = load_data(RENCONTRES_FFR_URL)

# --- Application ---
st.title("✍️ Designations Ovale")

if not rencontres_ffr_df.empty:
    # Calcul du nombre de matchs uniques
    nombre_matchs = rencontres_ffr_df["NUMERO RENCONTRE"].nunique()
    st.metric(label="Nombre de matchs désignés", value=nombre_matchs)

    st.divider()

    # Affichage du tableau
    st.header("Détails des rencontres")
    
    colonnes_a_afficher = [
        "Nom",
        "PRENOM",
        "FONCTION ARBITRE",
        "DPT DE RESIDENCE",
        "COMPETITION NOM",
        "LOCAUX",
        "VISITEURS",
        "TERRAIN CODE POSTAL"
    ]
    
    # Vérifier si les colonnes existent dans le dataframe
    colonnes_existantes = [col for col in colonnes_a_afficher if col in rencontres_ffr_df.columns]
    
    if len(colonnes_existantes) != len(colonnes_a_afficher):
        st.warning("Certaines colonnes demandées n'existent pas dans le fichier.")
        st.write("Colonnes disponibles :", rencontres_ffr_df.columns.tolist())
        st.write("Colonnes manquantes :", list(set(colonnes_a_afficher) - set(colonnes_existantes)))
    
    st.dataframe(rencontres_ffr_df[colonnes_existantes], hide_index=True, use_container_width=True)

else:
    st.warning("Aucune donnée de rencontre FFR n'a pu être chargée.")
