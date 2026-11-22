# Prüfimage für die Integrationsprüfung (G3). Enthält nur die gepinnten Prüfwerkzeuge der
# Plattform-API, keinen Quelltext und keine Zugangsdaten. Läuft mit --network none.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
COPY platform_api/requirements.txt platform_api/requirements-dev.txt /tmp/req/
RUN pip install --no-cache-dir -r /tmp/req/requirements-dev.txt PyYAML==6.0.3 && rm -rf /tmp/req
USER 65534:65534
WORKDIR /tmp
