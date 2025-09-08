import streamlit as st
import pandas as pd

# Importations centralisées
from utils import load_data, get_designateur_actif_nom
import config

# --- Affichage du designateur ---
designateur_nom = get_designateur_actif_nom()
st.sidebar.markdown(f"### 👤 {designateur_nom}")
st.sidebar.markdown("---")

# --- Chargement des données ---

rencontres_ffr_df = load_data(config.RENCONTRES_FFR_URL)

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
