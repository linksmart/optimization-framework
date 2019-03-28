#!/bin/zsh


# start
curl -H 'Content-Type: application/json' -X PUT -d '{ "control_frequency": 60, "horizon_in_steps": 24, "dT_in_seconds": 3600, "model_name": "CarParkModel", "repetition": 1, "solver": "ipopt" }' "http://localhost:8080/v1/optimization/start/c4688ade67fb"

sleep 15

# stop
curl -X PUT "http://localhost:8080/v1/optimization/stop/c4688ade67fb"

sleep 5

docker-compose stop

