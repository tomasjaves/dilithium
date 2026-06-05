FROM debian:bookworm-slim AS base

ENV DEBIAN_FRONTEND=noninteractive

# Toolchain + OpenSSL (nistkat in ref/) + Python for hypothesis_tests/ml_detection/benchmarks.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        make \
        libssl-dev \
        python3 \
        python3-pip \
        python3-venv \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd --system --gid ${APP_GID} dilithium \
 && useradd  --system --uid ${APP_UID} --gid ${APP_GID} \
             --home-dir /home/dilithium --create-home --shell /bin/bash \
             dilithium

RUN install -d -o dilithium -g dilithium /opt/venv /src

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

USER dilithium

# Isolated venv so pip install bypasses PEP 668 on Debian.
RUN python3 -m venv "$VIRTUAL_ENV" \
 && pip install --no-cache-dir --upgrade pip

# Install Python deps first for layer caching.
COPY --chown=dilithium:dilithium hypothesis_tests/requirements.txt    /tmp/req-hypothesis.txt
COPY --chown=dilithium:dilithium ml_detection/requirements.txt        /tmp/req-ml.txt
COPY --chown=dilithium:dilithium benchmarks/analysis/requirements.txt /tmp/req-bench.txt
RUN pip install --no-cache-dir \
        -r /tmp/req-hypothesis.txt \
        -r /tmp/req-ml.txt \
        -r /tmp/req-bench.txt

WORKDIR /src
COPY --chown=dilithium:dilithium . /src

# Recreate avx2/ -> ref/ symlinks that .dockerignore stripped from the build context.
RUN set -eu \
 && cd /src/avx2 \
 && for f in \
        fips202.c fips202.h \
        packing.c packing.h \
        params.h \
        randombytes.c randombytes.h \
        sign.h \
        status.c status.h \
        symmetric-shake.c \
        transform.c transform.h; do \
        ln -sf ../ref/$f $f; \
    done \
 && cd /src/avx2/test \
 && for f in \
        cpucycles.c cpucycles.h \
        speed_print.c speed_print.h \
        test_dilithium.c test_mul.c test_speed.c; do \
        ln -sf ../../ref/test/$f $f; \
    done

# Select implementation. ref keeps -O3 portable; avx2 requires x86_64 with AVX2+POPCNT.
ARG IMPL=ref
ENV IMPL=${IMPL}

WORKDIR /src/${IMPL}

RUN make all

CMD ["bash"]
