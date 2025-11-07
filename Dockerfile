# Dockerfile
## Base
FROM python:3.11-slim AS builder

ENV ARCH=amd64
ENV PATH="/opt/venv/bin:/base:$PATH"

COPY requirements.txt ./

RUN set -ex \
        && apt-get update \
        && apt-get install -y --no-install-recommends \
            build-essential \
            gcc \
            wget \
        \
        && python -m venv /opt/venv \
        \
        && pip install --upgrade pip \
        && pip install -r requirements.txt



# Release
FROM python:3.11-slim AS release

LABEL maintainer=courseproduction@bcit.ca

ENV PYTHONUNBUFFERED=1
ENV PATH=/code:/opt/venv/bin:$PATH
ARG VERSION
ENV VERSION=${VERSION:-0.0.0}

WORKDIR /code

RUN set -ex \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        redis;

# Copy env vars and init script
COPY manage.py ./
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY --from=builder /root/.cache /root/.cache
COPY --from=builder /opt/venv /opt/venv

# Copy app
COPY scorm_writer scorm_writer/
COPY api api/

ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--workers", "2", "scorm_writer.asgi:application"]
