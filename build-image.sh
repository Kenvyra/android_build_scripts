#!/usr/bin/env sh
DIRECTORY=$(dirname $0)

if ! command -v podman &> /dev/null
then
    echo "podman is not installed. Install it to use this script!"
    exit 1
fi

podman build -t kenvyra:latest $DIRECTORY
