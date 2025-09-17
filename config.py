"""
Fichier de configuration central pour l'application Streamlit.
Ce fichier contient les constantes, les URLs, les mappings de colonnes,
et les données statiques utilisées à travers l'application.
DISPO = RS_OVALE-022
RENCNTRES = RS_OVALE-024
ARBITRES = RS_OVALE-052
RENCONTRES_OVALE = RS_OVALE-023
CLUBS = RS_OVALE-007
"""
import pandas as pd

# --- URLs des Google Sheets ---
RENCONTRES_URL = "https://docs.google.com/spreadsheets/d/1I8RGfNNdaO1wlrtFgIOFbOnzpKszwJTxdyhQ7rRD1bg/export?format=xlsx"
DISPO_URL = "https://docs.google.com/spreadsheets/d/16-eSHsURF-H1zWx_a_Tu01E9AtmxjIXocpiR2t2ZNU4/export?format=xlsx"
ARBITRES_URL = "https://docs.google.com/spreadsheets/d/1bIUxD-GDc4V94nYoI_x2mEk0i_r9Xxnf02_Rn9YtoIc/export?format=xlsx"
CLUB_URL = "https://docs.google.com/spreadsheets/d/1GLWS4jOmwv-AOtkFZ5-b5JcjaSpBVlwqcuOCRRmEVPQ/export?format=xlsx"
DESIGNATIONS_URL = "https://docs.google.com/spreadsheets/d/1gaPIT5477GOLNfTU0ITwbjNK1TjuO8q-yYN2YasDezg/export?format=xlsx"
RENCONTRES_FFR_URL = "https://docs.google.com/spreadsheets/d/1ViKipszuqE5LPbTcFk2QvmYq4ZNQZVs9LbzrUVC4p4Y/export?format=xlsx"

# --- Fichier de clé de service ---
SERVICE_ACCOUNT_FILE = 'designation-cle.json'

# --- Mappings de Colonnes (consolidés) ---
COLUMN_MAPPING = {
    # Rencontres
    "rencontres_date": "DATE EFFECTIVE",
    "rencontres_competition": "COMPETITION NOM",
    "rencontres_locaux": "LOCAUX",
    "rencontres_visiteurs": "VISITEURS",
    "rencontres_numero": "RENCONTRE NUMERO",

    # Disponibilités
    "dispo_date": "DATE",
    "dispo_disponibilite": "DISPONIBILITE",
    "dispo_licence": "NO LICENCE",
    "dispo_designation": "DESIGNATION",

    # Arbitres
    "arbitres_affiliation": "Numéro Affiliation",
    "arbitres_nom": "Nom",
    "arbitres_prenom": "Prénom",
    "arbitres_categorie": "Catégorie",
    "arbitres_club_code": "Code Club",
    "arbitres_dpt_residence": "Département de Résidence",

    # Compétitions
    "competitions_nom": "NOM",
    "competitions_niveau_min": "NIVEAU MIN",
    "competitions_niveau_max": "NIVEAU MAX",

    # Catégories
    "categories_nom": "CATEGORIE",
    "categories_niveau": "Niveau",

    # Clubs
    "club_nom": "Nom",
    "club_code": "Code",
    "club_dpt": "DPT",
    "club_cp": "CP",
    
    # Désignations FFR
    "ffr_fonction_arbitre": "FONCTION ARBITRE",
    "ffr_nom": "NOM",
    "ffr_prenom": "PRENOM",
    "ffr_dpt_residence": "DPT DE RESIDENCE",
}

# --- Configuration pour la page de Désignation ---
ROLE_ICONS = {
    "Arbitre de champ": "🧑‍⚖️",
    "Arbitre Assistant 1": "🚩",
    "Arbitre Assistant 2": "🚩",
    "4e/5e arbitre": "📋",
    "Représentant Fédéral": "👔",
    "default": "❓"
}
ALL_ROLES = ["Arbitre de champ", "Arbitre Assistant 1", "Arbitre Assistant 2"]


# --- Liste des compétitions à filtrer par défaut ---
COMPETITIONS_FILTRE_DEFAUT = [
    "Fédérale 3",
    "Espoirs Fédéraux",
    "National U16",
    "National U18",
    "Gauderman",
    "Excellence B - Championnat de France",
    "Fédérale B - Championnat de France",
    "Fédérale 1 Féminine",
    "Fédérale 2 féminine",
    "Fédérale 2 Féminine – IDF/HDF",
    "Féminines Régionales à X",
    "Régionale 1 - Championnat Territorial",
    "Réserves Régionales 1 - Championnat Territorial",
    "Régionale 2 - Championnat Territorial",
    "Réserves Régionales 2 - Championnat Territorial",
    "Régionale 3 - Championnat Territorial",
    "Réserves Régionales 3 - Championnat Territorial",
    "Régional 1 U19",
    "Régional 2 U19",
    "Régional 3 U19",
    "Féminines Régionales à X « moins de 18 ans »",
    "Féminines Moins de 18 ans à XV - ELITE",
    "Régional 1 U16",
    "Régional 2 U16",
    "Régional 3 U16",
    "Championnat Territorial des Clubs + 18 ans Féminin à 7",
    "Championnat Territorial des Clubs - 18 ans Féminin à 7",
    "Matchs d'échanges",
    "Loisirs"
]

# --- Données Statiques ---
def load_static_categories():
    """Charge le DataFrame des catégories d'arbitres."""
    categories_data = {
        'Niveau': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        'CATEGORIE': ['Internationaux', '2ème Division PRO', 'Nationale 1 et 2', 'Arbitres assistants PRO', 'Arbitres assistants NAT', 'Divisionnaires 1', 'Divisionnaires 2', 'Divisionnaires 3', 'Ligue 1', 'Ligue 2', 'Ligue 3', 'Ligue 4', 'Ligue 5', 'Mineurs 17 ans', 'Mineurs 16 ans', 'Mineurs 15 ans']
    }
    return pd.DataFrame(categories_data)

def load_static_competitions():
    """Charge le DataFrame des compétitions."""
    competitions_data = {
        'NOM': [
            'Elite 1 Féminine', 'Elite 2 Féminine', 'Elite Alamercery', 'Elite Crabos', 
            'Espoirs Fédéraux', 'European Rugby Champions Cup', 'Excellence B - Championnat de France', 
            'Fédérale 1', 'Fédérale 2', 'Fédérale 3', 'Fédérale B - Championnat de France', 
            'Fédérale 1 Féminine', 'Fédérale 2 féminine', 'Fédérale 2 Féminine – IDF/HDF',
            'Féminines Moins de 18 ans à XV - ELITE', 'Féminines Régionales à X', 
            'Féminines Régionales à X « moins de 18 ans »', 'Gauderman', 'Loisirs', 'Matchs d\'échanges',
            'National U16', 'National U18', 
            'Régional 1 U16', 'Régional 1 U19', 'Régional 2 U16', 'Régional 2 U19', 
            'Régional 3 U16', 'Régional 3 U19', 
            'Régionale 1 - Championnat Territorial', 'Régionale 2 - Championnat Territorial', 
            'Régionale 3 - Championnat Territorial', 
            'Réserves Elite', 'Réserves Régionales 1 - Championnat Territorial', 
            'Réserves Régionales 2 - Championnat Territorial', 'Réserves Régionales 3 - Championnat Territorial',
            'Championnat Territorial des Clubs + 18 ans Féminin à 7', 
            'Championnat Territorial des Clubs - 18 ans Féminin à 7'
        ],
        'NIVEAU MIN': [
            6, 7, 7, 6, 6, 1, 9, 6, 7, 8, 9, 
            6, 7, 7, 7, 13, 14, 8, 15, 15, 6, 6,
            15, 10, 15, 13, 15, 13, 
            9, 11, 13, 
            7, 11, 13, 15,
            13, 15
        ],
        'NIVEAU MAX': [
            4, 6, 6, 4, 4, 1, 7, 6, 7, 8, 7, 
            4, 6, 6, 6, 10, 13, 6, 9, 9, 4, 4,
            9, 9, 9, 9, 9, 9, 
            7, 9, 9, 
            9, 9, 11, 9,
            9, 9
        ]
    }
    return pd.DataFrame(competitions_data)
