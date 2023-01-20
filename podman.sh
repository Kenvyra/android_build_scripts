#!/usr/bin/env sh
DIRECTORY=$(dirname $0)

if ! command -v podman &> /dev/null
then
    echo "podman is not installed. Install it to use this script!"
    exit 1
fi

if ! command -v ccache &> /dev/null
then
    echo "ccache is not installed. Install it to use this script!"
    exit 1
fi

if [ ! -d /tmp/kenvyra_ccache ]
then
    mkdir -p /tmp/kenvyra_ccache
    CCACHE_DIR=/tmp/kenvyra_ccache ccache -M 100GB
fi

KENVYRA_IMAGE=$(podman images | grep kenvyra)

if [ -z "$KENVYRA_IMAGE" ]
then
    echo "Kenvyra image is not built, run $DIRECTORY/build-image.sh"
    exit 1
fi

podman run \
	--rm \
	-it \
	--privileged \
	--ulimit=host \
	--ipc=host \
	--cgroups=disabled \
	--name kenvyra \
	--security-opt label=disable \
	--userns=keep-id \
	--hostname $(hostname) \
	--mount type=tmpfs,tmpfs-size=1G,destination=/build \
	-v $(pwd):/aosp-src \
	-v $(pwd)/out:/aosp-src/out \
	-v /tmp/kenvyra_ccache:/tmp/kenvyra_ccache \
	-e BUILDER_USER="kenvyra" \
	-e BUILDER_EMAIL="dev@kenvyra.xyz" \
	-e USE_CCACHE=1 \
	-e CCACHE_DIR="/tmp/kenvyra_ccache" \
	-e CCACHE_EXEC="/usr/bin/ccache" \
	-e HOME="/build" \
	kenvyra:latest \
	"$@"
