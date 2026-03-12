FROM python:3.10-slim

WORKDIR /app

EXPOSE 8501

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]