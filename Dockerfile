FROM python:3.8-alpine
ENV PYTHONUNBUFFERED=1
RUN mkdir /code
WORKDIR /code
COPY requirements/ /requirements/

RUN apk add --no-cache --virtual .build-deps \
        g++ \
    && pip install -r /requirements/production.txt \
    && apk del .build-deps

COPY . /code/