FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source (exclude venv — dependencies already installed above)
COPY backend/ .

# Create directories for SQLite DB and file storage
RUN mkdir -p data storage/screenshots storage/reports

EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
