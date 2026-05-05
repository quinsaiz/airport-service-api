FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync \
    --no-install-project \
    # --no-group dev \
    --frozen

COPY . .

RUN addgroup --gid 1000 unprivileged && \
    adduser --uid 1000 --gid 1000 --disabled-password --gecos "" unprivileged && \
    chown -R unprivileged:unprivileged /app

USER unprivileged:unprivileged

ENV PYTHONPATH=/app/app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sleep", "infinity"]
