#!/bin/bash
image="${1:-registry.local/medicony:latest}"
docker run -it --env-file=.env -v ~/medicony-storage/log:/app/log ${image} start