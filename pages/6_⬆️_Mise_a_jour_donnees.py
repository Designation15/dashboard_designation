import streamlit as st
import pandas as pd
import re

# Importations centralisées
import config
import json
from utils import (
    get_gspread_client,
    update_google_sheet,
    clear_sheet_except_header,
    load_data,
    get_designateur_actif_nom,
    get_designateur_actif_config,
)

def get_edit_url_from_export_url(export_url):
    """Convertit une URL d'export Google Sheet en URL d'édition."""
    match = re.search(r'/d/([^/]+)', export_url)
    if match:
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    return export_url # Fallback si le format est inattendu

# --- Affichage du designateur ---
designateur_nom = get_designateur_actif_nom()
st.sidebar.markdown(f"### 👤 {designateur_nom}")
st.sidebar.markdown("---")

# --- Interface Streamlit ---
st.title("⬆️ Mise à jour des Données")
st.markdown("Téléchargez un nouveau fichier Excel pour mettre à jour les données dans Google Sheets.")

# Charger la configuration des designateurs
def load_designateurs_config():
    """Charge la configuration des designateurs depuis le fichier JSON."""
    try:
        with open('designateurs_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Fichier de configuration des designateurs introuvable.")
        return None
    except json.JSONDecodeError:
        st.error("Erreur de format dans le fichier de configuration des designateurs.")
        return None

# Récupérer les URLs spécifiques au designateur actif et les URLs partagées
config_data = load_designateurs_config()
designateur_config = get_designateur_actif_config()

if config_data and designateur_config:
    # Fichiers spécifiques au designateur actif
    SHEET_URLS_DESIGNATEUR = {
        "Rencontres-024": get_edit_url_from_export_url(designateur_config['rencontres_url']),
        "Disponibilites-022": get_edit_url_from_export_url(designateur_config['dispo_url']),
        "Rencontres-Ovale-023": get_edit_url_from_export_url(designateur_config['rencontres_ovale_url']),
        "Designations": get_edit_url_from_export_url(designateur_config['designations_url']),
    }
    
    # Fichiers partagés (commun à tous les designateurs)
    SHEET_URLS_PARTAGES = {
        "Arbitres-052": get_edit_url_from_export_url(config_data['fichiers_partages']['arbitres_url']),
        "Clubs-007": get_edit_url_from_export_url(config_data['fichiers_partages']['club_url']),
    }
    
    # Combiner les deux dictionnaires
    SHEET_URLS = {**SHEET_URLS_DESIGNATEUR, **SHEET_URLS_PARTAGES}
else:
    # Fallback vers les URLs originales en cas d'erreur
    SHEET_URLS = {
        "Rencontres-024": get_edit_url_from_export_url(config.RENCONTRES_URL),
        "Disponibilites-022": get_edit_url_from_export_url(config.DISPO_URL),
        "Arbitres-052": get_edit_url_from_export_url(config.ARBITRES_URL),
        "Clubs-007": get_edit_url_from_export_url(config.CLUB_URL),
        "Rencontres-Ovale-023": get_edit_url_from_export_url(config.RENCONTRES_FFR_URL),
        "Designations": get_edit_url_from_export_url(config.DESIGNATIONS_URL),
    }
    st.warning("Utilisation des URLs par défaut - configuration des designateurs non disponible")

# Connexion au client gspread
gc = get_gspread_client()

if gc:
    st.subheader("1. Sélectionnez le type de données à mettre à jour")
    
    # Créer des options groupées pour une meilleure expérience utilisateur
    options_designateur = list(SHEET_URLS_DESIGNATEUR.keys())
    options_partages = list(SHEET_URLS_PARTAGES.keys())
    
    # Afficher les options avec des labels explicites
    st.write("**Fichiers spécifiques au designateur :**")
    for option in options_designateur:
        st.write(f"• {option}")
    
    st.write("**Fichiers partagés (tous les designateurs) :**")
    for option in options_partages:
        st.write(f"• {option}")
    
    data_type = st.selectbox(
        "Choisissez le fichier à mettre à jour :",
        options_designateur + options_partages
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
                            st.success("Mise à jour terminée ! Les données ont été actualisées dans Google Sheets.")
                            
                            # Vider le cache de la fonction de chargement des données
                            load_data.clear()
                            
                            # Invalider le session_state pour forcer le rechargement
                            st.session_state.data_loaded = False
                            
                            st.info("Les données ont été mises à jour. Cliquez sur le bouton ci-dessous pour rafraîchir l'application.")
                            
                            if st.button("🔄 Rafraîchir l'application"):
                                st.rerun()
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
                load_data.clear()
                st.session_state.data_loaded = False
                st.info("Les données ont été mises à jour. Cliquez sur le bouton ci-dessous pour rafraîchir l'application.")
                if st.button("🔄 Rafraîchir l'application"):
                    st.rerun()
            else:
                st.error("L'effacement des données de Désignations a échoué.")
else:
    st.warning("Impossible de se connecter à Google Sheets. Veuillez vérifier la configuration.")

st.divider()
