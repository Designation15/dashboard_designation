import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# --- Configuration ---     
# Chemin vers votre fichier JSON de compte de service
SERVICE_ACCOUNT_FILE = 'designation-cle.json' 

# URLs de vos feuilles Google Sheets (utilisez les mêmes que dans vos autres pages)
# Assurez-vous que ces URLs correspondent aux feuilles que vous voulez mettre à jour
SHEET_URLS = {
    "Rencontres-024": "https://docs.google.com/spreadsheets/d/1I8RGfNNdaO1wlrtFgIOFbOnzpKszwJTxdyhQ7rRD1bg/edit",
    "Disponibilites-022": "https://docs.google.com/spreadsheets/d/16-eSHsURF-H1zWx_a_Tu01E9AtmxjIXocpiR2t2ZNU4/edit",
    "Arbitres-052": "https://docs.google.com/spreadsheets/d/1bIUxD-GDc4V94nYoI_x2mEk0i_r9Xxnf02_Rn9YtoIc/edit",
    "Clubs-007": "https://docs.google.com/spreadsheets/d/1GLWS4jOmwv-AOtkFZ5-b5JcjaSpBVlwqcuOCRRmEVPQ/edit",
    "RencontresFFR": "https://docs.google.com/spreadsheets/d/1ViKipszuqE5LPbTcFk2QvmYq4ZNQZVs9LbzrUVC4p4Y/edit",
}


# --- Fonction d'authentification et de connexion à Google Sheets ---
@st.cache_resource(ttl=3600) # Cache la connexion pour 1 heure
def get_gspread_client():
    try:
        st.write("Début de la tentative d'authentification gspread.")
        # Priorité au fichier local pour le développement
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            st.write("Utilisation du fichier de clé de service local.")
            creds = Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE,
                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            )
        # Sinon, essayer d'utiliser les secrets de Streamlit (pour le déploiement)
        elif "gcp_service_account" in st.secrets:
            st.write("Utilisation des secrets Streamlit pour l'authentification.")
            creds_dict = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            )
        else:
            st.error("Configuration d'authentification introuvable.")
            st.info(f"Pour le développement local, assurez-vous que le fichier '{SERVICE_ACCOUNT_FILE}' est présent. Pour le déploiement sur Streamlit, assurez-vous que les secrets 'gcp_service_account' sont correctement configurés.")
            return None

        st.write(f"Authentification réussie. Email du compte de service : {creds.service_account_email}")
        client = gspread.authorize(creds)
        st.success("Connexion à Google Sheets réussie !")
        return client
    except Exception as e:
        st.error(f"Erreur lors de l'authentification avec Google Sheets : {e}")
        st.exception(e) # Affiche la trace complète de l'exception
        st.info("Vérifiez la configuration de vos secrets sur Streamlit Cloud ou votre fichier JSON local.")
        return None

# --- Fonction de mise à jour de la feuille Google Sheet ---
def update_google_sheet(client, sheet_url, df_new, data_type):
    try:
        # Extraire l'ID de la feuille de l'URL
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        st.write(f"Tentative d'ouverture de la feuille avec l'ID : {sheet_id}")
        spreadsheet = client.open_by_url(sheet_url) # Changement ici : open_by_url au lieu de open_by_key
        
        # Sélectionner la première feuille (index 0) du classeur
        worksheet = spreadsheet.get_worksheet(0)

        # Effacer le contenu existant
        worksheet.clear()

        # Convertir les colonnes de type datetime en string pour éviter TypeError
        for col in df_new.select_dtypes(include=['datetime64', 'datetime64[ns]']).columns:
            df_new[col] = df_new[col].dt.strftime('%Y-%m-%d %H:%M:%S') # Format ISO ou autre format lisible

        # Gérer les valeurs NaN dans les colonnes pour éviter InvalidJSONError
        # Convertir le DataFrame en liste de listes, en remplaçant les NaN par None
        data_to_write = df_new.astype(object).where(pd.notna(df_new), None).values.tolist()

        # Écrire les en-têtes et les données
        worksheet.update([df_new.columns.values.tolist()] + data_to_write)
        st.success(f"Feuille Google Sheet mise à jour avec succès pour l'URL : {sheet_url}")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Erreur : Feuille Google Sheet introuvable pour l'URL : {sheet_url}. Vérifiez l'ID et les permissions.")
        return False
    except gspread.exceptions.APIError as e:
        st.error(f"Erreur API Google Sheets lors de la mise à jour ({sheet_url}) : {e.response.text}")
        st.exception(e)
        return False
    except Exception as e:
        st.error(f"Erreur inattendue lors de la mise à jour de la feuille Google Sheet ({sheet_url}) : {e}")
        st.exception(e) # Affiche la trace complète de l'exception
        return False

# --- Interface Streamlit ---
st.title("⬆️ Mise à jour des Données")
st.markdown("Téléchargez un nouveau fichier Excel pour mettre à jour les données dans Google Sheets.")

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
        st.info(f"Vous allez mettre à jour la feuille Google Sheet associée à : {data_type} (URL: {selected_sheet_url})")

        st.subheader("2. Téléchargez le nouveau fichier Excel")
        uploaded_file = st.file_uploader(f"Téléchargez le fichier Excel pour '{data_type}'", type=["xlsx"])

        if uploaded_file is not None:
            try:
                df_uploaded = pd.read_excel(uploaded_file)
                st.success("Fichier Excel téléchargé et lu avec succès !")
                st.dataframe(df_uploaded.head()) # Afficher un aperçu des données

                if st.button(f"Confirmer la mise à jour de '{data_type}'"):
                    with st.spinner(f"Mise à jour de la feuille '{data_type}' en cours..."):
                        if update_google_sheet(gc, selected_sheet_url, df_uploaded, data_type):
                            st.success("Mise à jour terminée ! Les données devraient être à jour dans Google Sheets.")
                            st.warning("N'oubliez pas de vider le cache de Streamlit (menu hamburger > Clear cache) si les données ne se rafraîchissent pas immédiatement dans les autres pages.")
                        else:
                            st.error("La mise à jour a échoué. Veuillez vérifier les messages d'erreur ci-dessus.")
            except Exception as e:
                st.error(f"Erreur lors de la lecture du fichier Excel : {e}")
                st.info("Assurez-vous que le fichier est un fichier Excel valide (.xlsx).")
else:
    st.warning("Impossible de se connecter à Google Sheets. Veuillez vérifier la configuration.")
