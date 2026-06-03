# Fastly Compute Python Starter Kit

A basic starter kit for running Python applications on Fastly's Compute platform using the [WSGI](https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface) interface and the [Bottle](https://bottlepy.org/) web framework.

## Requirements

* [Fastly CLI](https://github.com/fastly/cli)
* [Python >= 3.12](https://www.python.org/)
* [uv](https://docs.astral.sh/uv/)

## Development

To build and deploy this application:

```bash
fastly compute build
fastly compute deploy
```
