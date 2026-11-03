FROM registry.access.redhat.com/ubi9/ubi-minimal:latest as poetry-builder

RUN microdnf -y update && \
    microdnf -y install \
        git shadow-utils python3.12-pip python-wheel \
        gcc python3.12-devel && \
    pip3.12 install --no-cache-dir --upgrade pip wheel && \
        microdnf clean all

ENV POETRY_VIRTUALENVS_IN_PROJECT=1

WORKDIR /caikit
COPY pyproject.toml .
COPY poetry.lock .
RUN pip3.12 install poetry && poetry install --no-root


FROM registry.access.redhat.com/ubi9/ubi-minimal:latest as deploy
RUN microdnf -y update && \
    microdnf -y install \
        shadow-utils python3.12 && \
    microdnf clean all

WORKDIR /caikit

COPY --from=poetry-builder /caikit/.venv /caikit/.venv
COPY caikit.yml /caikit/config/caikit.yml

ENV VIRTUAL_ENV=/caikit/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Security overrides on top of the poetry venv. The resolved poetry graph
# (caikit 0.28.1 -> datasets 3.3.2) caps some packages below the versions
# RHAI CVE trackers require (datasets caps fsspec<=2024.12.0), and fastapi
# >= 0.141 no longer pulls ujson through its extras. poetry.lock is kept
# aligned with these pins wherever the dependency graph allows.
RUN /caikit/.venv/bin/pip install --no-cache-dir "urllib3>=2.8.0"

RUN /caikit/.venv/bin/pip install --no-cache-dir \
    "fastapi>=0.134.0" "starlette>=1.3.1" "aiohttp>=3.14.3,<4.0.0" "python-dotenv==1.2.2" "ujson>=5.12.1" \
    "certifi>=2026.10.23" "pillow>=13.0.0" "fsspec>=2026.6.0" "anyio>=4.14.2" "dnspython>=2.9.0" "filelock>=4.2.1"

RUN groupadd --system caikit --gid 1001 && \
    adduser --system --uid 1001 --gid 0 --groups caikit \
    --create-home --home-dir /caikit --shell /sbin/nologin \
    --comment "Caikit User" caikit

USER caikit

ENV CONFIG_FILES=/caikit/config/caikit.yml
VOLUME ["/caikit/config/"]

CMD ["python",  "-m", "caikit.runtime"]
