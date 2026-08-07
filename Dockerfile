FROM python:3.12-slim

WORKDIR /app

# System deps needed to build/run psycopg2 and scikit-learn wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generated CSV outputs should live on a mounted volume, not in the image
VOLUME ["/app/outputs"]

EXPOSE 8002

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
