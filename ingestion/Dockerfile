FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fetch_news.py validate_bronze.py ./
CMD ["python", "fetch_news.py"]
