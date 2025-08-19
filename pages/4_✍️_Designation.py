import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# Importations centralisées
import config
from utils import (
    load_data,
    get_gspread_client,
    enregistrer_designation,
    load_designations_from_sheets,
    get_arbitre_status_for_date,
    get_department_from_club_name_or_code,
    extract_club_code_from_team_string,
)

# --- Initialisation & Chargement ---
st.title("✍️ Outil de Désignation Interactif")

if 'selected_match' not in st.session_state: st.session_state.selected_match = None
if 'previous_competition' not in st.session_state: st.session_state.previous_competition = None

gc = get_gspread_client()
categories_df = config.load_static_categories()
competitions_df = config.load_static_competitions()
rencontres_df = load_data(config.RENCONTRES_URL)
# Chargement via API Google Sheets directement
designations_df = load_designations_from_sheets(gc, config.DESIGNATIONS_URL)
if designations_df.empty:
    # Fallback sur l'ancienne méthode
    designations_df = load_data(config.DESIGNATIONS_URL)
rencontres_ffr_df = load_data(config.RENCONTRES_FFR_URL)
dispo_df = load_data(config.DISPO_URL)
arbitres_df = load_data(config.ARBITRES_URL)
club_df = load_data(config.CLUB_URL)

# --- Pré-traitement et Fusion des Données de Désignation ---
for df in [rencontres_df, rencontres_ffr_df, designations_df]:
    if "NUMERO RENCONTRE" in df.columns:
        df.rename(columns={"NUMERO RENCONTRE": "RENCONTRE NUMERO"}, inplace=True)
    if "RENCONTRE NUMERO" in df.columns:
        df["RENCONTRE NUMERO"] = df["RENCONTRE NUMERO"].astype(str)


ffr_cols = {'RENCONTRE NUMERO', 'FONCTION ARBITRE', 'NOM', 'PRENOM', 'DPT DE RESIDENCE'}
manual_cols = {'RENCONTRE NUMERO', 'FONCTION ARBITRE', 'NOM', 'PRENOM', 'DPT DE RESIDENCE'}

# Harmonisation des noms de colonnes dans rencontres_ffr_df
rencontres_ffr_df.rename(columns={
    "NUMERO RENCONTRE": "RENCONTRE NUMERO",
    "Nom": "NOM"
}, inplace=True)

if ffr_cols.issubset(rencontres_ffr_df.columns) and manual_cols.issubset(designations_df.columns):
    designations_combinees_df = pd.concat([
        rencontres_ffr_df[list(ffr_cols)],
        designations_df[list(manual_cols)]
    ], ignore_index=True)
else:
    designations_combinees_df = pd.DataFrame(columns=list(ffr_cols))

if 'rencontres_date_dt' not in rencontres_df.columns: rencontres_df['rencontres_date_dt'] = pd.to_datetime(rencontres_df["DATE EFFECTIVE"], errors='coerce', dayfirst=True)
if 'DATE_dt' not in dispo_df.columns: dispo_df['DATE_dt'] = pd.to_datetime(dispo_df['DATE'], errors='coerce', dayfirst=True)

if 'RENCONTRE NUMERO' in designations_combinees_df.columns and 'FONCTION ARBITRE' in designations_combinees_df.columns:
    roles_par_match = designations_combinees_df.groupby('RENCONTRE NUMERO')['FONCTION ARBITRE'].apply(list).reset_index()
    roles_par_match.rename(columns={'FONCTION ARBITRE': 'ROLES'}, inplace=True)
    rencontres_df = pd.merge(rencontres_df, roles_par_match, on='RENCONTRE NUMERO', how='left')
    rencontres_df['ROLES'] = rencontres_df['ROLES'].apply(lambda x: x if isinstance(x, list) else [])
else:
    rencontres_df['ROLES'] = [[] for _ in range(len(rencontres_df))]

def select_match(match_numero): st.session_state.selected_match = match_numero

# --- Interface ---
left_col, right_col = st.columns([2, 3])

with left_col:
    st.header("🗓️ Liste des Rencontres")
    competition_options = ["Toutes"] + sorted(competitions_df['NOM'].unique().tolist())
    competition_nom = st.selectbox("Filtrer par compétition", options=competition_options)
    
    if st.session_state.previous_competition != competition_nom:
        st.session_state.selected_match = None
        st.session_state.previous_competition = competition_nom

    if competition_nom == "Toutes":
        rencontres_filtrees_df = rencontres_df.copy()
        rencontres_filtrees_df = rencontres_filtrees_df.sort_values(by=['COMPETITION NOM', 'rencontres_date_dt'])
    else:
        rencontres_filtrees_df = rencontres_df[rencontres_df["COMPETITION NOM"] == competition_nom].copy()
        rencontres_filtrees_df = rencontres_filtrees_df.sort_values(by='rencontres_date_dt')
    
    unique_matches_df = rencontres_filtrees_df.drop_duplicates(subset=['RENCONTRE NUMERO'])

    if unique_matches_df.empty:
        st.warning("Aucune rencontre trouvée.")
    else:
        for index, rencontre in unique_matches_df.iterrows():
            with st.container(border=True):
                if competition_nom == "Toutes":
                    st.caption(rencontre['COMPETITION NOM'])
                st.subheader(f"{rencontre['LOCAUX']} vs {rencontre['VISITEURS']}")
                st.caption(f"{rencontre['rencontres_date_dt'].strftime('%d/%m/%Y')}")
                
                roles = rencontre.get('ROLES', [])
                if roles:
                    icon_str = " ".join([config.ROLE_ICONS.get(role, config.ROLE_ICONS['default']) for role in roles])
                    st.markdown(f"**Rôles pourvus :** {icon_str}")
                
                st.button("Sélectionner", key=f"select_{rencontre['RENCONTRE NUMERO']}", on_click=select_match, args=(rencontre['RENCONTRE NUMERO'],))

with right_col:
    if 'selected_match' not in st.session_state or st.session_state.selected_match is None:
        st.info("⬅️ Sélectionnez un match dans la liste de gauche pour commencer.")
    else:
        selected_match_numero = st.session_state.selected_match
        rencontre_details = rencontres_df[rencontres_df['RENCONTRE NUMERO'] == selected_match_numero].iloc[0]
        date_rencontre = rencontre_details['rencontres_date_dt']

        st.header(f"🎯 {rencontre_details['LOCAUX']} vs {rencontre_details['VISITEURS']}")
        
        col_refresh, _ = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 Rafraîchir les désignations", help="Met à jour uniquement les désignations manuelles"):
                st.cache_data.clear()
                st.rerun()
        
        st.subheader("Désignations Actuelles")
        roles_actuels = rencontre_details.get('ROLES', [])
        if roles_actuels:
            designations_actuelles_df = designations_combinees_df[designations_combinees_df['RENCONTRE NUMERO'].astype(str) == str(selected_match_numero)]
            cols_to_show = ["NOM", "PRENOM", "DPT DE RESIDENCE", "FONCTION ARBITRE"]
            
            for idx, row in designations_actuelles_df.iterrows():
                col1, col2 = st.columns([4, 1])
                with col1:
                    dpt = str(row['DPT DE RESIDENCE']).zfill(2)[:2]
                    st.write(f"{row['NOM']} {row['PRENOM']} ({dpt}) - {row['FONCTION ARBITRE']}")
                with col2:
                    is_manual = any(
                        (str(d_row.get('RENCONTRE NUMERO', '')) == str(selected_match_numero) and
                         str(d_row.get('NOM', '')) == str(row['NOM']) and
                         str(d_row.get('PRENOM', '')) == str(row['PRENOM']) and
                         str(d_row.get('FONCTION ARBITRE', '')) == str(row['FONCTION ARBITRE']))
                        for _, d_row in designations_df.iterrows()
                    )
                    if is_manual and st.button("Supprimer", key=f"delete_{idx}"):
                        if st.session_state.get(f"confirm_delete_{idx}", False):
                            try:
                                if gc:
                                    spreadsheet = gc.open_by_url(config.DESIGNATIONS_URL)
                                    worksheet = spreadsheet.get_worksheet(0)
                                    records = worksheet.get_all_records()
                                    for i, record in enumerate(records, start=2):
                                        if (str(record.get('RENCONTRE NUMERO', '')) == str(selected_match_numero) and \
                                           str(record.get('NOM', '')) == str(row['NOM']) and \
                                           str(record.get('PRENOM', '')) == str(row['PRENOM']) and \
                                           str(record.get('FONCTION ARBITRE', '')) == str(row['FONCTION ARBITRE'])):
                                            worksheet.delete_rows(i)
                                            st.success("Désignation supprimée !")
                                            st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de la suppression : {e}")
                        else:
                            st.session_state[f"confirm_delete_{idx}"] = True
                            st.warning("Confirmez la suppression en cliquant à nouveau")
        else:
            st.info("Aucune désignation existante pour ce match.")
        st.divider()

        st.subheader("Options de Filtrage")
        filter_mode = st.radio("Choisir le mode de filtrage :", ("Filtres stricts (recommandé)", "Aucun filtre (sauf appartenance club)"), horizontal=True)
        st.divider()

        st.subheader("Chercher un Arbitre")

        locaux_code = extract_club_code_from_team_string(rencontre_details["LOCAUX"])
        visiteurs_code = extract_club_code_from_team_string(rencontre_details["VISITEURS"])
        arbitres_filtres = arbitres_df[~arbitres_df['Code Club'].astype(str).isin([str(locaux_code), str(visiteurs_code)])]

        arbitres_filtres = pd.merge(arbitres_filtres, categories_df, left_on='Catégorie', right_on='CATEGORIE', how='left')

        if filter_mode == "Filtres stricts (recommandé)":
            competition_info = competitions_df[competitions_df['NOM'] == rencontre_details["COMPETITION NOM"]].iloc[0]
            niveau_min, niveau_max = (competition_info['NIVEAU MIN'], competition_info['NIVEAU MAX'])
            if niveau_min > niveau_max: niveau_min, niveau_max = niveau_max, niveau_min
            arbitres_filtres = arbitres_filtres[arbitres_filtres['Niveau'].between(niveau_min, niveau_max)]

            dpt_locaux = get_department_from_club_name_or_code(rencontre_details["LOCAUX"], club_df, config.COLUMN_MAPPING)
            if dpt_locaux and dpt_locaux != "Non trouvé":
                arbitres_filtres = arbitres_filtres[arbitres_filtres['Département de Résidence'].astype(str) != str(dpt_locaux)]

        arbitres_filtres = arbitres_filtres.sort_values(by='Niveau', ascending=True)

        if arbitres_filtres.empty:
            st.warning("Aucun arbitre trouvé avec les filtres actuels.")
        else:
            st.write(f"{len(arbitres_filtres)} arbitres trouvés")
            
            required_columns = ['Nom', 'Prénom', 'Numéro Affiliation', 'Catégorie', 'Niveau']
            if not all(col in arbitres_filtres.columns for col in required_columns):
                st.error(f"Colonnes manquantes dans arbitres_filtres. Requises: {required_columns}")
                st.write("Colonnes disponibles:", arbitres_filtres.columns.tolist())
                st.stop()
            
            roles_disponibles = [role for role in config.ALL_ROLES if role not in roles_actuels]
            
            for index, arbitre in arbitres_filtres.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        est_deja_designe = False
                        if not designations_df.empty and 'NUMERO LICENCE' in designations_df.columns:
                            est_deja_designe = not designations_df[designations_df['NUMERO LICENCE'].astype(str) == str(arbitre['Numéro Affiliation'])].empty
                        
                        jt_icon = " ⚑" if str(arbitre.get('JT', '')).strip().upper() == 'OUI' else ""
                        nom_affichage = f"**{arbitre['Nom']} {arbitre['Prénom']}{jt_icon}**"
                        if est_deja_designe:
                            st.success("✏️ Désignation MANUELLE", icon="✏️")
                            if jt_icon:
                                st.caption("Arbitre JT (Juge de Touche)")
                            designation_info = designations_df[
                                (designations_df['NUMERO LICENCE'].astype(str) == str(arbitre['Numéro Affiliation']))
                            ].iloc[0]
                            rencontre_date_designe = pd.to_datetime(designation_info['DATE'], dayfirst=True, errors='coerce')
                            if not pd.isna(rencontre_date_designe):
                                st.caption(f"📅 Désigné le {rencontre_date_designe.strftime('%d/%m/%Y')} sur {designation_info.get('LOCAUX', '?')} vs {designation_info.get('VISITEURS', '?')}")
                        
                        st.write(nom_affichage)
                        st.caption(f"Catégorie : {arbitre['Catégorie']} (Niveau {arbitre['Niveau']}) | Département: {arbitre['Département de Résidence']}")
                    
                    with col2:
                        try:
                            status_text, is_designable = get_arbitre_status_for_date(
                                arbitre['Numéro Affiliation'], 
                                date_rencontre, 
                                dispo_df
                            )
                            
                            if is_designable:
                                st.success(status_text, icon="✅")
                            else:
                                st.warning(status_text, icon="⚠️")
                            
                            if is_designable and roles_disponibles:
                                role_key = f"role_{selected_match_numero}_{arbitre['Numéro Affiliation']}"
                                selected_role = st.selectbox(
                                    "Choisir un rôle", 
                                    options=roles_disponibles, 
                                    key=role_key, 
                                    label_visibility="collapsed"
                                )
                                
                                button_key = f"designate_{selected_match_numero}_{arbitre['Numéro Affiliation']}"
                                if st.button("Valider", key=button_key, use_container_width=True):
                                    if gc:
                                        with st.spinner("Enregistrement..."):
                                            success = enregistrer_designation(gc, config.DESIGNATIONS_URL, rencontre_details, arbitre, dpt_locaux, selected_role)
                                            if success:
                                                st.toast("Désignation enregistrée !", icon="✅")
                                                st.rerun()
                                            else:
                                                st.error("Échec de l'enregistrement.")
                                    else:
                                        st.error("Client Google Sheets non authentifié")
                            elif not roles_disponibles:
                                st.info("Complet")
                        except Exception as e:
                            st.error(f"Erreur lors de l'affichage du statut: {str(e)}")