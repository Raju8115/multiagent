FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install flask ibm_db python-dotenv

EXPOSE 5000

CMD ["python3", "app.py"]
