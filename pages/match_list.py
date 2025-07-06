import streamlit as st
import pandas as pd

from st_aggrid import AgGrid, GridOptionsBuilder

def app(data_frames, column_mapping):
    st.title("Liste des Rencontres")

    rencontres_df = data_frames["rencontres_df"].copy()
    competitions_df = data_frames["competitions_df"].copy()

    # Assurez-vous que la colonne de date est au bon format
    rencontres_df[column_mapping['rencontres_date']] = pd.to_datetime(rencontres_df[column_mapping['rencontres_date']], errors='coerce')

    # Filtres
    st.sidebar.header("Filtres Rencontres")

    # Filtre par date
    min_date = rencontres_df[column_mapping['rencontres_date']].min().date()
    max_date = rencontres_df[column_mapping['rencontres_date']].max().date()
    selected_date_range = st.sidebar.date_input(
        "Filtrer par date",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Assurez-vous que selected_date_range est un tuple
    if len(selected_date_range) == 2:
        start_date, end_date = selected_date_range
        rencontres_filtrees = rencontres_df[
            (rencontres_df[column_mapping['rencontres_date']].dt.date >= start_date) &
            (rencontres_df[column_mapping['rencontres_date']].dt.date <= end_date)
        ]
    else:
        rencontres_filtrees = rencontres_df # Si une seule date est sélectionnée, ne pas filtrer par date

    # Filtre par compétition
    all_competitions = ["Toutes"] + list(competitions_df[column_mapping['competitions_nom']].unique())
    selected_competition = st.sidebar.selectbox(
        "Filtrer par compétition",
        options=all_competitions
    )

    if selected_competition != "Toutes":
        rencontres_filtrees = rencontres_filtrees[rencontres_filtrees[column_mapping['rencontres_competition']] == selected_competition]

    # Affichage des rencontres filtrées
    if not rencontres_filtrees.empty:
        display_df = rencontres_filtrees[[
            column_mapping['rencontres_date'],
            column_mapping['rencontres_competition'],
            column_mapping['rencontres_locaux'],
            column_mapping['rencontres_visiteurs']
        ]].copy()

        # Formater la colonne de date pour l'affichage
        display_df[column_mapping['rencontres_date']] = display_df[column_mapping['rencontres_date']].dt.strftime('%d/%m/%Y')

        # Renommer les colonnes pour un affichage plus lisible
        display_df = display_df.rename(columns={
            column_mapping['rencontres_date']: 'Date',
            column_mapping['rencontres_competition']: 'Compétition',
            column_mapping['rencontres_locaux']: 'Locaux',
            column_mapping['rencontres_visiteurs']: 'Visiteurs'
        })

        # Configuration de la grille AG Grid
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)
        gridOptions = gb.build()

        AgGrid(
            display_df,
            gridOptions=gridOptions,
            enable_enterprise_modules=False, # Mettre à True si vous avez une licence
            height=600,
            width='100%',
            reload_data=True,
            allow_unsafe_jscode=True, # Mettre à True pour permettre les callbacks JS
            theme='streamlit' # Thèmes possibles : streamlit, alpine, balham, material
        )
    else:
        st.info("Aucune rencontre trouvée avec les filtres appliqués.")
