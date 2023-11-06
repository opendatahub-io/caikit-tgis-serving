FROM registry.access.redhat.com/ubi8/ubi-minimal:latest as poetry-builder

RUN microdnf -y update && \
    microdnf -y install \
        git shadow-utils python39-pip python39-wheel && \
    pip3 install --no-cache-dir --upgrade pip wheel && \
    microdnf clean all

ENV POETRY_VIRTUALENVS_IN_PROJECT=1

WORKDIR /tmp/poetry
COPY pyproject.toml .
COPY poetry.lock .
RUN pip3 install poetry && poetry install


FROM registry.access.redhat.com/ubi8/ubi-minimal:latest as deploy
RUN microdnf -y update && \
    microdnf -y install \
        shadow-utils python39 && \
    microdnf clean all

WORKDIR /caikit

COPY --from=poetry-builder /tmp/poetry/.venv /caikit/
COPY caikit.yml /caikit/config/caikit.yml

ENV VIRTUAL_ENV=/caikit
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN groupadd --system caikit --gid 1001 && \
    adduser --system --uid 1001 --gid 0 --groups caikit \
    --create-home --home-dir /caikit --shell /sbin/nologin \
    --comment "Caikit User" caikit

USER caikit

ENV CONFIG_FILES=/caikit/config/caikit.yml
VOLUME ["/caikit/config/"]

CMD ["python",  "-m", "caikit.runtime"]
