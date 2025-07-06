import streamlit as st
import pandas as pd
import re
from utils import (
    extract_club_name_from_team_string, 
    extract_club_code_from_team_string,
    get_department_from_club_name_or_code, 
    get_cp_from_club_name_or_code, 
    highlight_designated_cells
)

def app(data_frames, column_mapping):
    st.title("Outil d'aide à la désignation d'arbitres de rugby")

    # Récupération des données depuis le dictionnaire passé en argument
    categories_df = data_frames["categories_df"]
    competitions_df = data_frames["competitions_df"]
    rencontres_df = data_frames["rencontres_df"]
    dispo_df = data_frames["dispo_df"]
    arbitres_df = data_frames["arbitres_df"]
    club_df = data_frames["club_df"]

    # Interface utilisateur
    st.header("Sélection de la rencontre")

    # Sélection de la compétition
    competition_nom = st.selectbox("Choisissez une compétition", competitions_df[column_mapping['competitions_nom']].unique())

    # Sélection de la rencontre
    rencontres_df[column_mapping['rencontres_date']] = pd.to_datetime(rencontres_df[column_mapping['rencontres_date']]).dt.strftime('%d/%m/%Y')
    rencontres_filtrees_df = rencontres_df[rencontres_df[column_mapping['rencontres_competition']] == competition_nom]
    
    if not rencontres_filtrees_df.empty:
        rencontres_filtrees_df['display'] = rencontres_filtrees_df.apply(
            lambda x: f"{x[column_mapping['rencontres_date']]} - {x[column_mapping['rencontres_locaux']]} vs {x[column_mapping['rencontres_visiteurs']]}",
            axis=1
        )
        option_selectionnee = st.selectbox(
            "Choisissez une rencontre",
            options=rencontres_filtrees_df['display'],
            index=0
        )

        if option_selectionnee:
            # Extraire les détails de la rencontre sélectionnée
            rencontre_details = rencontres_filtrees_df[rencontres_filtrees_df['display'] == option_selectionnee].iloc[0]
            locaux = rencontre_details[column_mapping['rencontres_locaux']]
            visiteurs = rencontre_details[column_mapping['rencontres_visiteurs']]
            
            date_rencontre = pd.to_datetime(rencontre_details[column_mapping['rencontres_date']], format='%d/%m/%Y')

            st.subheader("Détails de la rencontre")
            st.write(f"**Date :** {date_rencontre.strftime('%d/%m/%Y')}")
            st.write(f"**Équipe à domicile :** {locaux}")
            st.write(f"**Équipe visiteuse :** {visiteurs}")
            st.write(f"**Compétition :** {rencontre_details[column_mapping['rencontres_competition']]}")

            # Récupérer et afficher le CP de l'équipe à domicile
            cp_locaux = get_cp_from_club_name_or_code(locaux, club_df, column_mapping)
            st.write(f"**CP Équipe à domicile :** {cp_locaux}")

            # MODE DEBUG - À SUPPRIMER UNE FOIS QUE ÇA FONCTIONNE
            if st.checkbox("Mode Debug - Afficher les détails clubs", key="debug_details_clubs"):
                st.write("**Analyse des équipes :**")
                
                # Équipe locale
                code_local = extract_club_code_from_team_string(locaux)
                nom_local = extract_club_name_from_team_string(locaux)
                st.write(f"- Équipe locale brute: {locaux}")
                st.write(f"- Code extrait: {code_local}")
                st.write(f"- Nom extrait: {nom_local}")
                
                # Équipe visiteuse
                code_visiteur = extract_club_code_from_team_string(visiteurs)
                nom_visiteur = extract_club_name_from_team_string(visiteurs)
                st.write(f"- Équipe visiteuse brute: {visiteurs}")
                st.write(f"- Code extrait: {code_visiteur}")
                st.write(f"- Nom extrait: {nom_visiteur}")
                
                # Données club
                st.write("**Échantillon fichier clubs :**")
                st.dataframe(club_df.head())
                st.write(f"**Colonnes disponibles :** {club_df.columns.tolist()}")

            # Logique de filtrage des arbitres
            st.header("Disponibilité des arbitres qualifiés pour le week-end")

            # 1. Disponibilité
            dispo_df['DATE EFFECTIVE'] = pd.to_datetime(dispo_df[column_mapping['dispo_date']], errors='coerce')
            
            # Nettoyage de la colonne DISPONIBILITE pour une comparaison robuste
            dispo_df[column_mapping['dispo_disponibilite']] = dispo_df[column_mapping['dispo_disponibilite']].astype(str).str.strip().str.upper()

            # 2. Niveau requis
            competition_info = competitions_df[competitions_df[column_mapping['competitions_nom']] == competition_nom].iloc[0]
            niveau_min = competition_info[column_mapping['competitions_niveau_min']]
            niveau_max = competition_info[column_mapping['competitions_niveau_max']]

            if niveau_min > niveau_max:
                niveau_min, niveau_max = niveau_max, niveau_min

            arbitres_df_avec_niveau = pd.merge(
                arbitres_df,
                categories_df,
                left_on=column_mapping['arbitres_categorie'],
                right_on=column_mapping['categories_nom'],
                how='left'
            )
            
            arbitres_qualifies_niveau = arbitres_df_avec_niveau[
                arbitres_df_avec_niveau[column_mapping['categories_niveau']].between(niveau_min, niveau_max)
            ]

            # 3. Application de la neutralité - NOUVELLE VERSION
            dpt_locaux = get_department_from_club_name_or_code(locaux, club_df, column_mapping)
            dpt_visiteurs = get_department_from_club_name_or_code(visiteurs, club_df, column_mapping)

            # Debug - à supprimer une fois que ça fonctionne
            if st.checkbox("Mode Debug - Neutralité", key="debug_neutralite"):
                st.write(f"**Département équipe locale :** {dpt_locaux}")
                st.write(f"**Département équipe visiteuse :** {dpt_visiteurs}")

            dpts_to_exclude = []
            if dpt_locaux and dpt_locaux != "Non trouvé":
                dpts_to_exclude.append(dpt_locaux)
            if dpt_visiteurs and dpt_visiteurs != "Non trouvé":
                dpts_to_exclude.append(dpt_visiteurs)

            if st.checkbox("Mode Debug - Filtrage", key="debug_filtrage_1"):
                st.write(f"**Départements à exclure :** {dpts_to_exclude}")
                st.write(f"**Arbitres avant filtrage :** {len(arbitres_qualifies_niveau)}")

            if dpts_to_exclude:
                # S'assurer que la colonne département de résidence est traitée comme string
                arbitres_qualifies_niveau[column_mapping['arbitres_dpt_residence']] = arbitres_qualifies_niveau[column_mapping['arbitres_dpt_residence']].astype(str)
                
                # Filtrer les arbitres
                arbitres_qualifies_niveau = arbitres_qualifies_niveau[
                    ~arbitres_qualifies_niveau[column_mapping['arbitres_dpt_residence']].isin(dpts_to_exclude)
                ]
                
                if st.checkbox("Mode Debug - Filtrage", key="debug_filtrage_2"):
                    st.write(f"**Arbitres après filtrage :** {len(arbitres_qualifies_niveau)}")

            # 4. Déterminer les dates du week-end (vendredi, samedi, dimanche)
            jour_semaine = date_rencontre.dayofweek  # Lundi=0, Dimanche=6
            vendredi = date_rencontre - pd.Timedelta(days=jour_semaine - 4)
            samedi = vendredi + pd.Timedelta(days=1)
            dimanche = vendredi + pd.Timedelta(days=2)
            weekend_dates = [vendredi, samedi, dimanche]
            
            # 5. Préparer les données de disponibilité pour ce week-end
            dispo_cols_needed = [
                column_mapping['dispo_licence'],
                'DATE EFFECTIVE',
                column_mapping['dispo_disponibilite'],
                column_mapping['dispo_designation']
            ]
            dispo_weekend_df = dispo_df[dispo_df['DATE EFFECTIVE'].isin(weekend_dates)][dispo_cols_needed].copy()
            
            # 6. Fusionner les arbitres qualifiés avec leurs disponibilités du week-end
            arbitres_avec_dispo = pd.merge(
                arbitres_qualifies_niveau,
                dispo_weekend_df,
                left_on=column_mapping['arbitres_affiliation'],
                right_on=column_mapping['dispo_licence'],
                how='left'
            )

            # 7. Créer le tableau croisé dynamique (la grille)
            if not arbitres_avec_dispo.empty:
                # Formatter la date pour un affichage propre dans les colonnes
                arbitres_avec_dispo['DATE_AFFICHAGE'] = arbitres_avec_dispo['DATE EFFECTIVE'].dt.strftime('%d/%m/%Y')

                # Créer la grille avec désignation pour le style
                grille_dispo = arbitres_avec_dispo.pivot_table(
                    index=[column_mapping['arbitres_nom'], column_mapping['arbitres_prenom'], column_mapping['arbitres_dpt_residence'], column_mapping['arbitres_categorie']],
                    columns='DATE_AFFICHAGE',
                    values=[column_mapping['dispo_disponibilite'], column_mapping['dispo_designation']],
                    aggfunc='first'
                )

                # Grille d'affichage (uniquement la disponibilité)
                display_grille = grille_dispo[column_mapping['dispo_disponibilite']].fillna('Non renseigné')

                # Renommer la colonne 'Département de Résidence' en 'Dpt Résidence' pour l'affichage
                display_grille = display_grille.rename_axis(index={
                    column_mapping['arbitres_dpt_residence']: 'Dpt Résidence'
                })

                # Réorganiser les colonnes pour qu'elles soient dans l'ordre chronologique
                ordered_columns = [d.strftime('%d/%m/%Y') for d in weekend_dates]
                final_columns = [col for col in ordered_columns if col in display_grille.columns]
                
                if not final_columns:
                    st.info("Aucune information de disponibilité n'a été renseignée pour les arbitres qualifiés durant ce week-end.")
                    st.write("Voici la liste des arbitres qualifiés pour la compétition :")
                    st.dataframe(arbitres_qualifies_niveau[[
                        column_mapping['arbitres_nom'], 
                        column_mapping['arbitres_prenom'], 
                        column_mapping['arbitres_categorie']
                    ]])
                else:
                    # Appliquer le style et afficher
                    st.dataframe(display_grille[final_columns].style.apply(
                        highlight_designated_cells, 
                        grille_dispo=grille_dispo, 
                        column_mapping=column_mapping, 
                        axis=None
                    ))
            else:
                st.info("Aucun arbitre qualifié n'a été trouvé pour cette compétition.")
    else:
        st.warning("Aucune rencontre trouvée pour cette compétition.")