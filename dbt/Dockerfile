FROM python:3.12-slim
WORKDIR /usr/app
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir dbt-postgres
COPY . .
ENTRYPOINT ["dbt"]
CMD ["--help"]
