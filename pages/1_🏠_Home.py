import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt

# --- Configuration et chargement des données ---
RENCONTRES_URL = "https://docs.google.com/spreadsheets/d/1I8RGfNNdaO1wlrtFgIOFbOnzpKszwJTxdyhQ7rRD1bg/export?format=xlsx"
DISPO_URL = "https://docs.google.com/spreadsheets/d/16-eSHsURF-H1zWx_a_Tu01E9AtmxjIXocpiR2t2ZNU4/export?format=xlsx"
ARBITRES_URL = "https://docs.google.com/spreadsheets/d/1bIUxD-GDc4V94nYoI_x2mEk0i_r9Xxnf02_Rn9YtoIc/export?format=xlsx"

COLUMN_MAPPING = {
    "rencontres_date": "DATE EFFECTIVE",
    "rencontres_competition": "COMPETITION NOM",
    "rencontres_locaux": "LOCAUX",
    "rencontres_visiteurs": "VISITEURS",
    "dispo_date": "DATE",
    "dispo_disponibilite": "DISPONIBILITE",
    "dispo_licence": "NO LICENCE",
    "arbitres_affiliation": "Numéro Affiliation",
}

@st.cache_data
def load_data(url):
    try:
        df = pd.read_excel(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Impossible de charger les données depuis {url}. Erreur: {e}")
        return pd.DataFrame()

# --- Application Principale ---
st.title("🏠 Tableau de Bord Principal")
st.markdown("L'application est en cours de développement. Il y a des zones de debuq qui seront remplacées.Vue de l'activité et des désignations à venir.")

# Chargement des données
rencontres_df = load_data(RENCONTRES_URL)
arbitres_df = load_data(ARBITRES_URL)
dispo_df = load_data(DISPO_URL)

# Convertir la colonne de date des rencontres en datetime dès le chargement
if not rencontres_df.empty:
    rencontres_df['date_dt'] = pd.to_datetime(rencontres_df[COLUMN_MAPPING['rencontres_date']], errors='coerce', dayfirst=True)

    # Calculer la date min et max du fichier des rencontres
    min_rencontre_file_date = rencontres_df['date_dt'].min().strftime('%d/%m/%Y')
    max_rencontre_file_date = rencontres_df['date_dt'].max().strftime('%d/%m/%Y')

    # Alerte si des dates sont antérieures à la date du jour
    today = pd.to_datetime(datetime.now().date())
    if (rencontres_df['date_dt'] < today).any():
        st.warning(f"⚠️ Attention : Certaines rencontres sont antérieures à la date du jour. Le fichier couvre du {min_rencontre_file_date} au {max_rencontre_file_date}. Pensez à mettre à jour vos données !", icon="🚨")

# --- Métriques Clés ---
st.header("Statistiques Clés")

total_rencontres = len(rencontres_df)
total_arbitres = len(arbitres_df)

available_referees_count = 0

with st.expander("🔍 Debug: Calcul des arbitres disponibles", expanded=False):
    st.write(f"Date du jour : {datetime.now().date()}")
    
    # Déterminer la plage de dates à partir des rencontres
    min_rencontre_date = None
    max_rencontre_date = None
    if not rencontres_df.empty:
        rencontres_df['date_dt'] = pd.to_datetime(rencontres_df[COLUMN_MAPPING['rencontres_date']], errors='coerce', dayfirst=True)
        min_rencontre_date = rencontres_df['date_dt'].min()
        max_rencontre_date = rencontres_df['date_dt'].max()
        st.write(f"Plage de dates des rencontres : du {min_rencontre_date.strftime('%d/%m/%Y')} au {max_rencontre_date.strftime('%d/%m/%Y')}")
    else:
        st.write("Aucune rencontre trouvée pour déterminer la plage de dates.")

    if min_rencontre_date and max_rencontre_date and not dispo_df.empty:
        dispo_df['DATE EFFECTIVE'] = pd.to_datetime(dispo_df[COLUMN_MAPPING['dispo_date']], errors='coerce')
        
        # Filtrer les disponibilités sur la plage de dates des rencontres
        filtered_dispo = dispo_df[
            (dispo_df['DATE EFFECTIVE'] >= min_rencontre_date) & 
            (dispo_df['DATE EFFECTIVE'] <= max_rencontre_date)
        ]
        st.write(f"Nombre de lignes dans dispo_df filtrées par la plage des rencontres : {len(filtered_dispo)}")
        st.write(f"Valeurs uniques de 'DISPONIBILITE' dans les disponibilités filtrées : {filtered_dispo[COLUMN_MAPPING['dispo_disponibilite']].unique()}")

        if not filtered_dispo.empty:
            available_referees_count = filtered_dispo[filtered_dispo[COLUMN_MAPPING['dispo_disponibilite']].str.upper() == 'OUI'][COLUMN_MAPPING['dispo_licence']].nunique()
        st.write(f"Nombre final d'arbitres disponibles calculé : {available_referees_count}")
    else:
        st.write("dispo_df est vide ou aucune rencontre pour déterminer la plage, impossible de calculer les arbitres disponibles.")

col1, col2, col3 = st.columns(3)
col1.metric(label="📅 Total des Rencontres", value=total_rencontres)
col2.metric(label="👤 Total des Arbitres", value=total_arbitres)
col3.metric(label="✅ Arbitres Disponibles (Plage des rencontres)", value=available_referees_count)

st.divider()

# --- Prochaines Rencontres à Désigner ---
st.header("⚡ Prochaines Rencontres à Désigner")

if not rencontres_df.empty:
    rencontres_df['date_dt'] = pd.to_datetime(rencontres_df[COLUMN_MAPPING['rencontres_date']], errors='coerce', dayfirst=True)
    today = pd.to_datetime(datetime.now().date())
    prochaines_rencontres = rencontres_df[rencontres_df['date_dt'] >= today].copy()

    if not prochaines_rencontres.empty:
        prochaines_rencontres = prochaines_rencontres.sort_values(by='date_dt')
        cols_a_afficher = [
            COLUMN_MAPPING['rencontres_date'],
            COLUMN_MAPPING['rencontres_competition'],
            COLUMN_MAPPING['rencontres_locaux'],
            COLUMN_MAPPING['rencontres_visiteurs']
        ]
        prochaines_rencontres_display = prochaines_rencontres[cols_a_afficher].rename(columns={
            COLUMN_MAPPING['rencontres_date']: "Date",
            COLUMN_MAPPING['rencontres_competition']: "Compétition",
            COLUMN_MAPPING['rencontres_locaux']: "Équipe à Domicile",
            COLUMN_MAPPING['rencontres_visiteurs']: "Équipe Visiteuse"
        })
        st.dataframe(prochaines_rencontres_display.head(10), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune rencontre à venir n'a été trouvée.")
else:
    st.info("Aucune donnée de rencontre disponible.")

st.divider()

st.header("📊 Nombre de Rencontres par Jour (toutes dates)")
if not rencontres_df.empty:
    # Compter le nombre de rencontres par jour
    rencontres_par_jour = rencontres_df.groupby(rencontres_df['date_dt'].dt.date).size().reset_index(name='Nombre de Rencontres')
    rencontres_par_jour.columns = ['Date', 'Nombre de Rencontres']
    rencontres_par_jour['Date'] = pd.to_datetime(rencontres_par_jour['Date']) # Convertir en datetime pour Altair

    # Formater la date en JJ/MM/AAAA pour l'affichage
    rencontres_par_jour['Date'] = rencontres_par_jour['Date'].dt.strftime('%d/%m/%Y')

    st.dataframe(rencontres_par_jour, use_container_width=True, hide_index=True)
else:
    st.info("Aucune donnée de rencontre disponible pour afficher la répartition par jour.")

st.divider()
st.info("Utilisez le menu à gauche pour naviguer.")