FROM mysql:latest

# Définir les variables d'environnement
ARG MYSQL_ROOT_PASSWORD
ARG MYSQL_DATABASE
ARG MYSQL_USER
ARG MYSQL_PASSWORD

ENV MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD
ENV MYSQL_DATABASE=$MYSQL_DATABASE
ENV MYSQL_USER=$MYSQL_USER
ENV MYSQL_PASSWORD=$MYSQL_PASSWORD

# Créer un répertoire personnalisé pour les données et attribuer les bons droits
RUN mkdir -p /custom/mysql/data && chown mysql:mysql /custom/mysql/data

# Copier le fichier de configuration personnalisé dans le conteneur
COPY cnf.conf /etc/mysql/conf.d/

# Exposer le port MySQL
EXPOSE 3306

# Commande de démarrage de MySQL
CMD ["mysqld"]