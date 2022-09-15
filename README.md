# dnserver

Simple DNS server written in python for use in development and testing.

The DNS serves its own records, if none are found it proxies the request to an upstream DNS server
eg. CloudFlare at [`1.1.1.1`](https://1.1.1.1/).

You can set up records you want to serve with a custom `zones.toml` file,
see [example_zones.toml](example_zones.toml) for the format.

To use with docker:

    docker run -p 5053:53/udp -p 5053:53/tcp --rm samuelcolvin/dnserver

(See [dnserver on hub.docker.com](https://hub.docker.com/r/samuelcolvin/dnserver/))

Or with a custom zone file

    docker run -p 5053:53/udp -v `pwd`/zones.toml:/zones/zones.toml --rm samuelcolvin/dnserver

(assuming you have your zone records at `./zones.toml`,
TCP isn't required to use `dig`, hence why it's omitted in this case.)

Or see [docker-compose.yml](docker-compose.yml) for example of using dnserver with docker compose.
It demonstrates using dnserver as the DNS server for another container which then tries to make DNS queries
for numerous domains.

To run without docker (assuming you have `dnslib==0.9.7` and python 3.6 installed):

    PORT=5053 ZONE_FILE='./example_zones.txt' ./dnserver.py

You can then test (either of the above) with

```shell
~ ➤  dig @localhost -p 5053 example.com MX
...
;; ANSWER SECTION:
example.com.		300	IN	MX	5 whatever.com.
example.com.		300	IN	MX	10 mx2.whatever.com.
example.com.		300	IN	MX	20 mx3.whatever.com.

;; Query time: 2 msec
;; SERVER: 127.0.0.1#5053(127.0.0.1)
;; WHEN: Sun Feb 26 18:14:52 GMT 2017
;; MSG SIZE  rcvd: 94

~ ➤  dig @localhost -p 5053 tutorcruncher.com MX
...
;; ANSWER SECTION:
tutorcruncher.com.	299	IN	MX	10 aspmx2.googlemail.com.
tutorcruncher.com.	299	IN	MX	5 alt1.aspmx.l.google.com.
tutorcruncher.com.	299	IN	MX	5 alt2.aspmx.l.google.com.
tutorcruncher.com.	299	IN	MX	1 aspmx.l.google.com.
tutorcruncher.com.	299	IN	MX	10 aspmx3.googlemail.com.

;; Query time: 39 msec
;; SERVER: 127.0.0.1#5053(127.0.0.1)
;; WHEN: Sun Feb 26 18:14:48 GMT 2017
;; MSG SIZE  rcvd: 176
```

You can see that the first query took 2ms and returned results from [example_zones.toml](example_zones.toml),
the second query took 39ms as dnserver didn't have any records for the domain so had to proxy the query to
the upstream DNS server.
