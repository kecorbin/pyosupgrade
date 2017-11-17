FROM python:2.7-onbuild
COPY . /usr/src/app
# https://github.com/mher/flower/issues/735
WORKDIR /tmp
RUN git clone https://github.com/kecorbin/flower
WORKDIR /tmp/flower
RUN python setup.py install
WORKDIR /usr/src/app
CMD gunicorn app:app -b 0.0.0.0:8000