#!/usr/bin/bash
THREAD_COUNT=$(nproc --all)
repo sync -c --jobs-network=$(( $THREAD_COUNT < 16 ? $THREAD_COUNT : 16 )) -j$THREAD_COUNT --jobs-checkout=$THREAD_COUNT --force-sync --no-clone-bundle --no-tags --force-remove-dirty --optimized-fetch --auto-gc
