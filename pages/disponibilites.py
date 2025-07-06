import streamlit as st
import pandas as pd
from datetime import datetime
from utils import highlight_designated_cells

def app(data_frames, column_mapping):
    st.title("Disponibilités des Arbitres")

    # --- Récupération des données ---
    arbitres_df = data_frames["arbitres_df"].copy()
    dispo_df = data_frames["dispo_df"].copy()
    categories_df = data_frames["categories_df"].copy()

    # --- Filtres ---
    st.header("Filtres")

    # Filtre par catégorie
    all_categories = ["Toutes"] + list(categories_df[column_mapping['categories_nom']].unique())
    selected_categories = st.multiselect(
        "Filtrer par catégorie d'arbitre",
        options=all_categories,
        default=["Toutes"]
    )

    # --- Logique de filtrage ---
    # 1. Filtrer les arbitres par catégorie
    if "Toutes" not in selected_categories:
        arbitres_filtres = arbitres_df[arbitres_df[column_mapping['arbitres_categorie']].isin(selected_categories)]
    else:
        arbitres_filtres = arbitres_df

    # 2. Préparer les disponibilités
    dispo_df['DATE EFFECTIVE'] = pd.to_datetime(dispo_df[column_mapping['dispo_date']], errors='coerce')

    # Sélectionner uniquement les colonnes nécessaires de dispo_df pour éviter les conflits de noms
    dispo_a_merger = dispo_df[[
        column_mapping['dispo_licence'],
        column_mapping['dispo_disponibilite'],
        column_mapping['dispo_designation'],
        'DATE EFFECTIVE'
    ]]

    # 3. Fusionner les arbitres filtrés avec leurs disponibilités
    arbitres_avec_dispo = pd.merge(
        arbitres_filtres,
        dispo_a_merger,
        left_on=column_mapping['arbitres_affiliation'],
        right_on=column_mapping['dispo_licence'],
        how='inner' # inner pour ne garder que les arbitres avec des dispos
    )

    # --- Affichage de la grille ---
    st.header("Grille des Disponibilités")

    if not arbitres_avec_dispo.empty:
        # Formatter la date pour l'affichage
        arbitres_avec_dispo['DATE_AFFICHAGE'] = arbitres_avec_dispo['DATE EFFECTIVE'].dt.strftime('%d/%m/%Y')

        # Créer la table pivot
        grille_dispo = arbitres_avec_dispo.pivot_table(
            index=[column_mapping['arbitres_nom'], column_mapping['arbitres_prenom'], column_mapping['arbitres_categorie']],
            columns='DATE_AFFICHAGE',
            values=[column_mapping['dispo_disponibilite'], column_mapping['dispo_designation']],
            aggfunc='first'
        )

        # Grille pour l'affichage (uniquement la disponibilité)
        display_grille = grille_dispo[column_mapping['dispo_disponibilite']].fillna('Non renseigné')

        

        # Trier les colonnes par date
        ordered_columns = sorted(display_grille.columns, key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
        
        st.dataframe(display_grille[ordered_columns].style.apply(highlight_designated_cells, grille_dispo=grille_dispo, column_mapping=column_mapping, axis=None))
    else:
        st.info("Aucune disponibilité trouvée pour les filtres sélectionnés.")
