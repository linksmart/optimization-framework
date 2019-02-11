#!/usr/bin/env bash
set -e

sudo docker rmi -f $(docker images | grep "^<none>" | awk "{print $3}")