# The cell generator (cellweaver) with the tools its --verify and --simulate need.
# Built on the course image dd2-layout-tools (Magic 8.3.684, Netgen, ngspice 47):
#   docker build -t dd2-layout-tools ../DD2_Project1_student_pack/container
#   docker build -t dd2-cellweaver -f docker/cellweaver.Dockerfile cellweaver
# The build context is the cellweaver folder (it holds requirements.lock).
FROM dd2-layout-tools

# Netgen 1.5.323 is the version the generator was validated with
# (cellweaver docs/technology.md). The course image's Netgen 1.5.132 cannot
# read the extracted netlist, so LVS fails before it compares anything.
RUN git init /tmp/netgen && cd /tmp/netgen \
    && git remote add origin https://github.com/RTimothyEdwards/netgen.git \
    && git fetch --depth 1 origin e1528a797cdb155d6ebf8d91c5a55ed7d1713156 \
    && git checkout FETCH_HEAD \
    && ./configure && make -j"$(nproc)" && make install \
    && rm -rf /tmp/netgen

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      python3-venv python3-pip && rm -rf /var/lib/apt/lists/*
COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/cwvenv && /opt/cwvenv/bin/pip install --no-cache-dir -r /tmp/requirements.lock

# OpenSTA, for the worst delay of each mapped design (scripts/sta_delay.py).
# It links the CUDD BDD package, which Ubuntu does not ship, so CUDD is built
# first (autoreconf -fi: the checked-in build files ask for an old aclocal).
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      cmake swig libeigen3-dev zlib1g-dev libfl-dev libgtest-dev libreadline-dev \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/The-OpenROAD-Project/cudd.git /tmp/cudd \
    && cd /tmp/cudd && autoreconf -fi \
    && ./configure --prefix=/opt/cudd && make -j"$(nproc)" && make install \
    && rm -rf /tmp/cudd
RUN git clone --depth 1 https://github.com/The-OpenROAD-Project/OpenSTA.git /tmp/opensta \
    && cd /tmp/opensta && mkdir build && cd build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release -DCUDD_DIR=/opt/cudd \
    && make -j"$(nproc)" && make install \
    && rm -rf /tmp/opensta
