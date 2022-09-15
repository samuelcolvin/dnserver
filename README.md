# dnserver

[![CI](https://github.com/samuelcolvin/dnserver/workflows/CI/badge.svg?event=push)](https://github.com/samuelcolvin/dnserver/actions?query=event%3Apush+branch%3Amain+workflow%3ACI)
[![Coverage](https://codecov.io/gh/samuelcolvin/dnserver/branch/main/graph/badge.svg)](https://codecov.io/gh/samuelcolvin/dnserver)
[![pypi](https://img.shields.io/pypi/v/dnserver.svg)](https://pypi.python.org/pypi/dnserver)
[![docker](https://img.shields.io/docker/image-size/samuelcolvin/dnserver?sort=date)](https://hub.docker.com/r/samuelcolvin/dnserver/)
[![versions](https://img.shields.io/pypi/pyversions/dnserver.svg)](https://github.com/samuelcolvin/dnserver)
[![license](https://img.shields.io/github/license/samuelcolvin/dnserver.svg)](https://github.com/samuelcolvin/dnserver/blob/main/LICENSE)

Simple DNS server written in python for use in development and testing.

The DNS serves its own records, if none are found it proxies the request to an upstream DNS server
eg. CloudFlare at [`1.1.1.1`](https://www.cloudflare.com/learning/dns/what-is-1.1.1.1/).

You can set up records you want to serve with a custom `zones.toml` file,
see [example_zones.toml](https://github.com/samuelcolvin/dnserver/blob/main/example_zones.toml) an example.

## Installation from PyPI

Install with:

```bash
pip install dnserver
```

Usage:

```bash
dnserver --help
```

(or `python -m dnserver --help`)

For example, to serve a file called `my_zones.toml` file on port `5053`, run:

```bash
dnserver --port 5053 my_zones.toml
```

## Usage with Docker

To use with docker:

```bash
docker run -p 5053:53/udp -p 5053:53/tcp --rm samuelcolvin/dnserver
```

(See [dnserver on hub.docker.com](https://hub.docker.com/r/samuelcolvin/dnserver/))

Or with a custom zone file:

```bash
docker run -p 5053:53/udp -v `pwd`/zones.toml:/zones/zones.toml --rm samuelcolvin/dnserver
```

(assuming you have your zone records at `./zones.toml`,
TCP isn't required to use `dig`, hence why it's omitted in this case.)

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

You can see that the first query took 2ms and returned results from `example_zones.toml`,
the second query took 39ms as dnserver didn't have any records for the domain so had to proxy the query to
the upstream DNS server.
