FROM python:3.12-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système pour la compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Nettoyer les dépendances de build pour réduire la taille
# On garde uniquement les bibliothèques runtime et on supprime les outils de compilation
RUN apt-get purge -y --auto-remove gcc g++ make \
    && rm -rf /var/lib/apt/lists/*

# Copier le code de l'application
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Créer le répertoire pour la base de données
RUN mkdir -p /app/data

# Exposer le port de l'API
EXPOSE 8000

# Commande pour démarrer l'application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
