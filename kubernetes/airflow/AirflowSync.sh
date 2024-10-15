#!/bin/bash

echo " -- Start : Add and update apache airflow -- "
helm repo add apache-airflow https://airflow.apache.org
helm repo update
echo " -- End : Create namespace airlines -- "

echo " -- Start : Create namespace airlines -- "
kubectl create namespace airlines
echo " -- End : Create namespace airlines -- "

echo " -- Start : Apply PV / PVC -- "
kubectl apply -f ./airflow/pv-logs.yaml -n airlines
kubectl apply -f ./airflow/pvc-logs.yaml -n airlines
echo " -- End : Apply PV / PVC -- "

echo " -- Start : Sleep 3s -- "
sleep 3
echo " -- End : Sleep 3s -- "

echo " -- Start : Install Airflow -- "
helm upgrade --install airflow apache-airflow/airflow -f ./airflow/override.yaml --namespace airlines
echo " -- End : Install Airflow -- "

# Pour port-forward le service, exécutez la commande suivante :

# kubectl port-forward svc/airflow-webserver 8080:8080 --namespace airlines


#Installation : 

# ssh-keygen -t rsa -b 4096 -C "remiducroc@gmail.com"
# base64 key.private -w 0 > temp.txt
# cat temp.txt
# cat key.pub





# helm install airflow apache-airflow/airflow \
# --namespace airlines \
# --set airflow.image.repository=glampe/dst_airlines_custom_airflow \
# --set airflow.image.tag=0.1.0 
# --set webserver.defaultUser.username="$admin_env" \
# --set webserver.defaultUser.password="$admin_env" \
# --set postgresql.auth.postgresPassword="$pg_pw" \
# --set postgresql.auth.username="$pg_user" \
# --set postgresql.auth.password="$pg_pw"
