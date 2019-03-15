#!/bin/zsh

curl -H 'Content-Type: application/json' -X PUT -d '{ "control_frequency": 60, "horizon_in_steps": 24, "dT_in_seconds": 3600, "model_name": "MaximizePVResidentialBolzano", "repetition": -1, "solver": "ipopt" }' "http://localhost:8080/v1/optimization/start/db0e1be950a9"

sleep 15

curl -X PUT "http://localhost:8080/v1/optimization/stop/db0e1be950a9"

sleep 5

docker-compose stop

