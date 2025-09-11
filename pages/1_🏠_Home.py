import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt

import config

st.title("🏠 Tableau de Bord Principal")
st.markdown("Vue de l'activité et des désignations à venir.")

# Récupération des données déjà traitées depuis la session
rencontres_df = st.session_state.get('rencontres_df', pd.DataFrame())
arbitres_df = st.session_state.get('arbitres_df', pd.DataFrame())
dispo_df = st.session_state.get('dispo_df', pd.DataFrame())

# --- Filtre par défaut ---
st.header("Filtre")

# Utilisation de la liste centralisée depuis config.py
competitions_filtre_defaut = config.COMPETITIONS_FILTRE_DEFAUT

# Bouton toggle pour activer/désactiver le filtre par défaut
filtre_actif = st.checkbox("Activer le filtre par compétitions", value=True)

# Application du filtre aux données
rencontres_filtrees_df = rencontres_df
if filtre_actif and not rencontres_df.empty and config.COLUMN_MAPPING['rencontres_competition'] in rencontres_df.columns:
    rencontres_filtrees_df = rencontres_df[rencontres_df[config.COLUMN_MAPPING['rencontres_competition']].isin(competitions_filtre_defaut)]

# --- Affichage des métriques ---

st.header("Statistiques Clés")

# Alerte si des dates sont antérieures à la date du jour
if not rencontres_filtrees_df.empty and 'rencontres_date_dt' in rencontres_filtrees_df.columns:
    min_rencontre_file_date = rencontres_filtrees_df['rencontres_date_dt'].min().strftime('%d/%m/%Y')
    max_rencontre_file_date = rencontres_filtrees_df['rencontres_date_dt'].max().strftime('%d/%m/%Y')
    today = pd.to_datetime(datetime.now().date())
    if (rencontres_filtrees_df['rencontres_date_dt'] < today).any():
        st.warning(f"⚠️ Attention : Certaines rencontres sont antérieures à la date du jour. Le fichier couvre du {min_rencontre_file_date} au {max_rencontre_file_date}. Pensez à mettre à jour vos données !", icon="🚨")

total_rencontres = len(rencontres_filtrees_df)
total_arbitres = len(arbitres_df)
available_referees_count = 0

# Calcul des arbitres disponibles
if not rencontres_filtrees_df.empty and not dispo_df.empty and 'rencontres_date_dt' in rencontres_filtrees_df.columns and 'DATE_dt' in dispo_df.columns:
    min_rencontre_date = rencontres_filtrees_df['rencontres_date_dt'].min()
    max_rencontre_date = rencontres_filtrees_df['rencontres_date_dt'].max()
    
    filtered_dispo = dispo_df[
        (dispo_df['DATE_dt'] >= min_rencontre_date) & 
        (dispo_df['DATE_dt'] <= max_rencontre_date)
    ]
    if not filtered_dispo.empty:
        available_referees_count = filtered_dispo[filtered_dispo[config.COLUMN_MAPPING['dispo_disponibilite']].str.upper() == 'OUI'][config.COLUMN_MAPPING['dispo_licence']].nunique()

col1, col2, col3 = st.columns(3)
col1.metric(label="📅 Total des Rencontres", value=total_rencontres)
col2.metric(label="👤 Total des Arbitres", value=total_arbitres)
col3.metric(label="✅ Arbitres Disponibles (Plage des rencontres)", value=available_referees_count)

st.divider()

# --- Prochaines Rencontres à Désigner ---
st.header("⚡ Prochaines Rencontres à Désigner")

if not rencontres_filtrees_df.empty and 'rencontres_date_dt' in rencontres_filtrees_df.columns:
    today = pd.to_datetime(datetime.now().date())
    prochaines_rencontres = rencontres_filtrees_df[rencontres_filtrees_df['rencontres_date_dt'] >= today].copy()

    if not prochaines_rencontres.empty:
        prochaines_rencontres = prochaines_rencontres.sort_values(by='rencontres_date_dt')
        cols_a_afficher = [config.COLUMN_MAPPING['rencontres_date'], config.COLUMN_MAPPING['rencontres_competition'], config.COLUMN_MAPPING['rencontres_locaux'], config.COLUMN_MAPPING['rencontres_visiteurs']]
        prochaines_rencontres_display = prochaines_rencontres[cols_a_afficher].rename(columns={
            config.COLUMN_MAPPING['rencontres_date']: "Date",
            config.COLUMN_MAPPING['rencontres_competition']: "Compétition",
            config.COLUMN_MAPPING['rencontres_locaux']: "Équipe à Domicile",
            config.COLUMN_MAPPING['rencontres_visiteurs']: "Équipe Visiteuse"
        })
        st.dataframe(prochaines_rencontres_display.head(10), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune rencontre à venir n'a été trouvée.")
else:
    st.info("Aucune donnée de rencontre disponible.")

st.divider()

st.header("📊 Nombre de Rencontres par Jour (toutes dates)")
if not rencontres_filtrees_df.empty and 'rencontres_date_dt' in rencontres_filtrees_df.columns:
    rencontres_par_jour = rencontres_filtrees_df.groupby(rencontres_filtrees_df['rencontres_date_dt'].dt.date).size().reset_index(name='Nombre de Rencontres')
    rencontres_par_jour.columns = ['Date', 'Nombre de Rencontres']
    rencontres_par_jour['Date_dt'] = pd.to_datetime(rencontres_par_jour['Date'])
    rencontres_par_jour['Date'] = rencontres_par_jour['Date_dt'].dt.strftime('%d/%m/%Y')

    st.dataframe(rencontres_par_jour[['Date', 'Nombre de Rencontres']], use_container_width=True, hide_index=True)
else:
    st.info("Aucune donnée de rencontre disponible pour afficher la répartition par jour.")
