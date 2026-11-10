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
