# dnserver

Simple DNS server written in python for use in development and testing.

The DNS serves it's own records, if none are found it proxies the request to and upstream DNS server 
eg. google at `8.8.8.8`.

You can setup the by default if serves some records for `example.com`)

To use with docker:

    docker pull samuelcolvin/dnserver
    docker run -p 5053:53/udp -p 5053:53/tcp --rm dnserver

Or see [docker-compose.yml](docker-compose.yml) for example of using dnserver with docker compose.

To run without docker:

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
