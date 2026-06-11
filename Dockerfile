FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system appuser && adduser --system --no-create-home --ingroup appuser appuser

RUN chown -R appuser:appuser /app

RUN apt-get update && apt-get upgrade -y perl-base

USER appuser

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]