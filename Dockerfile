# Dockerfile
## Base
FROM python:3.11-slim AS builder

ENV ARCH=amd64
ENV PANDOC_VERSION=2.19.2
ENV GET_PANDOC_URL=https://github.com/jgm/pandoc/releases/download
ENV PATH="/opt/venv/bin:/base:$PATH"

ENV ANTLR_VERSION=4.12.0
ENV ANTLR_HOME=/root/.m2/repository/org/antlr/antlr4/
ENV CLASSPATH=$CLASSPATH:$ANTLR_HOME/$ANTLR_VERSION/antlr4-$ANTLR_VERSION-complete.jar

COPY requirements.txt ./

RUN set -ex \
        && apt-get update \
        && apt-get install -y --no-install-recommends \
            openjdk-25-jdk \
            openjdk-25-jre \
            build-essential \
            gcc \
            wget \
        \
        && wget -O pandoc.deb \
            "$GET_PANDOC_URL/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-1-$ARCH.deb" \
        && dpkg -i pandoc.deb \
        \
        && python -m venv /opt/venv \
        \
        && pip install --upgrade pip \
        && pip install -r requirements.txt \
        && antlr4 -v $ANTLR_VERSION

## Build Formatter
WORKDIR /usr/src/formatter

COPY antlr/formatter/formatter.g4 antlr/formatter/formatter.java ./

RUN set -ex \
    && cp $ANTLR_HOME/$ANTLR_VERSION/antlr4-$ANTLR_VERSION-complete.jar ./antlr.jar \
    && antlr4 -v $ANTLR_VERSION formatter.g4 -visitor -no-listener \
    && javac *.java \
    && jar cvfe formatter.jar formatter  *.class ./antlr.jar \
    ;

## Build Sectioner
WORKDIR /usr/src/sectioner

COPY antlr/sectioner/sectioner.g4 antlr/sectioner/sectioner.java ./

RUN set -ex \
    && cp $ANTLR_HOME/$ANTLR_VERSION/antlr4-$ANTLR_VERSION-complete.jar ./antlr.jar \
    && antlr4 -v $ANTLR_VERSION sectioner.g4 -visitor -no-listener \
    && javac *.java \
    && jar cvfe sectioner.jar sectioner  *.class ./antlr.jar \
    ;

## Build Splitter
WORKDIR /usr/src/splitter

COPY antlr/splitter/splitter.g4 antlr/splitter/splitter.java ./

RUN set -ex \
    && cp $ANTLR_HOME/$ANTLR_VERSION/antlr4-$ANTLR_VERSION-complete.jar ./antlr.jar \
    && antlr4 -v $ANTLR_VERSION splitter.g4 -visitor -no-listener \
    && javac *.java \
    && jar cvfe splitter.jar splitter  *.class ./antlr.jar \
    ;

## Build Questionparser
WORKDIR /usr/src/questionparser

COPY antlr/questionparser/questionparser.g4 antlr/questionparser/questionparser.java ./

RUN set -ex \
    && cp $ANTLR_HOME/$ANTLR_VERSION/antlr4-$ANTLR_VERSION-complete.jar ./antlr.jar \
    && antlr4 -v $ANTLR_VERSION questionparser.g4 -visitor -no-listener \
    && javac *.java \
    && jar cvfe questionparser.jar questionparser  *.class ./antlr.jar \
    ;

## Build Endanswers
WORKDIR /usr/src/endanswers

COPY antlr/endanswers/endanswers.g4 antlr/endanswers/endanswers.java ./

RUN set -ex \
    && cp $ANTLR_HOME/$ANTLR_VERSION/antlr4-$ANTLR_VERSION-complete.jar ./antlr.jar \
    && antlr4 -v $ANTLR_VERSION endanswers.g4 -visitor -no-listener \
    && javac *.java \
    && jar cvfe endanswers.jar endanswers  *.class ./antlr.jar \
    ;


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
        redis \
        libreoffice-writer \
        openjdk-25-jdk-headless \
    && mkdir -p /run/daphne \
    ;

# Copy env vars and init script
COPY manage.py ./
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Copy compiled pandoc app
COPY --from=builder /usr/bin/pandoc /usr/local/bin/
COPY --from=builder /root/.cache /root/.cache
COPY --from=builder /opt/venv /opt/venv

# Copy compiled antlr libraries
COPY --from=builder /usr/src /antlr_build/

# Copy app
COPY scorm_writer scorm_writer/
COPY api api/
COPY pandoc pandoc/
COPY restapi restapi/

ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "scorm_writer.asgi:application"]
