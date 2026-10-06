# Version matched to the Python package. No runtime paid services.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
RUN python -m pip install --no-cache-dir playwright==1.63.0 beautifulsoup4==4.14.3 pillow==12.3.0
COPY probe.py /app/probe.py
COPY tests /app/tests
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp/home TZ=Europe/Warsaw
WORKDIR /app
USER pwuser
ENTRYPOINT ["python", "/app/probe.py"]
