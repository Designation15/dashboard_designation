import streamlit as st
import pandas as pd
from datetime import datetime
from utils import highlight_designated_cells

# --- Configuration et chargement des données ---
ARBITRES_URL = "https://docs.google.com/spreadsheets/d/1bIUxD-GDc4V94nYoI_x2mEk0i_r9Xxnf02_Rn9YtoIc/export?format=xlsx"
DISPO_URL = "https://docs.google.com/spreadsheets/d/16-eSHsURF-H1zWx_a_Tu01E9AtmxjIXocpiR2t2ZNU4/export?format=xlsx"

COLUMN_MAPPING = {
    "dispo_date": "DATE",
    "dispo_disponibilite": "DISPONIBILITE",
    "dispo_licence": "NO LICENCE",
    "dispo_designation": "DESIGNATION",
    "arbitres_affiliation": "Numéro Affiliation",
    "arbitres_nom": "Nom",
    "arbitres_prenom": "Prénom",
    "arbitres_categorie": "Catégorie",
    "categories_nom": "CATEGORIE",
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

# --- Chargement des données ---
arbitres_df = load_data(ARBITRES_URL)
dispo_df = load_data(DISPO_URL)

# --- Application ---
st.title("✅ Disponibilités des Arbitres")
st.markdown("RS_OVALE2-022 - Vue consolidée de toutes les disponibilités des arbitres.")

if st.button("🔄 Vider le cache et recharger les données"):
    st.cache_data.clear()
    st.rerun()

st.header("Filtres")

if not arbitres_df.empty:
    all_categories = ["Toutes"] + list(arbitres_df[COLUMN_MAPPING['arbitres_categorie']].unique())
    selected_categories = st.multiselect(
        "Filtrer par catégorie d'arbitre",
        options=all_categories,
        default=["Toutes"]
    )

    if "Toutes" not in selected_categories:
        arbitres_filtres = arbitres_df[arbitres_df[COLUMN_MAPPING['arbitres_categorie']].isin(selected_categories)]
    else:
        arbitres_filtres = arbitres_df

    if not dispo_df.empty:
        dispo_df['DATE EFFECTIVE'] = pd.to_datetime(dispo_df[COLUMN_MAPPING['dispo_date']], errors='coerce')
        dispo_a_merger = dispo_df[[
            COLUMN_MAPPING['dispo_licence'],
            COLUMN_MAPPING['dispo_disponibilite'],
            COLUMN_MAPPING['dispo_designation'],
            'DATE EFFECTIVE'
        ]]
        arbitres_avec_dispo = pd.merge(
            arbitres_filtres,
            dispo_a_merger,
            left_on=COLUMN_MAPPING['arbitres_affiliation'],
            right_on=COLUMN_MAPPING['dispo_licence'],
            how='inner'
        )

        st.header("Grille des Disponibilités")
        if not arbitres_avec_dispo.empty:
            arbitres_avec_dispo['DATE_AFFICHAGE'] = arbitres_avec_dispo['DATE EFFECTIVE'].dt.strftime('%d/%m/%Y')
            # Vérification des colonnes nécessaires
            required_cols = ['Club', 'Nombre  de matchs à arbitrer']
            if not all(col in arbitres_df.columns for col in required_cols):
                st.error(f"Colonnes manquantes dans arbitres_df. Requises: {required_cols}")
                st.write("Colonnes disponibles:", arbitres_df.columns.tolist())
                st.stop()

            # Ajout des colonnes Club et Nb matchs à arbitrer
            arbitres_avec_dispo = arbitres_avec_dispo.merge(
                arbitres_df[[COLUMN_MAPPING['arbitres_affiliation'], 'Club', 'Nombre  de matchs à arbitrer']],
                on=COLUMN_MAPPING['arbitres_affiliation'],
                how='left'
            )
            
            # Vérification finale des colonnes avec les noms corrects (_x)
            if 'Club_x' not in arbitres_avec_dispo.columns or 'Nombre  de matchs à arbitrer_x' not in arbitres_avec_dispo.columns:
                st.error("Erreur critique : Les colonnes Club_x ou Nombre  de matchs à arbitrer_x sont manquantes après jointure")
                st.write("Colonnes disponibles dans arbitres_avec_dispo:", arbitres_avec_dispo.columns.tolist())
                st.stop()
            
            # Renommage des colonnes avant création du pivot
            arbitres_avec_dispo = arbitres_avec_dispo.rename(columns={
                'Club_x': 'Club',
                'Nombre  de matchs à arbitrer_x': 'Nbr matchs\nà arbitrer'
            })
            
            grille_dispo = arbitres_avec_dispo.pivot_table(
                index=[COLUMN_MAPPING['arbitres_nom'], COLUMN_MAPPING['arbitres_prenom'], 
                      COLUMN_MAPPING['arbitres_categorie'], 'Club', 'Nbr matchs\nà arbitrer'],
                columns='DATE_AFFICHAGE',
                values=[COLUMN_MAPPING['dispo_disponibilite'], COLUMN_MAPPING['dispo_designation']],
                aggfunc='first'
            )
            display_grille = grille_dispo[COLUMN_MAPPING['dispo_disponibilite']].fillna('Non renseigné')
            ordered_columns = sorted(display_grille.columns, key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
            st.markdown("""
                <style>
                    .stDataFrame {
                        width: 100%;
                    }
                    .col_heading.level0.col4 {
                        text-align: center;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            st.dataframe(
                display_grille[ordered_columns].style.apply(
                    highlight_designated_cells, 
                    grille_dispo=grille_dispo, 
                    column_mapping=COLUMN_MAPPING, 
                    axis=None
                ),
                height=600,
                width=None  # None permet l'ajustement automatique à la largeur disponible
            )
        else:
            st.info("Aucune disponibilité trouvée pour les filtres sélectionnés.")
    else:
        st.warning("Impossible de charger les données de disponibilité.")
else:
    st.warning("Impossible de charger les données des arbitres.")
