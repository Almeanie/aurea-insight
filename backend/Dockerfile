FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required by WeasyPrint and data tooling
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    pkg-config \
    libglib2.0-0 \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Cloud Run sets PORT; default 8000 for local)
EXPOSE 8888

# Run the application; use PORT from env for Cloud Run
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8888}"]
