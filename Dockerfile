FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps (psycopg2 / cryptography / paramiko)
RUN apt-get update -y \
  && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock.txt ./

# Prefer lock if present; fallback to flexible ranges.
RUN python -m pip install --upgrade pip setuptools wheel \
  && if [ -f requirements.lock.txt ]; then python -m pip install -r requirements.lock.txt; else python -m pip install -r requirements.txt; fi

COPY . .

EXPOSE 2083

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "2083", "--workers", "2"]

