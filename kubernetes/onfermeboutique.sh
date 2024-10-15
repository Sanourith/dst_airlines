#!/bin/bash

helm uninstall mongodb -n airlines
helm uninstall mysql -n airlines
helm uninstall fastapi -n airlines
helm uninstall airflow -n airlines
helm uninstall prometheus --namespace airlines
helm uninstall grafana --namespace airlines 

# kubectl delete -f ./airflow/pv-dags.yaml -n airlines
# kubectl delete -f ./airflow/pvc-dags.yaml -n airlines
kubectl delete -f ./airflow/pv-logs.yaml -n airlines
kubectl delete -f ./airflow/pvc-logs.yaml -n airlines

kubectl delete namespace airlines