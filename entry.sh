#!/bin/sh
sudo chown -R garagon:/usr/src/app/

sudo -u garagon "$@"
