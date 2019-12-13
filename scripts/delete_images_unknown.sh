#!/usr/bin/env bash
set -e

sudo docker rmi -f $(sudo docker images | grep "^<none>" | awk "{print $3}")