FROM python:3.6-alpine

LABEL maintainer "s@muelcolvin.com"

ADD ./requirements.txt /home/root/requirements.txt
RUN pip install -r /home/root/requirements.txt

RUN mkdir /zones
ADD ./example_zones.txt /zones/zones.txt

WORKDIR /home/root
EXPOSE 53/tcp
EXPOSE 53/udp
ADD ./dnserver.py /home/root/dnserver.py
CMD ["./dnserver.py"]
