FROM python:3.13

WORKDIR /app

COPY app.py .

RUN pip install --no-cache-dir flask

EXPOSE 8080

# Intentionally runs as root — VULN-01 demonstration
# DO NOT use in production
CMD ["python", "app.py"]
