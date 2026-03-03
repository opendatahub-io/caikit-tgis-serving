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

RUN /caikit/.venv/bin/pip install --no-cache-dir "urllib3>=2.6.0"

RUN /caikit/.venv/bin/pip install --no-cache-dir \
    "fastapi==0.123.7" "starlette>=0.49.1,<0.51.0" "aiohttp>=3.13.3,<4.0.0"
RUN groupadd --system caikit --gid 1001 && \
    adduser --system --uid 1001 --gid 0 --groups caikit \
    --create-home --home-dir /caikit --shell /sbin/nologin \
    --comment "Caikit User" caikit

USER caikit

ENV CONFIG_FILES=/caikit/config/caikit.yml
VOLUME ["/caikit/config/"]

CMD ["python",  "-m", "caikit.runtime"]
