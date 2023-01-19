FROM registry.fedoraproject.org/fedora-minimal:37

RUN microdnf install -y \
	git \
	bison \
	which \
	ccache \
	perl \
	patchutils \
	automake \
	autoconf \
	binutils \
	diffutils \
	flex \
	gcc \
	gcc-c++ \
	gdb \
	glibc-devel \
	libtool \
	pkgconf \
	pkgconf-m4 \
	pkgconf-pkg-config \
	strace \
	bzip2 \
	python3 \
	make \
	openssl \
	openssl-devel \
	curl \
	procps-ng \
	openssh-clients \
	freetype \
	freetype-devel \
	rsync \
	xz \
	tar \
	ncurses-libs

RUN ln -s /usr/lib64/libncurses.so.6 /usr/lib64/libncurses.so.5 && \
	ln -s /usr/lib64/libtinfo.so.6 /usr/lib64/libtinfo.so.5

RUN curl http://commondatastorage.googleapis.com/git-repo-downloads/repo > /usr/bin/repo && \
	chmod +x /usr/bin/repo

COPY entrypoint.sh /usr/bin/

ENTRYPOINT ["/usr/bin/entrypoint.sh"]
