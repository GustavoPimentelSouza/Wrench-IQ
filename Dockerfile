FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY domain/ ./domain/
COPY application/ ./application/
COPY adapters/ ./adapters/
COPY infrastructure/ ./infrastructure/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY tests/ ./tests/
COPY pytest.ini .
COPY conftest.py .
COPY .env.test .
COPY main.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
