import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt

def app(data_frames, column_mapping):
    st.title("Bienvenue dans l'Outil d'aide à la désignation")
    st.markdown("Votre tableau de bord central pour la gestion des arbitres de rugby.")

    # --- Récupération des données ---
    rencontres_df = data_frames["rencontres_df"]
    arbitres_df = data_frames["arbitres_df"]
    competitions_df = data_frames["competitions_df"]
    dispo_df = data_frames["dispo_df"]

    # --- KPIs ---
    st.header("Statistiques Clés")

    # Calculs
    total_rencontres = len(rencontres_df)
    total_arbitres = len(arbitres_df)
    total_competitions = len(competitions_df)

    # Affichage en colonnes
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total des Rencontres", value=total_rencontres)
    with col2:
        st.metric(label="Total des Arbitres", value=total_arbitres)
    with col3:
        st.metric(label="Total des Compétitions", value=total_competitions)

    st.markdown("---")

    # --- Graphiques ---
    st.header("Aperçu Visuel")

    # 1. Répartition des arbitres par catégorie
    if not arbitres_df.empty:
        arbitres_par_categorie = arbitres_df[column_mapping['arbitres_categorie']].value_counts().reset_index()
        arbitres_par_categorie.columns = ['Catégorie', "Nombre d'arbitres"]
        chart_arbitres_cat = alt.Chart(arbitres_par_categorie).mark_bar().encode(
            x=alt.X('Catégorie', sort='-y'),
            y='Nombre d\'arbitres',
            tooltip=['Catégorie', 'Nombre d\'arbitres']
        ).properties(
            title='Répartition des Arbitres par Catégorie'
        )
        st.altair_chart(chart_arbitres_cat, use_container_width=True)
    else:
        st.info("Aucune donnée d'arbitre disponible pour les graphiques.")

    st.markdown("---")

    # 2. Nombre de rencontres par compétition
    if not rencontres_df.empty:
        rencontres_par_competition = rencontres_df[column_mapping['rencontres_competition']].value_counts().reset_index()
        rencontres_par_competition.columns = ['Compétition', 'Nombre de rencontres']
        chart_rencontres_comp = alt.Chart(rencontres_par_competition).mark_bar().encode(
            x=alt.X('Compétition', sort='-y'),
            y='Nombre de rencontres',
            tooltip=['Compétition', 'Nombre de rencontres']
        ).properties(
            title='Nombre de Rencontres par Compétition'
        )
        st.altair_chart(chart_rencontres_comp, use_container_width=True)
    else:
        st.info("Aucune donnée de rencontre disponible pour les graphiques.")

    st.markdown("---")

    # 3. Nombre d'arbitres disponibles par jour (si les données le permettent)
    if not dispo_df.empty:
        dispo_df['DATE EFFECTIVE'] = pd.to_datetime(dispo_df[column_mapping['dispo_date']], errors='coerce')
        available_referees = dispo_df[dispo_df[column_mapping['dispo_disponibilite']] == 'OUI']
        
        if not available_referees.empty:
            referees_per_day = available_referees.groupby(available_referees['DATE EFFECTIVE'].dt.date).size().reset_index(name="Nombre d'arbitres disponibles")
            referees_per_day.columns = ['Date', "Nombre d'arbitres disponibles"]
            referees_per_day['Date'] = pd.to_datetime(referees_per_day['Date'])
            chart_dispo_jour = alt.Chart(referees_per_day).mark_line().encode(
                x=alt.X('Date', type='temporal'),
                y='Nombre d\'arbitres disponibles',
                tooltip=['Date', 'Nombre d\'arbitres disponibles']
            ).properties(
                title='Nombre d\'arbitres disponibles par jour'
            )
            st.altair_chart(chart_dispo_jour, use_container_width=True)
        else:
            st.info("Aucune donnée de disponibilité 'OUI' trouvée pour les graphiques.")
    else:
        st.info("Aucune donnée de disponibilité disponible pour les graphiques.")

    st.markdown("---")

    # --- Prochaines Rencontres ---
    st.header("Prochaines Rencontres à Désigner")

    # S'assurer que la colonne de date est au format datetime
    date_col = column_mapping['rencontres_date']
    # La conversion de date est déjà faite en amont, nous pouvons l'utiliser directement
    rencontres_df['date_dt'] = pd.to_datetime(rencontres_df[date_col], errors='coerce', dayfirst=True)


    # Filtrer les rencontres futures
    today = pd.to_datetime(datetime.now().date())
    prochaines_rencontres = rencontres_df[rencontres_df['date_dt'] >= today].copy()

    if not prochaines_rencontres.empty:
        # Trier par date
        prochaines_rencontres = prochaines_rencontres.sort_values(by='date_dt')

        # Sélection des colonnes à afficher
        cols_a_afficher = [
            column_mapping['rencontres_date'],
            column_mapping['rencontres_competition'],
            column_mapping['rencontres_locaux'],
            column_mapping['rencontres_visiteurs']
        ]
        
        # Renommer les colonnes pour un affichage plus clair
        prochaines_rencontres_display = prochaines_rencontres[cols_a_afficher].rename(columns={
            column_mapping['rencontres_date']: "Date",
            column_mapping['rencontres_competition']: "Compétition",
            column_mapping['rencontres_locaux']: "Équipe à Domicile",
            column_mapping['rencontres_visiteurs']: "Équipe Visiteuse"
        })

        st.dataframe(prochaines_rencontres_display.head(10), use_container_width=True)
    else:
        st.info("Aucune rencontre à venir n'a été trouvée.")
    
    st.markdown("---")
    st.info("Utilisez le menu latéral pour naviguer vers la page de désignation ou pour voir la liste complète des matchs.")
