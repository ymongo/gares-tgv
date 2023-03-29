#!/usr/bin/env python3

"""
Module Docstring
"""

__author__ = "MONGO"
__version__ = "0.1.0"
__license__ = "MIT"


import argparse
import pandas as pd
from bs4 import BeautifulSoup as bs
import requests
from requests.adapters import HTTPAdapter, Retry
from logzero import logger
import ssl
import json

session = requests.Session()
retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[ 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

ssl._create_default_https_context = ssl._create_unverified_context
DEBUG = 0
GARES_SNCF_URL="https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/referentiel-gares-voyageurs/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"
HORAIRES_GARES_SNCF_URL = 'https://www.garesetconnexions.sncf/fr/gares-services/{gare}/horaires'
API_HORAIRES = "https://garesetconnexions-online.azure-api.net/API/PIV/Departures/00{code}" 
WIKIPEDIA_GARES_URL = "https://fr.wikipedia.org/wiki/{nom_gare}"
WIKIPEDIA_LISTES_GARES_TGV_URL = "https://fr.wikipedia.org/wiki/Liste_des_gares_desservies_par_TGV"
sncf_apikey = ""
failed_wikipedia_request = []

def print_badline(arg):
    logger.info(f"{arg}")

def get_url(url, supp_headers={}):
    headers = {
        'Accept': '*/*',
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0",
    }
    headers.update(supp_headers)
    logger.info(f"Calling url {url} with headers {headers}")

    response = session.get(url, headers=headers, )
    if response.status_code == 200:
        logger.info(f"Succesfully retrieved content for url {url}")
    else:
        notfound = "not found html"
        logger.error(
            f"Something went wrong while retrieving content for url {url}, status code {response.status_code}, message {response.text if response.status_code != 404 else notfound}")
    return response

def has_horaires_tgv(x, sncf_apikey): 
    headers = {
        "Ocp-Apim-Subscription-Key": sncf_apikey,
    }

    content = get_url(API_HORAIRES.format(code=x), supp_headers=headers)
    horaires_df = pd.DataFrame(json.loads(content.text))
    is_gare_tgv_by_horaires = False
    if horaires_df.shape[0] > 0: 
        is_gare_tgv_by_horaires = horaires_df[horaires_df['trainType'].str.contains('TGV', case=False) == True].shape[0] > 0
        logger.info(f"is {x} une gare tgv by horaires? {is_gare_tgv_by_horaires}")

    return is_gare_tgv_by_horaires

def has_wikipedia_tgv_mention(intitule_gare: str):
    intitule_gare = intitule_gare.replace(" - ", "_-_").replace(" ", "-")
    is_gare_tgv_by_wikipedia = False
    prefixe_gare = "Gare_de_"
    if "Les-" in intitule_gare[0:4]:
        intitule_gare = intitule_gare.split('Les-')[1].strip()
        prefixe_gare = "Gare_des_"
    elif "Le-" in intitule_gare[0:3]:
        intitule_gare = intitule_gare.split('Le-')[1].strip()
        prefixe_gare = "Gare_du_"
    elif "La-" in intitule_gare[0:3]:
        intitule_gare = intitule_gare.replace('La-', 'La_',1)
        prefixe_gare = "Gare_de_"
    elif intitule_gare[0].lower() in ["a", "e", "é", "i", "o", "u", "y"] :
        prefixe_gare = "Gare_d'"

        """ Correctifs data"""
    if intitule_gare ==  "Mâcon":
        intitule_gare = "Mâcon-Ville"
    if intitule_gare == "Calais":
        intitule_gare = "Calais-Ville"
    elif intitule_gare == "Valence":
        intitule_gare = "Valence-Ville"
    elif intitule_gare == 'Futuroscope':
        prefixe_gare = "Gare_du_"
    elif intitule_gare == "Saint-Maixent-L'École":
        intitule_gare = "Saint-Maixent_(Deux-Sèvres)"
    elif "Plagne" in intitule_gare:
        intitule_gare = "Aime-La_Plagne"
    elif intitule_gare == "Saint-Gervais-les-Bains-Le-Fayet":
        intitule_gare = "Saint-Gervais-les-Bains-Le_Fayet"
    elif "Aix-" in intitule_gare:
        intitule_gare = "Aix-les-Bains-Le_Revard"
    
    if '_Le-' in intitule_gare:
        intitule_gare = intitule_gare.replace('_Le-', '_Le_')
    elif '_La-' in intitule_gare:
        intitule_gare = intitule_gare.replace('_La-', '_La_')
    
    url = WIKIPEDIA_GARES_URL.format(nom_gare=prefixe_gare+intitule_gare)
    data = get_url(url)
    soup = bs(data.content, "html5lib")
    if len(soup.text) > 0:
        is_gare_tgv_by_wikipedia = False
        try:
            tgv_mention = soup.find("div", id="mw-content-text")
            tgv_mention = tgv_mention.find("table", class_="infobox_v2")
            tgv_mention = tgv_mention.find(lambda tag:tag.name=="tr" and "Service" in tag.text)
            tgv_mention = tgv_mention.find(lambda tag:tag.name=="a" and "TGV" in tag.text)
           
            is_gare_tgv_by_wikipedia = 'tgv' in tgv_mention.get_text().lower() if tgv_mention is not None else False
        except AttributeError:
            logger.error(f"Attribute errror, couldn't find wikipedia tgv info for {intitule_gare}")
            global failed_wikipedia_request
            failed_wikipedia_request.append([url, data.status_code])
            is_gare_tgv_by_wikipedia = False
        logger.info(f"is {intitule_gare} une gare tgv by wikipedia? {is_gare_tgv_by_wikipedia}")
    return is_gare_tgv_by_wikipedia

def main(args):

    if args.check: 
        wiki_liste_gares_sncf_data = get_url(WIKIPEDIA_LISTES_GARES_TGV_URL)
        soup = bs(wiki_liste_gares_sncf_data.content, "html5lib")
        gares_fr_table = soup.find('table', {"class":"wikitable sortable"})
        gares_fr_table_df = pd.read_html(str(gares_fr_table))[0]
        gares_fr_table_df["Gare cleaned"]= gares_fr_table_df["Gare"].apply(lambda x: x.replace(' - ', ' ').replace('-', ' '))
        gares_tgv = pd.read_csv('output.csv', engine="python", on_bad_lines=print_badline)
        gares_fr_table_df["Gare identified"]= gares_tgv["Intitulé plateforme"].apply(lambda x: x.replace(' - ', ' ').replace('-', ' '))
        gares_fr_table_df["Checked"]= gares_fr_table_df["Gare cleaned"].apply(lambda x: x).isin(gares_fr_table_df["Gare identified"])
        gares_fr_table_df.to_csv('check.csv', encoding="utf-8")
        return
    
    """ Main entry point of the app """
    logger.info("hello world")

    """ get gares data"""
    gares=pd.read_csv(GARES_SNCF_URL, engine="python", on_bad_lines=print_badline, sep='\;')
    
    logger.info(f"test head: {gares.head()}")
    
    """ get gares count"""
    logger.info(f"gares: count {gares.shape[0]}")

    """ filter is not gare RER"""
    gares = gares[gares['Intitulé plateforme'].str.contains('RER') == False].copy()
    logger.info(f"gares is not RER : count {gares.shape[0]}")

    """ filter has not date fin validité plateforme"""
    gares = gares[pd.isnull(gares['Date fin validité plateforme']) == True ].copy()
    logger.info(f"gares has not date fin de validité : count {gares.shape[0]}")

    """identify gares tgv with Intitulé plateforme"""
    gares['Verification TGV'] = gares['Intitulé plateforme'].apply(lambda x: 'intitulé plateforme' if 'tgv' in x.lower() else None)
    gares_tgv = gares[pd.isnull(gares['Verification TGV']) == False].copy()
    gares = gares[pd.isnull(gares['Verification TGV']) == True].copy()
    logger.info(f"test wip gares tgv by intitulé: {gares_tgv.shape[0]}")
    logger.info(f"remaining gares after intitule: {gares.shape[0]}")

    """ get sncf api key """
    horaires_page = get_url(HORAIRES_GARES_SNCF_URL.format(gare="saint-malo"))
    soup = bs(horaires_page.content, "html5lib")
    sncf_apikey = soup.find("div", class_="scheduleStation")["data-apikey"]
    logger.info(f"sncf api key: {sncf_apikey}")

    """identify gares tgv by horaires"""
    gares['Verification TGV'] = gares['Code UIC'].apply(lambda x: 'horaires' if has_horaires_tgv(x, sncf_apikey) else None)
    gares_tgv = pd.concat([gares_tgv, gares[pd.isnull(gares['Verification TGV']) == False]])
    gares = gares[pd.isnull(gares['Verification TGV']) == True].copy()
    logger.info(f"test wip gares tgv by horaires: {gares_tgv.shape[0]}")
    logger.info(f"remaining gares after horaires: {gares.shape[0]}")

    """identify gares tgv by wikipedia"""
    gares['Verification TGV'] = gares['Intitulé plateforme'].apply(lambda x: 'wikipedia' if has_wikipedia_tgv_mention(x) else None)
    gares_tgv = pd.concat([gares_tgv, gares[pd.isnull(gares['Verification TGV']) == False]])
    gares = gares[pd.isnull(gares['Verification TGV']) == True].copy()
    logger.info(f"test wip gares tgv by wikipedia: {gares_tgv.shape[0]}")
    logger.info(f"remaining gares after wikipedia: {gares.shape[0]}")

    """clean up, save to file"""
    gares_tgv = gares_tgv.drop_duplicates(subset=['Code gare']).sort_values(by=['Intitulé plateforme'])
    gares_tgv.to_csv('output.csv', encoding='utf-8')
    logger.info(f"final gares tgv count: {gares_tgv.shape[0]}")

    """save failed wikipedia request"""
    with open(r'failed_wikipedia-requests.txt', 'w', encoding='utf-8') as fp:
        global failed_wikipedia_request
        for item in failed_wikipedia_request:
            fp.write("%s\n" % item)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true")

    return parser.parse_args()

if __name__ == "__main__":
    """ This is executed when run from the command line """
    args = args = get_args()
    main(args)
