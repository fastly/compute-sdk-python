from io import StringIO
from urllib.parse import urlparse

from bottle import route, run, template, Bottle

from wit_world.exports import Reactor as BaseReactor
from wit_world.imports import log, http_req, http_resp, http_body
from wit_world.imports.http_body import read, write
from wit_world.imports.http_resp import send_downstream


app = Bottle()


@app.route('/hello/<name>')
def index(name):
    return template('<b>Hello {{name}}</b>!', name=name)


def init():
    global log_ep
    log_ep = log.endpoint_get("")


def print(msg):
    log.write(log_ep, msg.encode())


# def do_serve(req: int, body: int, app: Bottle) -> None:
#     
# 
# 
#     request_body = read(body, 1024)
#     print(f"Look at your body: {request_body}")
# 
#     response_body = http_body.new()
#     write(response_body, b"bytes!", http_body.WriteEnd.BACK)
#     
#     response = http_resp.new()
#     http_resp.header_append(response, b"Foof", b"Barf")
#     send_downstream(response, response_body, True)


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

    response_body = http_body.new()  # TODO: Maybe stream.
    url = urlparse(http_req.uri_get(req, 2048))
    environ = {"REQUEST_METHOD": http_req.method_get(req, 12),
               "PATH_INFO": url.path,
               "QUERY_STRING": url.query,
               "SERVER_NAME": url.hostname,
               "SERVER_PORT": url.port,
               "wsgi.errors": StringIO()  # TODO: Replace with a file-like wrapper around the log endpoint.
    }
    print(f"{environ}")
    for body_chunk in app(environ, start_response):
        write(response_body, body_chunk, http_body.WriteEnd.BACK)
    send_downstream(response, response_body, False)


class Reactor(BaseReactor):
    def serve(self, req: int, body: int) -> None:
        init()
        try:
            serve_wsgi_request(req, body, app)
        except Exception as e:
            # outf = Stdout()
            print(f"Exception {e}")
            print("--- Traceback Follows ---")
            try:
                tb = e.__traceback__
                current_tb = tb
                while current_tb:
                    frame = current_tb.tb_frame
                    print(f"  File: {frame.f_code.co_filename}, "
                          f"Function: {frame.f_code.co_name}, "
                          f"Line: {frame.f_lineno}")
                    current_tb = current_tb.tb_next
            except Exception as e2:
                print(f"print_exc failed {e2}")
