#!/usr/bin/env bash
#set -e

# Build the containers
docker-compose -f docker-compose-arm.yml down

# Launch the db alone once and give it time to create db user and database
# This is a quickfix to avoid waiting for database to startup on first execution (more details [here](https://docs.docker.com/compose/startup-order/))
#docker-compose -f docker/docker-compose.yml up -d db
#sleep 5
#docker-compose -f docker/docker-compose.dev.yml stop db