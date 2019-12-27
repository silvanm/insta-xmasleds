FROM python:3.7

WORKDIR /code

ADD . /code

RUN pip install -r requirements-webserver.txt

EXPOSE 8000

CMD uvicorn webserver:app --host 0.0.0.0 --port 8000
