FROM python:3.12-slim

WORKDIR /workspace

# Install system dependencies needed for compiling postgres drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Append psycopg2-binary so the container can connect to PostgreSQL
RUN echo "psycopg2-binary==2.9.9" >> requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
