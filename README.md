# dnserver

Simple DNS server written in python for use in development and testing.

Can be used in docker, see [docker-compose.yml](docker-compose.yml) for example.

To run without docker:

    PORT=5053 ZONE_FILE='./example_zones.txt' UPSTREAM=8.8.8.8 ./dnserver.py
