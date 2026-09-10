FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py dashboard.py pipeline_guide.py data_explorer.py airflow_client.py pipeline_viz.py data_layer.py ui_helpers.py sample_data.json .
COPY .streamlit/ ./.streamlit/
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
