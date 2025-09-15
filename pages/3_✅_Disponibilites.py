import streamlit as st
import pandas as pd
from datetime import datetime

# Importations centralisées
from utils import highlight_designated_cells, load_data
import config

# --- Chargement des données ---
arbitres_df = load_data(config.ARBITRES_URL)
dispo_df = load_data(config.DISPO_URL)

# --- Application ---
st.title("✅ Disponibilités des Arbitres")
st.markdown("RS_OVALE2-022 - Vue consolidée de toutes les disponibilités des arbitres.")

if st.button("🔄 Vider le cache et recharger les données"):
    st.cache_data.clear()
    st.rerun()

st.header("Filtres")

if not arbitres_df.empty:
    all_categories = ["Toutes"] + list(arbitres_df[config.COLUMN_MAPPING['arbitres_categorie']].unique())
    selected_categories = st.multiselect(
        "Filtrer par catégorie d'arbitre",
        options=all_categories,
        default=["Toutes"]
    )

    if "Toutes" not in selected_categories:
        arbitres_filtres = arbitres_df[arbitres_df[config.COLUMN_MAPPING['arbitres_categorie']].isin(selected_categories)]
    else:
        arbitres_filtres = arbitres_df

    if not dispo_df.empty:
        dispo_df['DATE EFFECTIVE'] = pd.to_datetime(dispo_df[config.COLUMN_MAPPING['dispo_date']], errors='coerce')
        dispo_a_merger = dispo_df[[
            config.COLUMN_MAPPING['dispo_licence'],
            config.COLUMN_MAPPING['dispo_disponibilite'],
            config.COLUMN_MAPPING['dispo_designation'],
            'DATE EFFECTIVE'
        ]]
        arbitres_avec_dispo = pd.merge(
            arbitres_filtres,
            dispo_a_merger,
            left_on=config.COLUMN_MAPPING['arbitres_affiliation'],
            right_on=config.COLUMN_MAPPING['dispo_licence'],
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
                arbitres_df[[config.COLUMN_MAPPING['arbitres_affiliation'], 'Club', 'Nombre  de matchs à arbitrer']],
                on=config.COLUMN_MAPPING['arbitres_affiliation'],
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
                index=[config.COLUMN_MAPPING['arbitres_nom'], config.COLUMN_MAPPING['arbitres_prenom'], 
                      config.COLUMN_MAPPING['arbitres_categorie'], 'Club', 'Nbr matchs\nà arbitrer'],
                columns='DATE_AFFICHAGE',
                values=[config.COLUMN_MAPPING['dispo_disponibilite'], config.COLUMN_MAPPING['dispo_designation']],
                aggfunc='first'
            )
            # Remplacer "OUI" et "NON" par des chaînes vides, garder "Non renseigné" pour les valeurs manquantes
            display_grille = grille_dispo[config.COLUMN_MAPPING['dispo_disponibilite']].fillna('Non renseigné')
            display_grille = display_grille.replace({'OUI': '', 'NON': ''})
            ordered_columns = sorted(display_grille.columns, key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
            st.markdown("""                <style>
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
                    column_mapping=config.COLUMN_MAPPING, 
                    axis=None
                ),
                height=600
                # width=None a été retiré car il cause une erreur dans certaines versions de Streamlit
            )
        else:
            st.info("Aucune disponibilité trouvée pour les filtres sélectionnés.")
    else:
        st.warning("Impossible de charger les données de disponibilité.")
else:
    st.warning("Impossible de charger les données des arbitres.")
