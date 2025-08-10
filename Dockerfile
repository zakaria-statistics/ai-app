FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure files dir exists
RUN mkdir -p /app/files

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
