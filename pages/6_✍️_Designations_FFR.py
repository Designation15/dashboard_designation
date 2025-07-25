import streamlit as st
import pandas as pd

# --- Configuration et chargement des données ---
RENCONTRES_FFR_URL = "https://docs.google.com/spreadsheets/d/1ViKipszuqE5LPbTcFk2QvmYq4ZNQZVs9LbzrUVC4p4Y/export?format=xlsx"
ARBITRES_URL = "https://docs.google.com/spreadsheets/d/1bIUxD-GDc4V94nYoI_x2mEk0i_r9Xxnf02_Rn9YtoIc/export?format=xlsx"
CLUB_URL = "https://docs.google.com/spreadsheets/d/1GLWS4jOmwv-AOtkFZ5-b5JcjaSpBVlwqcuOCRRmEVPQ/export?format=xlsx"

@st.cache_data
def load_static_data():
    categories_data = {
        'Niveau': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        'CATEGORIE': [
            'Internationaux', '2ème Division PRO', 'Nationale 1 et 2', 
            'Arbitres assistants PRO', 'Arbitres assistants NAT', 'Divisionnaires 1', 
            'Divisionnaires 2', 'Divisionnaires 3', 'Ligue 1', 'Ligue 2', 'Ligue 3', 
            'Ligue 4', 'Ligue 5', 'Mineurs 17 ans', 'Mineurs 16 ans', 'Mineurs 15 ans'
        ]
    }
    categories_df = pd.DataFrame(categories_data)
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
    competitions_df = pd.DataFrame(competitions_data)
    competitions_df.rename(columns={'NOM': 'COMPETITION_NAME_FOR_MERGE'}, inplace=True)
    return categories_df, competitions_df

@st.cache_data(ttl=300)
def load_all_data():
    rencontres_df = pd.read_excel(RENCONTRES_FFR_URL)
    arbitres_df = pd.read_excel(ARBITRES_URL)
    club_df = pd.read_excel(CLUB_URL)
    categories_df, competitions_df = load_static_data()
    
    for df in [rencontres_df, arbitres_df, club_df]:
        df.columns = df.columns.str.strip()

    if 'CP' in club_df.columns:
        club_df['DPT_from_CP'] = club_df['CP'].astype(str).str.zfill(5).str[:2]
    else:
        club_df['DPT_from_CP'] = pd.NA

    if 'NOM' in rencontres_df.columns and 'Nom' not in rencontres_df.columns:
        rencontres_df.rename(columns={'NOM': 'Nom'}, inplace=True)

    # --- Robust Merge Logic ---
    arbitres_cols_to_merge = ['Numéro Affiliation', 'Catégorie', 'DPT DE RESIDENCE']
    existing_arbitres_cols = [col for col in arbitres_cols_to_merge if col in arbitres_df.columns]
    merged_df = pd.merge(rencontres_df, arbitres_df[existing_arbitres_cols], left_on='NUMERO LICENCE', right_on='Numéro Affiliation', how='left')
    # --- End Robust Merge ---

    merged_df = pd.merge(merged_df, categories_df, left_on='Catégorie', right_on='CATEGORIE', how='left')
    merged_df = pd.merge(merged_df, competitions_df, left_on='COMPETITION NOM', right_on='COMPETITION_NAME_FOR_MERGE', how='left')

    if 'LOCAUX' in merged_df.columns and 'Code' in club_df.columns:
        merged_df['LOCAUX_CODE'] = merged_df['LOCAUX'].str.extract(r'\((.*?)\)').fillna('0').astype(str)
        club_df['Code'] = club_df['Code'].astype(str)
        merged_df = pd.merge(merged_df, club_df[['Code', 'DPT_from_CP', 'CP']], left_on='LOCAUX_CODE', right_on='Code', how='left')
        merged_df.rename(columns={'DPT_from_CP': 'DPT_LOCAUX', 'CP': 'CP_LOCAUX'}, inplace=True)
    
    if 'DPT_LOCAUX' not in merged_df.columns: merged_df['DPT_LOCAUX'] = pd.NA
    if 'CP_LOCAUX' not in merged_df.columns: merged_df['CP_LOCAUX'] = pd.NA
    
    final_numeric_cols = ['Niveau', 'NIVEAU MIN', 'NIVEAU MAX', 'DPT DE RESIDENCE', 'DPT_LOCAUX', 'CP_LOCAUX']
    for col in final_numeric_cols:
        if col in merged_df.columns:
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce')

    return merged_df

# --- Fonctions de vérification ---
def check_neutrality(row):
    dpt_locaux = row.get("DPT_LOCAUX")
    dpt_residence = row.get("DPT DE RESIDENCE")
    if row.get("FONCTION ARBITRE") == "Arbitre de champ" and pd.notna(dpt_residence) and pd.notna(dpt_locaux):
        try:
            if int(dpt_residence) == int(dpt_locaux):
                return "⚠️ Neutralité"
        except (ValueError, TypeError):
            pass
    return ""

def check_competence(row):
    if row.get("FONCTION ARBITRE") == "Arbitre de champ":
        try:
            niveau = int(row.get('Niveau'))
            niveau_min = int(row.get('NIVEAU MIN'))
            niveau_max = int(row.get('NIVEAU MAX'))
            borne_inf = min(niveau_min, niveau_max)
            borne_sup = max(niveau_min, niveau_max)
            if not (borne_inf <= niveau <= borne_sup):
                return "❌ Compétence"
        except (ValueError, TypeError):
            pass
    return ""

def apply_styling(row):
    if "Neutralité" in row["Statut"]:
        return ['background-color: #FFDDC1'] * len(row)
    if "Compétence" in row["Statut"]:
        return ['background-color: #FFC0CB'] * len(row)
    return [''] * len(row)

# --- Chargement des données ---
data_df = load_all_data()

# --- Application ---
st.set_page_config(layout="wide")
st.title("✍️ Désignations FFR - Analyse Avancée")

if not data_df.empty:
    st.sidebar.header("Filtres")
    competitions = sorted([str(c) for c in data_df["COMPETITION NOM"].dropna().unique()])
    selected_competition = st.sidebar.multiselect("Filtrer par Compétition", options=competitions, default=[])
    search_term = st.sidebar.text_input("Rechercher un club ou un arbitre")

    filtered_df = data_df.copy()
    if selected_competition:
        filtered_df = filtered_df[filtered_df["COMPETITION NOM"].isin(selected_competition)]
    if search_term:
        search_mask = (
            filtered_df["LOCAUX"].str.contains(search_term, case=False, na=False) |
            filtered_df["VISITEURS"].str.contains(search_term, case=False, na=False) |
            filtered_df["Nom"].str.contains(search_term, case=False, na=False) | 
            filtered_df["PRENOM"].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[search_mask]

    filtered_df["Statut"] = filtered_df.apply(lambda row: " ".join(filter(None, [check_neutrality(row), check_competence(row)])), axis=1)
    filtered_df["Statut"] = filtered_df["Statut"].replace("", "✅ OK")

    st.header("Statistiques des Désignations")
    total_matchs = filtered_df["NUMERO RENCONTRE"].nunique()
    total_postes = len(filtered_df)
    postes_designes = len(filtered_df[filtered_df["Nom"].notna()])
    postes_a_designer = total_postes - postes_designes

    col1, col2, col3 = st.columns(3)
    col1.metric("Matchs Uniques", total_matchs)
    col2.metric("Postes d'Arbitres Pourvus", f"{postes_designes}/{total_postes}")
    col3.metric("Postes à Pourvoir", postes_a_designer)

    st.divider()

    st.header("Détails des Désignations")
    colonnes_a_afficher = [
        "Statut", "COMPETITION NOM", "LOCAUX", "VISITEURS", "DPT_LOCAUX", "CP_LOCAUX",
        "FONCTION ARBITRE", "Nom", "PRENOM", "DPT DE RESIDENCE", "Catégorie", "Niveau", "NIVEAU MIN", "NIVEAU MAX"
    ]
    
    # On vérifie quelles colonnes existent VRAIMENT avant de les afficher
    colonnes_finales = [col for col in colonnes_a_afficher if col in filtered_df.columns]

    st.dataframe(
        filtered_df[colonnes_finales].style.apply(apply_styling, axis=1).format(
            {
                "DPT DE RESIDENCE": "{:.0f}",
                "Niveau": "{:.0f}",
                "NIVEAU MIN": "{:.0f}",
                "NIVEAU MAX": "{:.0f}",
                "DPT_LOCAUX": "{:.0f}",
                "CP_LOCAUX": "{:.0f}"
            },
            na_rep="-"
        ),
        hide_index=True, 
        use_container_width=True
    )

else:
    st.warning("Aucune donnée n'a pu être chargée.")
