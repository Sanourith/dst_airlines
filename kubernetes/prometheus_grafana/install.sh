#! /bin/bash

# Prometheus stack :
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus -n airlines
# helm uninstall prometheus

# Grafana stack : 
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install grafana grafana/grafana --namespace airlines
# helm install grafana grafana/grafana -f values.yaml -n airlines

kubectl apply -f grafana.yaml -n airlines

# kubectl port-forward svc/prometheus-server 9090:80 -n airlines 
# kubectl port-forward svc/grafana 3000:80 -n airlines 
# helm delete my-release

############
### LOGS ###
############
# admin  ---  prom-operator