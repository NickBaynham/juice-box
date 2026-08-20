FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir pdm

COPY pyproject.toml pdm.lock ./
RUN pdm install --prod --no-self

COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN pdm install --prod --no-editable

EXPOSE 8000

CMD ["pdm", "run", "python", "-m", "juicebox"]
