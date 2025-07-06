import re
import pandas as pd

def extract_club_name_from_team_string(team_string):
    """
    Extrait le nom du club d'une chaîne d'équipe (sans le code entre parenthèses)
    Ex: "STADE ROCHELAIS (SRO)" -> "STADE ROCHELAIS"
    """
    match = re.search(r'^(.*?)\s*(\(\w+\))?$', str(team_string))
    if match:
        return match.group(1).strip()
    return str(team_string).strip()

def extract_club_code_from_team_string(team_string):
    """
    Extrait le code club entre parenthèses d'une chaîne d'équipe
    Ex: "STADE ROCHELAIS (SRO)" -> "SRO"
    Ex: "A C BOBIGNY 93 RUGBY (4581E)" -> "4581E"
    """
    match = re.search(r'\((.*?)\)', str(team_string))
    if match:
        return match.group(1).strip()
    return None

def get_department_from_club_name(club_name_full, club_df, column_mapping):
    """
    Récupère le département à partir du nom du club (méthode originale)
    """
    extracted_name = extract_club_name_from_team_string(club_name_full)
    club_df[column_mapping['club_nom']] = club_df[column_mapping['club_nom']].astype(str)
    matching_clubs = club_df[club_df[column_mapping['club_nom']].str.contains(extracted_name, case=False, na=False)]
    if not matching_clubs.empty:
        # Prioritize exact match if available
        exact_match = matching_clubs[matching_clubs[column_mapping['club_nom']] == extracted_name]
        if not exact_match.empty:
            best_match = exact_match.iloc[0]
        else:
            # If no exact match, use the longest name as a heuristic
            best_match = matching_clubs.loc[matching_clubs[column_mapping['club_nom']].str.len().idxmax()]
        
        cp = str(best_match[column_mapping['club_cp']])
        if len(cp) >= 2:
            return cp[:2]
    return "Non trouvé"

def get_department_from_club_code(club_code, club_df, column_mapping):
    """
    Récupère le département à partir du code club (nouvelle méthode plus précise)
    """
    if not club_code:
        return None
    
    # La colonne du code club dans club_df est 'Code'
    club_code_col = 'Code' # As specified by user
    if club_code_col not in club_df.columns:
        return None
    
    # Recherche par code club exact
    matching_club = club_df[club_df[club_code_col] == club_code]
    
    if not matching_club.empty:
        cp = str(matching_club.iloc[0][column_mapping['club_cp']])
        if len(cp) >= 2:
            return cp[:2]
    return None

def get_department_from_club_name_or_code(club_name_full, club_df, column_mapping):
    """
    Fonction combinée qui essaie d'abord par code, puis par nom
    """
    # Tentative 1 : Par code club
    club_code = extract_club_code_from_team_string(club_name_full)
    if club_code:
        dept_by_code = get_department_from_club_code(club_code, club_df, column_mapping)
        if dept_by_code:
            return dept_by_code
    
    # Tentative 2 : Par nom (fallback)
    return get_department_from_club_name(club_name_full, club_df, column_mapping)

def get_cp_from_club_name(club_name_full, club_df, column_mapping):
    """
    Récupère le code postal complet à partir du nom du club
    """
    extracted_name = extract_club_name_from_team_string(club_name_full)
    club_df[column_mapping['club_nom']] = club_df[column_mapping['club_nom']].astype(str)
    matching_clubs = club_df[club_df[column_mapping['club_nom']].str.contains(extracted_name, case=False, na=False)]
    if not matching_clubs.empty:
        best_match = matching_clubs.loc[matching_clubs[column_mapping['club_nom']].str.len().idxmax()]
        return str(best_match[column_mapping['club_cp']])
    return "Non trouvé"

def get_cp_from_club_code(club_code, club_df, column_mapping):
    """
    Récupère le code postal complet à partir du code club
    """
    if not club_code:
        return "Non trouvé"
    
    club_code_col = 'Code' # As specified by user
    if club_code_col not in club_df.columns:
        return "Non trouvé"
    
    # Recherche par code club exact
    matching_club = club_df[club_df[club_code_col] == club_code]
    
    if not matching_club.empty:
        return str(matching_club.iloc[0][column_mapping['club_cp']])
    return "Non trouvé"

def get_cp_from_club_name_or_code(club_name_full, club_df, column_mapping):
    """
    Fonction combinée pour récupérer le CP qui essaie d'abord par code, puis par nom
    """
    # Tentative 1 : Par code club
    club_code = extract_club_code_from_team_string(club_name_full)
    if club_code:
        cp_by_code = get_cp_from_club_code(club_code, club_df, column_mapping)
        if cp_by_code != "Non trouvé":
            return cp_by_code
    
    # Tentative 2 : Par nom (fallback)
    return get_cp_from_club_name(club_name_full, club_df, column_mapping)

def highlight_designated_cells(df_to_style, grille_dispo, column_mapping):
    """
    Met en évidence les cellules où des arbitres sont désignés
    """
    # Crée une matrice de style vide de la même taille que le df à styler.
    style_matrix = pd.DataFrame('', index=df_to_style.index, columns=df_to_style.columns)
    
    # Récupère la partie "DESIGNATION" de la grille complète.
    designation_data = grille_dispo[column_mapping['dispo_designation']]
    
    # Crée un masque booléen où la désignation est 1 (en remplissant les non-valeurs par 0).
    mask = (designation_data.fillna(0) == 1)
    
    # Applique le style à la matrice de style en utilisant le masque.
    # On s'assure de ne le faire que pour les colonnes communes.
    common_cols = style_matrix.columns.intersection(mask.columns)
    style_matrix.loc[:, common_cols] = style_matrix.loc[:, common_cols].mask(mask[common_cols], 'background-color: #FFDDC1')
    
    return style_matrix
