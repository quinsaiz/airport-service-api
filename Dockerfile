FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app
COPY ./entrypoint.sh /entrypoint.sh

RUN addgroup --gid 1000 unprivileged && \
    adduser --uid 1000 --gid 1000 --disabled-password --gecos "" unprivileged && \
    chown -R unprivileged:unprivileged /app

USER unprivileged:unprivileged

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
