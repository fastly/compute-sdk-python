import platform

from bottle import Bottle

from fastly_compute.wsgi import WsgiHttpIncoming

app = Bottle()


@app.route("/")
def index():
    version = platform.python_version()
    return f"Welcome to Python {version} on Fastly Compute!"


# Create the HTTP handler using WSGI; this adapts the fastly compute
# platform to the WSGI standard for use with a variety of frameworks.
HttpIncoming = WsgiHttpIncoming(app)
