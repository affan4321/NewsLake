FROM python:3.12-slim
# Unbuffered stdout: without this, print() output only flushes when the process exits
# (stdout isn't a TTY in a container), so Airflow's live task logs look stalled even
# though the script is progressing normally.
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fetch_news.py validate_bronze.py ./
CMD ["python", "fetch_news.py"]
