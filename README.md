
# Gares TGV

Construit un fchier csv listant les gares SNCF TGV en France, à partir de la liste des gares SNCF accesible à https://www.data.gouv.fr/fr/datasets/liste-des-gares/

L'idée étant d'obtenir un maximum d'informations à partir des données SNCF en prermier lieu, puis de compléter et vérifier avec des données Wikipedia.


## Installation

Récupérez le script en local, créez un venv dans le dossier du script et activez-le:

```bash
  python -m venv .venv
  .venv/Scripts/activate
```

Une fois le venv activé installez les libs requises et lancez le script:
```bash
  pip install -r requirements.txt
  python main.py

```

##  Traitements Effectués

Le script récupère la liste des gares SNCF puis:
- retire les gares RER
- retire les gares ayant une date de fin de validité
- identifie les gares TGV par intitulé plateforme
- identifie les gares TGV par horaires en gare
- identifie les gares TGV par page wikipedia
- exporte les gares TGV identifiées dans un fichier output.csv

Vérification possible avec les gares listées sur https://fr.wikipedia.org/wiki/Liste_des_gares_desservies_par_TGV (nombreux faux positifs, données à uniformaiser)
```bash
  python main.py --check

```