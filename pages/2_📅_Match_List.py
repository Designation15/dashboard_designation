import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

# --- Configuration et chargement des données ---
RENCONTRES_URL = "https://docs.google.com/spreadsheets/d/1I8RGfNNdaO1wlrtFgIOFbOnzpKszwJTxdyhQ7rRD1bg/export?format=xlsx"

COLUMN_MAPPING = {
    "rencontres_date": "DATE EFFECTIVE",
    "rencontres_competition": "COMPETITION NOM",
    "rencontres_locaux": "LOCAUX",
    "rencontres_visiteurs": "VISITEURS",
    "competitions_nom": "NOM",
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

@st.cache_data
def load_static_competitions():
    competitions_data = {
        'NOM': [
            'Elite 1 Féminine', 'Elite 2 Féminine', 'Elite Alamercery', 'Elite Crabos', 
            'Espoirs Fédéraux', 'European Rugby Champions Cup', 'Excellence B - Championnat de France', 
            'Fédérale 1', 'Fédérale 2', 'Fédérale 3', 'Fédérale B - Championnat de France', 
            'Féminines Moins de 18 ans à XV - ELITE', 'Féminines Régionales à X', 
            'Féminines Régionales à X « moins de 18 ans »', 'Régional 1 U16', 'Régional 1 U19', 
            'Régional 2 U16', 'Régional 2 U19', 'Régional 3 U16', 'Régional 3 U19', 
            'Régionale 1 - Championnat Territorial', 'Régionale 2 - Championnat Territorial', 
            'Régionale 3 - Championnat Territorial', 'Réserves Elite', 
            'Réserves Régionales 1 - Championnat Territorial', 'Réserves Régionales 2 - Championnat Territorial'
        ],
        'NIVEAU MIN': [6, 7, 7, 6, 6, 1, 9, 6, 7, 8, 9, 7, 13, 14, 15, 10, 15, 13, 15, 13, 9, 11, 13, 7, 11, 13],
        'NIVEAU MAX': [4, 6, 6, 4, 4, 1, 7, 6, 7, 8, 7, 6, 10, 13, 9, 9, 9, 9, 9, 9, 7, 9, 9, 9, 9, 11]
    }
    return pd.DataFrame(competitions_data)

# --- Chargement des données ---
rencontres_df = load_data(RENCONTRES_URL)
competitions_df = load_static_competitions()

# --- Application ---
st.title("📅 Liste des Rencontres")
st.markdown("RS_OVALE2-024 - Vue consolidée de toutes les rencontres")

if not rencontres_df.empty:
    # Convertir la colonne de date avec dayfirst=True
    rencontres_df[COLUMN_MAPPING['rencontres_date']] = pd.to_datetime(rencontres_df[COLUMN_MAPPING['rencontres_date']], errors='coerce', dayfirst=True)

    st.sidebar.header("Filtres Rencontres")
    
    # Debug: Afficher les dates min/max du DataFrame
    min_df_date = rencontres_df[COLUMN_MAPPING['rencontres_date']].min().date()
    max_df_date = rencontres_df[COLUMN_MAPPING['rencontres_date']].max().date()
    st.sidebar.write(f"Dates disponibles dans le fichier : {min_df_date.strftime('%d/%m/%Y')} - {max_df_date.strftime('%d/%m/%Y')}")

    selected_date_range = st.sidebar.date_input(
        "Filtrer par date",
        value=(min_df_date, max_df_date),
        min_value=min_df_date,
        max_value=max_df_date
    )

    rencontres_filtrees = rencontres_df.copy() # Initialiser avec toutes les rencontres

    # Assurez-vous que selected_date_range est un tuple de deux dates
    if len(selected_date_range) == 2:
        start_date, end_date = selected_date_range
        st.sidebar.write(f"Dates sélectionnées par le filtre : {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")

        rencontres_filtrees = rencontres_filtrees[
            (rencontres_filtrees[COLUMN_MAPPING['rencontres_date']].dt.date >= start_date) &
            (rencontres_filtrees[COLUMN_MAPPING['rencontres_date']].dt.date <= end_date)
        ]
    else:
        st.sidebar.write("Veuillez sélectionner une plage de dates.")

    # Filtre par compétition
    all_competitions = ["Toutes"] + list(competitions_df[COLUMN_MAPPING['competitions_nom']].unique())
    selected_competition = st.sidebar.selectbox(
        "Filtrer par compétition",
        options=all_competitions
    )

    if selected_competition != "Toutes":
        rencontres_filtrees = rencontres_filtrees[rencontres_filtrees[COLUMN_MAPPING['rencontres_competition']] == selected_competition]

    # Affichage des rencontres filtrées
    if not rencontres_filtrees.empty:
        display_df = rencontres_filtrees[[
            COLUMN_MAPPING['rencontres_date'],
            COLUMN_MAPPING['rencontres_competition'],
            COLUMN_MAPPING['rencontres_locaux'],
            COLUMN_MAPPING['rencontres_visiteurs']
        ]].copy()

        # Formater la colonne de date pour l'affichage
        display_df[COLUMN_MAPPING['rencontres_date']] = display_df[COLUMN_MAPPING['rencontres_date']].dt.strftime('%d/%m/%Y')

        # Renommer les colonnes pour un affichage plus lisible
        display_df = display_df.rename(columns={
            COLUMN_MAPPING['rencontres_date']: 'Date',
            COLUMN_MAPPING['rencontres_competition']: 'Compétition',
            COLUMN_MAPPING['rencontres_locaux']: 'Locaux',
            COLUMN_MAPPING['rencontres_visiteurs']: 'Visiteurs'
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
else:
    st.warning("Impossible de charger les données des rencontres.")