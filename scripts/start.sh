#!/bin/bash
image="${1:-registry.local/medicony:latest}"
docker run -d --restart unless-stopped --name medicony --env-file=.env -v ~/medicony-storage/log:/app/log ${image} start