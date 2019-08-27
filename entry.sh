#!/bin/sh
set -x
sudo chown -R garagon: /usr/src/app/

sudo -u garagon "$@"
