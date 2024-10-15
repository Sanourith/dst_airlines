#! /bin/bash

# Prometheus stack :
helm uninstall prometheus --namespace airlines
# helm uninstall prometheus

# Grafana stack : 
helm uninstall grafana --namespace airlines 
# helm delete my-release