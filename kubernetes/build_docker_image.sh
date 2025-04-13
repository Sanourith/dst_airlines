#!/bin/bash

set -e
# set -x

# Récupérer le répertoire où se trouve le script
script_dir="$(dirname "$(realpath "$0")")"

directories=("airflow" "fastapi" "mongo-DB" "mysql" "prometheus_grafana")

owner="sanourith"

env_file="$script_dir/../env/private.env"

if [[ ! -f "$env_file" ]]; then
    echo "Error: $env_file not found. Please check the path."
    exit 1
fi

# Charger les variables d'environnement depuis private.env
export $(grep -v '^#' "$env_file" | xargs)

# Boucle sur les directories
for repo in "${directories[@]}"; do
    repo_path="$script_dir/$repo"  # Chemin du répertoire du repository
    repo_name=$(basename "$repo")  # Nom du répertoire actuel

    # Vérifie si le Dockerfile existe dans ce répertoire
    if [[ -f "$repo_path/Dockerfile" ]]; then
        echo "Building Dockerfile for $repo_name..."

        # Construire l'image Docker de base
        docker build -t "$owner/$repo_name" "$repo_path"
        echo "$owner/$repo_name image built successfully."

        # Si le repo est mysql, construire avec les variables privées
        if [[ "$repo_name" == "mysql" ]]; then
            echo "Building MySQL version with private.env variables..."
            docker build \
                --build-arg MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD \
                --build-arg MYSQL_DATABASE=$MYSQL_DATABASE \
                --build-arg MYSQL_USER=$MATTHIEU_USERNAME \
                --build-arg MYSQL_PASSWORD=$MATTHIEU_PASSWORD \
                -t my-mysql-image "$repo_path"
            echo "MySQL image built successfully with private.env variables."
        fi
    else 
        echo "No Dockerfile detected for $repo. Continuing..."
        continue
    fi
done

echo "Dockerfiles build commands launched successfully."