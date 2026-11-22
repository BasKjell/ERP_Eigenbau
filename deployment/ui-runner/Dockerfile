# Prüfbrowser für die Klickprüfung der FLOWAGENTS (headless Chromium über Playwright).
# Läuft nur im internen Netz flow-agents-ui gegen die Vorschau; kein Internet, read-only.
#   docker build -t flow-agents-ui-runner:1 deployment/ui-runner
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble
RUN pip install --no-cache-dir playwright==1.55.0
COPY runner.py /opt/flow_ui_runner.py
USER pwuser
ENTRYPOINT ["python", "/opt/flow_ui_runner.py"]
