# API Collectes de Déchets

API REST pour consulter les calendriers de collecte des déchets.

Fonctionnalités principales:
- Consultation des collectes
- Filtrage par type, ville, date
- Recherche de la prochaine collecte
- Documentation interactive (Swagger)
- Parser du calendrier PDF

Installation (Docker - recommandé)

Prérequis:
- Docker
- Docker Compose

Démarrage rapide (développement):
1. Copier votre PDF calendrier dans `data/`:
```bash
# cp /path/to/your-calendar.pdf data/calendar.pdf
```
2. Démarrer en mode développement (montage local):
```bash
docker-compose up -d --build
```

Déploiement (exemple production):
- adaptez `docker-compose.example.yml` et remplacez les placeholders par vos chemins.

Commandes utiles:
```bash
# Démarrer
docker-compose up -d

# Voir les logs
docker-compose logs -f api

# Arrêter
docker-compose down

# Re-parser le calendrier
docker-compose exec api python scripts/parse_calendar.py
```

Configuration des volumes:
- En développement: le répertoire `./data` est monté dans le conteneur (`/app/data`).
- En production: utilisez un volume Docker ou un bind-mount sur votre hôte.

Utilisation sans Docker

1. Installer les dépendances:
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
2. Copier le PDF dans `data/` puis lancer le parser:
```bash
python scripts/parse_calendar.py
```
3. Lancer l'API en dev:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints principaux:
- `GET /collections/` — liste des collectes
- `GET /collections/{id}` — collecte par id
- `GET /collections/next` — prochaine collecte
- Documentation interactive: `/docs` (Swagger)

Structure du projet:
```
fr-trash-collect-api/
├── app/
├── scripts/
├── data/
├── requirements.txt
├── docker-compose.yml
├── docker-compose.example.yml
└── README.md
```

Contributions

Ouvrez une issue ou une pull request sur le dépôt GitHub.

Licence: MIT
# API Collectes de Déchets - Nouvoitou & Saint-Armel

API REST en lecture seule pour consulter les calendriers de collecte des déchets de Rennes Métropole pour les communes de Nouvoitou et Saint-Armel.

## Fonctionnalités

- Consultation des collectes planifiées
- Filtrage par type de déchet, ville, date
- Recherche de la prochaine collecte
- Statistiques sur les collectes
- Documentation interactive Swagger UI
- Parser automatique du calendrier PDF

## Types de collecte

- **Ordures ménagères**: Lundi semaine paire
- **Déchets recyclables**: Jeudi semaine impaire
- **Déchets alimentaires**: Composteur (non collecté)

## Installation

### Option 1: Docker (Recommandé)

#### Prérequis
- Docker
- Docker Compose

#### Démarrage rapide avec Docker

1. **Copier le PDF calendrier**:
```bash
cp /chemin/vers/Nouvoitou-Saint-Armel.pdf data/calendar.pdf
```

2. **Construire et démarrer le conteneur**:
```bash
docker-compose up -d
```

3. **Parser le calendrier** (première utilisation):
```bash
docker-compose exec api python scripts/parse_calendar.py
```

4. **Accéder à l'API**: http://localhost:8000/docs

#### Commandes Docker utiles

```bash
# Démarrer l'API
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter l'API
docker-compose down

# Reconstruire l'image après modification du code
docker-compose up -d --build

# Re-parser le calendrier
docker-compose exec api python scripts/parse_calendar.py

# Accéder au shell du conteneur
docker-compose exec api /bin/bash
```

### Option 2: Installation locale

#### Prérequis
- Python 3.10+
- pip

#### Installation des dépendances

```bash
# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

## Utilisation

### Avec Docker

L'API est automatiquement démarrée avec `docker-compose up -d`. Pour parser le calendrier:

```bash
docker-compose exec api python scripts/parse_calendar.py
```

### Sans Docker

#### 1. Parser le calendrier PDF

Avant de démarrer l'API, vous devez parser le calendrier PDF pour peupler la base de données:

```bash
# Copier le PDF dans le dossier data/
cp /chemin/vers/Nouvoitou-Saint-Armel.pdf data/calendar.pdf

# Activer l'environnement virtuel
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Exécuter le parser
python scripts/parse_calendar.py
```

Options du parser:
```bash
python scripts/parse_calendar.py --help

# Personnaliser les paramètres
python scripts/parse_calendar.py \
  --pdf data/calendar.pdf \
  --cities "Nouvoitou,Saint-Armel" \
  --start 2024-10-01 \
  --end 2026-09-30
```

#### 2. Lancer l'API

```bash
uvicorn app.main:app --reload
```

L'API sera accessible à l'adresse: `http://localhost:8000`

#### 3. Accéder à la documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints API

### GET /

Page d'accueil avec informations sur l'API.

### GET /collections/

Liste toutes les collectes avec filtres optionnels:

**Paramètres de requête:**
- `skip` (int): Nombre d'éléments à ignorer pour la pagination
- `limit` (int): Nombre maximum d'éléments à retourner (max 100)
- `waste_type` (str): Filtrer par type (`ordures_menageres`, `dechets_recyclables`, `dechets_alimentaires`)
- `city` (str): Filtrer par ville (`Nouvoitou`, `Saint-Armel`)
- `start_date` (date): Date de début (format YYYY-MM-DD)
- `end_date` (date): Date de fin (format YYYY-MM-DD)
- `upcoming` (bool): Si true, ne retourne que les collectes futures

**Exemples:**
```bash
# Toutes les collectes
curl http://localhost:8000/collections/

# Ordures ménagères uniquement
curl http://localhost:8000/collections/?waste_type=ordures_menageres

# Collectes à venir pour Nouvoitou
curl http://localhost:8000/collections/?city=Nouvoitou&upcoming=true

# Collectes de janvier 2025
curl http://localhost:8000/collections/?start_date=2025-01-01&end_date=2025-01-31
```

### GET /collections/{collection_id}

Récupère une collecte spécifique par son ID.

**Exemple:**
```bash
curl http://localhost:8000/collections/1
```

### GET /collections/next

Récupère la prochaine collecte planifiée.

**Paramètres de requête:**
- `waste_type` (str, optionnel): Filtrer par type
- `city` (str, optionnel): Filtrer par ville

**Exemples:**
```bash
# Prochaine collecte (tous types)
curl http://localhost:8000/collections/next

# Prochaine collecte d'ordures ménagères
curl http://localhost:8000/collections/next?waste_type=ordures_menageres

# Prochaine collecte pour Saint-Armel
curl http://localhost:8000/collections/next?city=Saint-Armel
```

### GET /collections/stats

Récupère les statistiques sur les collectes.

**Exemple:**
```bash
curl http://localhost:8000/collections/stats
```

**Réponse:**
```json
{
  "total_collections": 104,
  "collections_by_type": {
    "ordures_menageres": 52,
    "dechets_recyclables": 52,
    "dechets_alimentaires": 0
  },
  "next_ordures_menageres": { ... },
  "next_dechets_recyclables": { ... }
}
```

## Structure du projet

```
trash-collection-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI
│   ├── models.py            # Modèles SQLAlchemy
│   ├── schemas.py           # Schémas Pydantic
│   ├── database.py          # Configuration base de données
│   └── crud.py              # Opérations de lecture
├── scripts/
│   ├── __init__.py
│   └── parse_calendar.py    # Parser du calendrier PDF
├── data/
│   └── calendar.pdf         # Calendrier PDF (à ajouter)
├── requirements.txt
├── .gitignore
└── README.md
```

## Modèle de données

### Collection

| Champ | Type | Description |
|-------|------|-------------|
| id | Integer | Identifiant unique |
| date | Date | Date de la collecte |
| waste_type | String | Type de déchet (enum) |
| city | String | Ville (Nouvoitou ou Saint-Armel) |
| day_of_week | String | Jour de la semaine en français |
| week_number | Integer | Numéro de semaine ISO |
| is_holiday_shift | Boolean | Collecte décalée à cause d'un jour férié |
| notes | String | Notes optionnelles (raison du décalage) |
| created_at | DateTime | Date de création en base |

## Gestion des jours fériés

Le parser gère automatiquement les décalages liés aux jours fériés:
- Si une collecte tombe un jour férié ou un weekend, elle est décalée au jour ouvrable suivant
- Le champ `is_holiday_shift` est marqué à `true`
- Une note explicative est ajoutée dans le champ `notes`

## Technologies

- **FastAPI**: Framework web moderne et performant
- **SQLAlchemy**: ORM pour la gestion de la base de données
- **SQLite**: Base de données légère
- **Pydantic**: Validation des données
- **pdfplumber**: Extraction de données PDF
- **Typer**: Interface en ligne de commande

## Développement

### Mettre à jour le calendrier

Lorsqu'un nouveau calendrier PDF est disponible:

1. Remplacer le fichier PDF dans `data/calendar.pdf`
2. Relancer le parser: `python scripts/parse_calendar.py`
3. Les anciennes données seront automatiquement supprimées et remplacées

### Relancer l'API en mode développement

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Licence

Ce projet est fourni à titre d'exemple pour la gestion des collectes de déchets.

## Contact

Pour toute question sur les collectes de déchets: 0 223 622 622

Site web: https://metropole.rennes.fr
