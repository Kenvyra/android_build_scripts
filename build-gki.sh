#!/usr/bin/env bash

if [[ -z "${1}" ]]; then
    echo "No device specified."
    exit 1
fi

DIRECTORY=$(dirname $0)

$DIRECTORY/podman.sh "lunch kenvyra_$1-userdebug; TARGET_BOARD_PLATFORM=$1 OUT_DIR=/aosp-src/out/msm-kernel-$1 LTO=thin ./kernel_platform/build/android/prepare_vendor.sh $1 gki"
