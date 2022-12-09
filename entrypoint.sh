#!/usr/bin/bash
set -o allexport
cd /aosp-src
source build/envsetup.sh
bash -c "$@"
