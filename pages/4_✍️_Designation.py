import streamlit as st
import pandas as pd

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

# --- Fonctions d'affichage de l'UI ---

def display_current_designations(rencontre_details, designations_combinees_df, designations_df, gc):
    st.subheader("Désignations Actuelles")
    selected_match_numero = rencontre_details['RENCONTRE NUMERO']
    roles_actuels = rencontre_details.get('ROLES', [])
    
    if not roles_actuels:
        st.info("Aucune désignation existante pour ce match.")
        return

    designations_actuelles_df = designations_combinees_df[designations_combinees_df['RENCONTRE NUMERO'].astype(str) == str(selected_match_numero)]
    
    for idx, row in designations_actuelles_df.iterrows():
        col1, col2 = st.columns([4, 1])
        with col1:
            dpt = str(row.get('DPT DE RESIDENCE', '')).zfill(2)[:2]
            st.write(f"- {row.get('NOM', '')} {row.get('PRENOM', '')} ({dpt}) - *{row.get('FONCTION ARBITRE', '')}*")
        with col2:
            is_manual = any(
                (str(d_row.get('RENCONTRE NUMERO', '')) == str(selected_match_numero) and
                 str(d_row.get('NOM', '')) == str(row['NOM']) and
                 str(d_row.get('PRENOM', '')) == str(row['PRENOM']) and
                 str(d_row.get('FONCTION ARBITRE', '')) == str(row['FONCTION ARBITRE']))
                for _, d_row in designations_df.iterrows()
            )
            
            button_key = f"delete_{idx}_{selected_match_numero}"
            confirm_key = f"confirm_{button_key}"

            if is_manual:
                if st.session_state.get(confirm_key, False):
                    if st.button("Vraiment Supprimer ?", key=button_key, type="primary"):
                        try:
                            if gc:
                                spreadsheet = gc.open_by_url(config.DESIGNATIONS_URL)
                                worksheet = spreadsheet.get_worksheet(0)
                                records = worksheet.get_all_records()
                                row_to_delete = -1
                                for i, record in enumerate(records):
                                    if (str(record.get('RENCONTRE NUMERO')) == str(selected_match_numero) and
                                        record.get('NOM') == row['NOM'] and
                                        record.get('PRENOM') == row['PRENOM'] and
                                        record.get('FONCTION ARBITRE') == row['FONCTION ARBITRE']):
                                        row_to_delete = i + 2
                                        break
                                
                                if row_to_delete != -1:
                                    worksheet.delete_rows(row_to_delete)
                                    st.toast("Désignation supprimée !", icon="✅")
                                    st.cache_data.clear()
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                                else:
                                    st.error("Impossible de trouver la désignation à supprimer.")
                        except Exception as e:
                            st.error(f"Erreur lors de la suppression : {e}")
                else:
                    if st.button("Supprimer", key=button_key):
                        st.session_state[confirm_key] = True
                        st.rerun()

def display_referee_finder(rencontre_details, arbitres_df, club_df, categories_df, competitions_df, dispo_df, designations_df, gc):
    st.subheader("Options de Filtrage")
    filter_mode = st.radio("Mode de filtrage :", ("Filtres stricts (recommandé)", "Aucun filtre (sauf appartenance club)"), horizontal=True, key=f"filter_{rencontre_details['RENCONTRE NUMERO']}")
    st.divider()
    st.subheader("Chercher un Arbitre")
    
    # --- AJOUT DU CHAMP DE RECHERCHE ---
    search_query = st.text_input("Filtrer par nom ou prénom", key=f"search_{rencontre_details['RENCONTRE NUMERO']}")

    # Logique de filtrage
    locaux_code = extract_club_code_from_team_string(rencontre_details["LOCAUX"])
    visiteurs_code = extract_club_code_from_team_string(rencontre_details["VISITEURS"])
    arbitres_filtres = arbitres_df[~arbitres_df[config.COLUMN_MAPPING['arbitres_club_code']].astype(str).isin([str(locaux_code), str(visiteurs_code)])]
    arbitres_filtres = pd.merge(arbitres_filtres, categories_df, left_on=config.COLUMN_MAPPING['arbitres_categorie'], right_on=config.COLUMN_MAPPING['categories_nom'], how='left')
    dpt_locaux = get_department_from_club_name_or_code(rencontre_details["LOCAUX"], club_df, config.COLUMN_MAPPING)
    if filter_mode == "Filtres stricts (recommandé)":
        comp_info = competitions_df[competitions_df[config.COLUMN_MAPPING['competitions_nom']] == rencontre_details[config.COLUMN_MAPPING['rencontres_competition']]]
        if not comp_info.empty:
            comp_info = comp_info.iloc[0]
            niveau_min, niveau_max = (comp_info['NIVEAU MIN'], comp_info['NIVEAU MAX'])
            if niveau_min > niveau_max: niveau_min, niveau_max = niveau_max, niveau_min
            arbitres_filtres = arbitres_filtres[arbitres_filtres[config.COLUMN_MAPPING['categories_niveau']].between(niveau_min, niveau_max)]
        if dpt_locaux and dpt_locaux != "Non trouvé":
            arbitres_filtres = arbitres_filtres[arbitres_filtres[config.COLUMN_MAPPING['arbitres_dpt_residence']].astype(str) != str(dpt_locaux)]
    
    # --- APPLICATION DU FILTRE DE RECHERCHE ---
    if search_query:
        arbitres_filtres = arbitres_filtres[
            arbitres_filtres[config.COLUMN_MAPPING['arbitres_nom']].str.contains(search_query, case=False, na=False) |
            arbitres_filtres[config.COLUMN_MAPPING['arbitres_prenom']].str.contains(search_query, case=False, na=False)
        ]

    arbitres_filtres = arbitres_filtres.sort_values(by=config.COLUMN_MAPPING['categories_niveau'], ascending=True)
    if arbitres_filtres.empty:
        st.warning("Aucun arbitre trouvé avec les filtres actuels.")
        return
    st.write(f"{len(arbitres_filtres)} arbitres trouvés")
    roles_actuels = rencontre_details.get('ROLES', [])
    roles_disponibles = [role for role in config.ALL_ROLES if role not in roles_actuels]
    for _, arbitre in arbitres_filtres.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                est_deja_designe = False
                if not designations_df.empty and 'NUMERO LICENCE' in designations_df.columns:
                    deja_designe_df = designations_df[designations_df['NUMERO LICENCE'].astype(str) == str(arbitre[config.COLUMN_MAPPING['arbitres_affiliation']])]
                    est_deja_designe = not deja_designe_df.empty
                st.write(f"**{arbitre[config.COLUMN_MAPPING['arbitres_nom']]} {arbitre[config.COLUMN_MAPPING['arbitres_prenom']]}**")
                st.caption(f"Cat: {arbitre[config.COLUMN_MAPPING['arbitres_categorie']]} (Niv {arbitre[config.COLUMN_MAPPING['categories_niveau']]}) | Dpt: {arbitre[config.COLUMN_MAPPING['arbitres_dpt_residence']]}")
                if est_deja_designe and 'DATE' in deja_designe_df.columns:
                    st.info(f"✏️ Déjà une désignation manuelle le {pd.to_datetime(deja_designe_df.iloc[0]['DATE'], dayfirst=True, errors='coerce').strftime('%d/%m')}")
            with col2:
                status_text, is_designable = get_arbitre_status_for_date(arbitre[config.COLUMN_MAPPING['arbitres_affiliation']], rencontre_details['rencontres_date_dt'], dispo_df)
                if is_designable:
                    st.success(status_text, icon="✅")
                    if roles_disponibles:
                        key_suffix = f"{rencontre_details['RENCONTRE NUMERO']}_{arbitre[config.COLUMN_MAPPING['arbitres_affiliation']]}"
                        selected_role = st.selectbox("Rôle", options=roles_disponibles, key=f"role_{key_suffix}", label_visibility="collapsed")
                        if st.button("Valider", key=f"designate_{key_suffix}", use_container_width=True):
                            if gc:
                                success = enregistrer_designation(gc, config.DESIGNATIONS_URL, rencontre_details, arbitre, dpt_locaux, selected_role)
                                if success:
                                    st.toast("Désignation enregistrée !", icon="✅")
                                    st.cache_data.clear()
                                    st.rerun()
                    else:
                        st.info("Complet")
                else:
                    st.warning(status_text, icon="⚠️")

# --- Initialisation & Chargement ---
st.title("✍️ Outil de Désignation Interactif")
if 'selected_match' not in st.session_state: st.session_state.selected_match = None
if 'previous_competition' not in st.session_state: st.session_state.previous_competition = None
gc = get_gspread_client()
categories_df = config.load_static_categories()
competitions_df = config.load_static_competitions()
rencontres_df = load_data(config.RENCONTRES_URL)
designations_df = load_designations_from_sheets(gc, config.DESIGNATIONS_URL) if gc else pd.DataFrame()
if designations_df.empty:
    designations_df = load_data(config.DESIGNATIONS_URL)
rencontres_ffr_df = load_data(config.RENCONTRES_FFR_URL)
dispo_df = load_data(config.DISPO_URL)
arbitres_df = load_data(config.ARBITRES_URL)
club_df = load_data(config.CLUB_URL)

# --- Pré-traitement des données ---
for df in [rencontres_df, rencontres_ffr_df, designations_df]:
    if "NUMERO RENCONTRE" in df.columns:
        df.rename(columns={"NUMERO RENCONTRE": "RENCONTRE NUMERO"}, inplace=True)
    if "RENCONTRE NUMERO" in df.columns:
        df["RENCONTRE NUMERO"] = df["RENCONTRE NUMERO"].astype(str)
ffr_cols = {'RENCONTRE NUMERO', 'FONCTION ARBITRE', 'NOM', 'PRENOM', 'DPT DE RESIDENCE'}
manual_cols = {'RENCONTRE NUMERO', 'FONCTION ARBITRE', 'NOM', 'PRENOM', 'DPT DE RESIDENCE', 'NUMERO LICENCE', 'DATE'}
if 'Nom' in rencontres_ffr_df.columns:
    rencontres_ffr_df.rename(columns={"Nom": "NOM"}, inplace=True)
if ffr_cols.issubset(rencontres_ffr_df.columns) and manual_cols.issubset(designations_df.columns):
    designations_combinees_df = pd.concat([rencontres_ffr_df[list(ffr_cols)], designations_df[list(manual_cols)]], ignore_index=True)
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

# --- Interface Principale ---
left_col, right_col = st.columns([2, 3])
with left_col:
    st.header("🗓️ Liste des Rencontres")
    competition_options = sorted(competitions_df[config.COLUMN_MAPPING['competitions_nom']].unique().tolist())
    selected_competitions = st.multiselect(
        "Filtrer par compétition", 
        options=competition_options, 
        placeholder="Choisissez une ou plusieurs compétitions"
    )

    # La logique de réinitialisation doit maintenant comparer des listes
    if st.session_state.get('previous_competition') != selected_competitions:
        st.session_state.selected_match = None
        st.session_state.previous_competition = selected_competitions

    if selected_competitions:
        rencontres_filtrees_df = rencontres_df[rencontres_df[config.COLUMN_MAPPING['rencontres_competition']].isin(selected_competitions)]
    else:
        rencontres_filtrees_df = rencontres_df
    rencontres_filtrees_df = rencontres_filtrees_df.sort_values(by=['COMPETITION NOM', 'rencontres_date_dt'])
    unique_matches_df = rencontres_filtrees_df.drop_duplicates(subset=['RENCONTRE NUMERO'])
    if unique_matches_df.empty:
        st.warning("Aucune rencontre trouvée.")
    else:
        for _, rencontre in unique_matches_df.iterrows():
            with st.container(border=True):
                if not selected_competitions:
                    st.caption(rencontre[config.COLUMN_MAPPING['rencontres_competition']])
                st.subheader(f"{rencontre[config.COLUMN_MAPPING['rencontres_locaux']]} vs {rencontre[config.COLUMN_MAPPING['rencontres_visiteurs']]}")
                st.caption(f"{rencontre['rencontres_date_dt'].strftime('%d/%m/%Y')}")
                roles = rencontre.get('ROLES', [])
                if roles:
                    icon_str = " ".join([config.ROLE_ICONS.get(role, config.ROLE_ICONS['default']) for role in roles])
                    st.markdown(f"**Rôles pourvus :** {icon_str}")
                st.button("Sélectionner", key=f"select_{rencontre['RENCONTRE NUMERO']}", on_click=lambda num=rencontre['RENCONTRE NUMERO']: st.session_state.update(selected_match=num))
with right_col:
    if not st.session_state.selected_match:
        st.info("⬅️ Sélectionnez un match dans la liste de gauche pour commencer.")
    else:
        selected_match_numero = st.session_state.selected_match
        rencontre_details = rencontres_df[rencontres_df['RENCONTRE NUMERO'] == selected_match_numero].iloc[0]
        st.header(f"🎯 {rencontre_details[config.COLUMN_MAPPING['rencontres_locaux']]} vs {rencontre_details[config.COLUMN_MAPPING['rencontres_visiteurs']]}")
        if st.button("🔄 Rafraîchir", help="Met à jour les données de désignation"):
            st.cache_data.clear()
            st.rerun()
        display_current_designations(rencontre_details, designations_combinees_df, designations_df, gc)
        st.divider()
        display_referee_finder(rencontre_details, arbitres_df, club_df, categories_df, competitions_df, dispo_df, designations_df, gc)
