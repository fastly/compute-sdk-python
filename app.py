from urllib.parse import urlparse

import art
import bottle
from bottle import template, Bottle

from wit_world.exports import Reactor as BaseReactor
from wit_world.imports import log, http_req, http_resp, http_body
from wit_world.imports.http_resp import send_downstream


app = Bottle()
app.catchall = False  # bottle backtrace causes issues, use our own


@app.route("/hello/<name>")
def index(name):
    return template("Hello <pre>{{name}}</pre>", name=art.text2art(name))


def print(*args):
    # hack to allow print locally; so far, monkeypatching
    # sys.stdout/sys.stderr hasn't panned out, so more
    # research required.
    log.write(log_ep, " ".join(args).encode())


def init():
    global log_ep
    log_ep = log.endpoint_get("")

    # enables a bit more debug logging from the framework
    bottle.debug(True)


class Stderr:
    def write(self, data: str):
        print(f"wsgi-error: {data}")

    def flush(self):
        pass


def serve_wsgi_request(req, body, app):
    """Pass a WSGI application a single request, and adapt what it hands us back
    to the Fastly API."""

    response = http_resp.new()

    def start_response(status: str, headers: list[tuple], exc_info=None):
        code, _description = status.split(" ", 1)
        http_resp.status_set(response, int(code))
        for header, value in headers:
            print(f"Header: {header}. Value: {value}.")
            http_resp.header_append(response, header.encode(), value.encode())
        return lambda x: None  # TODO: Return a real write().

    response_body = http_body.new()
    url = urlparse(http_req.uri_get(req, 2048))
    environ = {
        "REQUEST_METHOD": http_req.method_get(req, 12),
        "PATH_INFO": url.path,
        "QUERY_STRING": url.query,
        "SERVER_NAME": url.hostname,
        "SERVER_PORT": str(url.port),
        "wsgi.errors": Stderr(),
    }
    print(f"{environ}")
    for body_chunk in app(environ, start_response):
        # TODO: this would be a good place to stream but for now we just
        #       write to the buffer and send once the handler is done.
        http_body.write(response_body, body_chunk, http_body.WriteEnd.BACK)
    send_downstream(response, response_body, False)


class Reactor(BaseReactor):
    def serve(self, req: int, body: int) -> None:
        init()
        try:
            serve_wsgi_request(req, body, app)
        except Exception as e:
            # outf = Stdout()
            try:
                print(f"Exception {type(e).__name__} - {e}")
                print("--- Traceback Follows ---")

                current_tb = e.__traceback__
                while current_tb:
                    frame = current_tb.tb_frame
                    print(
                        f"  File: {frame.f_code.co_filename}, "
                        f"Function: {frame.f_code.co_name}, "
                        f"Line: {frame.f_lineno}"
                    )
                    current_tb = current_tb.tb_next
            except Exception as e2:
                print(f"print_exc failed {e2}")
