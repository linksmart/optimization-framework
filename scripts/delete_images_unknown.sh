#!/usr/bin/env bash
set -e

docker rmi $(docker images | grep "^<none>" | awk "{print $3}")