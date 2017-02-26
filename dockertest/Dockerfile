FROM python:3.6-alpine

LABEL maintainer "s@muelcolvin.com"

RUN apk --update --no-cache add gcc musl-dev \
 && rm -rf /var/cache/apk/*

ADD ./requirements.txt /home/root/requirements.txt
RUN pip install -r /home/root/requirements.txt

WORKDIR /home/root
ADD ./run.py /home/root/run.py
CMD ["./run.py"]
