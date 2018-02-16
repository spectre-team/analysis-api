FROM python:3.6-slim

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

ENV FLASK_APP api.py

CMD ["flask", "run", "-p", "80", "-h", "0.0.0.0"]
