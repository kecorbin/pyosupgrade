FROM python:2.7-onbuild
COPY . /usr/src/app
WORKDIR /usr/src/app
CMD gunicorn app:app -b 0.0.0.0:8000