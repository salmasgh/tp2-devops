# ---- build stage: install deps into a virtualenv ----
FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --upgrade pip setuptools && pip install -r requirements.txt

# ---- runtime stage: minimal, non-root ----
FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/salmasgh/tp2-devops" \
      org.opencontainers.image.description="TP2 DevOps - Payment API (FastAPI + OpenTelemetry)"
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /srv
COPY app ./app
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,sys;urllib.request.urlopen('http://127.0.0.1:8000/health');sys.exit(0)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
