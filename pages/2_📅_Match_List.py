import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

import config

# --- Récupération des données ---
rencontres_df = st.session_state.get('rencontres_df', pd.DataFrame())
competitions_df = st.session_state.get('competitions_df', pd.DataFrame())

st.title("📅 Liste des Rencontres")
st.markdown("RS_OVALE2-024 - Vue consolidée de toutes les rencontres")

if not rencontres_df.empty and 'rencontres_date_dt' in rencontres_df.columns:
    rencontres_filtrees = rencontres_df.copy()

    st.sidebar.header("Filtres Rencontres")
    
    min_df_date = rencontres_filtrees['rencontres_date_dt'].min().date()
    max_df_date = rencontres_filtrees['rencontres_date_dt'].max().date()
    
    selected_date_range = st.sidebar.date_input(
        "Filtrer par date",
        value=(min_df_date, max_df_date),
        min_value=min_df_date,
        max_value=max_df_date
    )

    if len(selected_date_range) == 2:
        start_date, end_date = selected_date_range
        rencontres_filtrees = rencontres_filtrees[
            (rencontres_filtrees['rencontres_date_dt'].dt.date >= start_date) &
            (rencontres_filtrees['rencontres_date_dt'].dt.date <= end_date)
        ]
    
    all_competitions = ["Toutes"] + list(competitions_df[config.COLUMN_MAPPING['competitions_nom']].unique())
    selected_competition = st.sidebar.selectbox(
        "Filtrer par compétition",
        options=all_competitions
    )

    if selected_competition != "Toutes":
        rencontres_filtrees = rencontres_filtrees[rencontres_filtrees[config.COLUMN_MAPPING['rencontres_competition']] == selected_competition]

    if not rencontres_filtrees.empty:
        cols_to_display = [
            config.COLUMN_MAPPING['rencontres_date'],
            config.COLUMN_MAPPING['rencontres_competition'],
            config.COLUMN_MAPPING['rencontres_locaux'],
            config.COLUMN_MAPPING['rencontres_visiteurs']
        ]
        display_df = rencontres_filtrees[cols_to_display].copy()

        # Formater la date pour l'affichage final
        display_df[config.COLUMN_MAPPING['rencontres_date']] = pd.to_datetime(display_df[config.COLUMN_MAPPING['rencontres_date']], errors='coerce').dt.strftime('%d/%m/%Y')

        display_df = display_df.rename(columns={
            config.COLUMN_MAPPING['rencontres_date']: 'Date',
            config.COLUMN_MAPPING['rencontres_competition']: 'Compétition',
            config.COLUMN_MAPPING['rencontres_locaux']: 'Locaux',
            config.COLUMN_MAPPING['rencontres_visiteurs']: 'Visiteurs'
        })

        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)
        gridOptions = gb.build()

        AgGrid(
            display_df,
            gridOptions=gridOptions,
            enable_enterprise_modules=False,
            height=600,
            width='100%',
            reload_data=True,
            allow_unsafe_jscode=True,
            theme='streamlit'
        )
    else:
        st.info("Aucune rencontre trouvée avec les filtres appliqués.")
else:
    st.warning("Impossible de charger les données des rencontres.")