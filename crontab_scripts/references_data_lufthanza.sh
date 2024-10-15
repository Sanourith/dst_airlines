#! /bin/bash

echo "Lancement du script de récupération des API\nAirports\nAirlines\nAircrafts\nCities"
python3 /home/sanou/DST-Airlines/dst_airlines/data/Lufthansa_API_to_csv.py
echo "Script terminé"

# crontab -e
# * 16 * * * script