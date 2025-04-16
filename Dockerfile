FROM python:3.11-slim

ENV POETRY_VERSION=1.8.2

RUN apt-get update && \
    apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

WORKDIR /app/backend

COPY backend/ .

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction

CMD ["python", "app.py"]
