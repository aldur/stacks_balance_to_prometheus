FROM python:3.12.8-slim AS base

# Setup env
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

FROM base AS python-deps

RUN pip install --no-cache-dir poetry==1.8.5

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

FROM base AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1

ARG UID=1001
ARG GID=1001

# Create and switch to a new user
RUN groupadd -f -g "${GID}" appuser \
    && useradd --create-home --no-log-init -o -u "${UID}" -g "${GID}" appuser

WORKDIR /home/appuser

COPY --from=python-deps /.venv ./.venv

COPY main.py main.py

RUN chown -R "${UID}":"${GID}" main.py

USER appuser

EXPOSE 8081

# Run the application
ENTRYPOINT ["/home/appuser/.venv/bin/python", "main.py"]
