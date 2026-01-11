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

# Copier les données (calendrier) si présentes
COPY data/ ./data/

# Copier l'entrypoint qui lancera le parser si nécessaire
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Créer le répertoire pour la base de données
RUN mkdir -p /app/data

# Exposer le port de l'API
EXPOSE 8000

# Entrypoint: lance le parser si un PDF est présent, puis démarre le serveur
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
