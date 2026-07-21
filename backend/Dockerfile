FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system --gid 1001 photonops && adduser --system --uid 1001 --ingroup photonops photonops

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2 \
    && pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY entrypoint.sh ./entrypoint.sh

RUN chown -R photonops:photonops /app
USER 1001

EXPOSE 8000
CMD ["sh", "/app/entrypoint.sh"]
