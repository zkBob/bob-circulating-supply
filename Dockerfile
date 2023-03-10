FROM python:3.9-alpine

RUN apk update && apk upgrade
# GCC.
RUN apk add --no-cache --virtual .build-deps gcc musl-dev

RUN python -m pip install --upgrade pip
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Remove gcc.
RUN apk del .build-deps
# Remove cache.
RUN python -m pip cache purge

WORKDIR /app

COPY app.py .
COPY abi abi
COPY bobstats bobstats
COPY bobvault bobvault
COPY supply supply
COPY utils utils

CMD ["python", "app.py"]
