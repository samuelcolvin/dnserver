FROM python:3.10-alpine

RUN mkdir /zones
ADD ./example_zones.toml /zones/zones.toml

ADD ./dnserver /home/root/code/dnserver
ADD ./pyproject.toml /home/root/code
ADD ./LICENSE /home/root/code
ADD ./README.md /home/root/code
RUN pip install /home/root/code
EXPOSE 53/tcp
EXPOSE 53/udp
ENTRYPOINT ["dnserver"]
CMD ["/zones/zones.toml"]
