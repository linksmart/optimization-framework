#!/bin/sh

chown -R garagon: /usr/src/app/

sudo -i -u garagon "$@"