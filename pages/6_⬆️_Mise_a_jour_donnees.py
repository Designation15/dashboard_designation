import streamlit as st
import pandas as pd
import re

# Importations centralisées
import config
from utils import (
    get_gspread_client,
    update_google_sheet,
    clear_sheet_except_header,
)

def get_edit_url_from_export_url(export_url):
    """Convertit une URL d'export Google Sheet en URL d'édition."""
    match = re.search(r'/d/([^/]+)', export_url)
    if match:
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    return export_url # Fallback si le format est inattendu

# --- Interface Streamlit ---
st.title("⬆️ Mise à jour des Données")
st.markdown("Téléchargez un nouveau fichier Excel pour mettre à jour les données dans Google Sheets.")

# Recréer le dictionnaire des URLs à partir de la config
SHEET_URLS = {
    "Rencontres-024": get_edit_url_from_export_url(config.RENCONTRES_URL),
    "Disponibilites-022": get_edit_url_from_export_url(config.DISPO_URL),
    "Arbitres-052": get_edit_url_from_export_url(config.ARBITRES_URL),
    "Clubs-007": get_edit_url_from_export_url(config.CLUB_URL),
    "RencontresFFR-023": get_edit_url_from_export_url(config.RENCONTRES_FFR_URL),
    "Designations": get_edit_url_from_export_url(config.DESIGNATIONS_URL),
}

# Connexion au client gspread
gc = get_gspread_client()

if gc:
    st.subheader("1. Sélectionnez le type de données à mettre à jour")
    data_type = st.selectbox(
        "Quel type de données souhaitez-vous mettre à jour ?",
        list(SHEET_URLS.keys())
    )

    if data_type:
        selected_sheet_url = SHEET_URLS[data_type]
        st.info(f"Vous allez mettre à jour la feuille Google Sheet associée à : {data_type}")

        st.subheader("2. Téléchargez le nouveau fichier Excel")
        uploaded_file = st.file_uploader(f"Téléchargez le fichier Excel pour '{data_type}'", type=["xlsx"])

        if uploaded_file is not None:
            try:
                df_uploaded = pd.read_excel(uploaded_file)
                st.success("Fichier Excel téléchargé et lu avec succès !")
                st.dataframe(df_uploaded.head()) # Afficher un aperçu des données

                if st.button(f"Confirmer la mise à jour de '{data_type}'"):
                    with st.spinner(f"Mise à jour de la feuille '{data_type}' en cours..."):
                        if update_google_sheet(gc, selected_sheet_url, df_uploaded):
                            st.success("Mise à jour terminée ! Les données devraient être à jour dans Google Sheets.")
                            st.warning("N'oubliez pas de vider le cache de Streamlit (menu hamburger > Clear cache) si les données ne se rafraîchissent pas immédiatement dans les autres pages.")
                        else:
                            st.error("La mise à jour a échoué. Veuillez vérifier les messages d'erreur ci-dessus.")
            except Exception as e:
                st.error(f"Erreur lors de la lecture du fichier Excel : {e}")
                st.info("Assurez-vous que le fichier est un fichier Excel valide (.xlsx).")

    st.subheader("3. Effacer les données de la feuille de Désignations")
    st.warning("Attention : Ce bouton effacera TOUTES les lignes (sauf l'en-tête) de la feuille 'Designations' dans Google Sheets. Cette action est irréversible.")
    if st.button("Effacer les données de Désignations"):
        designations_sheet_url = SHEET_URLS["Designations"]
        with st.spinner("Effacement des données en cours..."):
            if clear_sheet_except_header(gc, designations_sheet_url):
                st.success("Données de Désignations effacées avec succès !")
            else:
                st.error("L'effacement des données de Désignations a échoué.")
else:
    st.warning("Impossible de se connecter à Google Sheets. Veuillez vérifier la configuration.")