#! /bin/bash
CURRENT_DIR=$(dirname "$(realpath "$0")")
PROJECT_DIR=$(dirname "$CURRENT_DIR")

echo "$CURRENT_DIR"
echo "$PROJECT_DIR"

source "$PROJECT_DIR/env/private.env"

# Lancement des conteneurs docker-compose
docker compose up -d

# Attente que le conteneur soit créé et fonctionnel
sleep 10

# Récupération du nom (--format "{{.Names}}") du conteneur (docker ps) généré par l'image mysql (--filter "ancestor=mysql")
DB_MYSQL=$(docker ps --filter "ancestor=mysql" --format "{{.Names}}")

# "docker exec mysql < file_path" exécute en mysql sur le conteneur le script localisé sur la machine hôte en file_path
# echo "Création de la base de données."
# docker exec -i $DB_MYSQL mysql -u root -p$MYSQL_ROOT_PASSWORD < ./create_dst_airlines_database.sql
echo "Création des utilisateurs."
docker exec -i $DB_MYSQL mysql -u root -p$MYSQL_ROOT_PASSWORD < ./create_dst_airlines_users.sql




