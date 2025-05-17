# DST-Airlines

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

Predict airplane flight delays based on data collected from Lufthansa API among else

## Project Organization
  
```
├── LICENSE            <- Open-source license if one is chosen
├── Makefile           <- Makefile with convenience commands like `make data` or `make train`
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── docs               <- A default mkdocs project; see mkdocs.org for details
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── pyproject.toml     <- Project configuration file with package metadata for dst_airlines
│                         and configuration for tools like black
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── setup.cfg          <- Configuration file for flake8
│
└── dst_airlines                <- Source code for use in this project.
    │
    ├── __init__.py    <- Makes dst_airlines a Python module
    │
    ├── data           <- Scripts to download or generate data
    │   └── make_dataset.py
    │
    ├── features       <- Scripts to turn raw data into features for modeling
    │   └── build_features.py
    │
    ├── models         <- Scripts to train models and then use trained models to make
    │   │                 predictions
    │   ├── predict_model.py
    │   └── train_model.py
    │
    └── visualization  <- Scripts to create exploratory and results oriented visualizations
        └── visualize.py
```

--------

## Ennoncé

Le projet AIRLINES vous a été attribué, vous trouverez la fiche projet ici: [CLIQUEZ ICI](https://docs.google.com/document/d/1XyT7ePkgoMPAu8jf4q3R88R33dXrm_NwXfh5Px-redo/edit).

Etapes : 
> Pour information, ces étapes sont pensées pour que votre projet se passe au mieux, c’est-à-dire sans problème de dernière minute et avec un rendu final à la hauteur de vos capacités.

- **Étape 0 / Cadrage (Notre première réunion)** : Semaine du 20 Juillet
  - Introduction de chaque membre de l'équipe
  - Explication du cadre du projet (les différentes étapes)
- **Étape 1 / Découverte des sources de données disponibles** : Deadline Début Sprint 4 (30 Juillet)
  - Définir le contexte et le périmètre du projet.
  - Prise en main des différentes sources de données. Il vous faudra explorer les APIs et les pages webs.
  - Livrable attendu: Vous devez fournir un rapport expliquant les différentes sources de données accompagnées d'exemples de données collectées.
- **Étape 2 / Organisation des données** : Deadline MC 4 (08 Aout)
  - Il s'agira de la partie la plus importante de votre projet où vous ferez le cœur du métier de Data Engineer.
  - On vous demande d'organiser les données via différentes bases de données :
    - Relationnelle
    - NoSQL
  - Il faudra penser à l'architecture des données, notamment comment relier les différentes données entre elles.
  - Livrable attendu : Tout document expliquant l'architecture choisie (Diagramme UML)
- **Étape 3 / Consommation des données** : Deadline Mi sprint 5 (27 Aout)
  - Une fois vos données organisées, il faut les consommer, ce n'est pas le rôle initial d'un Data Engineer, mais pour que la pipeline des données soit complète, vous devez avoir cette partie.
  - Il sera attendu de mettre en place un algorithme de Machine Learning qui répondra à votre problématique.
- **Étape 4 / Déploiement** : Deadline Mi Sprint 7 (12 Septembre)
  - Création d'une API du modèle de Machine Learning et/ou de la base de données
  - Réaliser des tests unitaires sur votre API
  - Conteneuriser cette API via Docker et les bases de données
  - Mesurer la dérive des données
- **Étape 5 / Automatisation & Monitoring**: Deadline Fin sprint 9 (03 Octobre)
  - Automatiser les différentes précédentes étapes pour que l'application soit fonctionnel en continu
  - Mettez en place une pipeline CI pour mettre à jour efficacement votre application
  - Monitorer l'application en production
- **Étape 6 / Démonstration de l'application + Soutenance (20 minutes de présentation + 10 minutes de question)** : semaine du 04 Octobre
  - Vulgariser le déroulement de votre projet
  - Expliquer l'architecture choisie lors de l'organisation des données
  - Montrer que l'application est fonctionnelle
  - Il ne sera pas attendu de parler en détail de la section consommation des données

Précisions : 
- Il n'y a pas d'attente spécifique concernant le format et contenu des rapports