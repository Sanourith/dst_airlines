#! /bin/bash

kubectl create namespace airlines
echo " -- Start the creation of MongoDB -- "
helm install mongodb ./mongo-DB/ -n airlines
echo " -- Creation of MongoDB done -- "
echo " -- Start the creation of MySQL -- "
helm install mysql ./mysql/ -n airlines
echo " -- Creation of MySQL done -- "
echo " -- Start the creation of FastAPI -- "
helm install fastapi ./fastapi/ -n airlines
echo " -- Creation of FastAPI done -- "
echo " -- Start the creation of Airflow -- "
bash ./airflow/AirflowSync.sh
echo " -- Start the creation of Prometheus/Grafana -- "
bash ./prometheus_grafana/install.sh
echo " -- Creation of Prometheus/Grafana done -- "


# Post Forwarding du webserver

#kubectl port-forward svc/fastapi-service 8000:80 -n airlines
#kubectl port-forward svc/airflow-webserver 8080:8080 --namespace airlines
#kubectl port-forward svc/prometheus-server 9090:80 -n airlines 

#Avoir l'ip cluster
#kubectl get nodes -o wide

# Nécessité d'avoir une storageClass de type local-path, pour le faire sur minikube (https://minikube.sigs.k8s.io/docs/tutorials/local_path_provisioner/) :
# minikube addons enable storage-provisioner-rancher