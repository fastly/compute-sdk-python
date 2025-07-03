from wit_world.exports import Reactor as BaseReactor
from wit_world.imports import log, http_req, http_resp, http_body
from wit_world.imports.http_body import read, write
from wit_world.imports.http_resp import send_downstream
import sys
import traceback
import io
import art


def init():
    global log_ep
    log_ep = log.endpoint_get("")


def print(msg):
    log.write(log_ep, msg.encode())


def do_serve(req: int, body: int) -> None:
    # resp.set_status(418)
    request_body = read(body, 1024)
    print(f"Look at your body: {request_body}")

    response_body = http_body.new()
    write(response_body, b"bytes!", http_body.WriteEnd.BACK)
    
    response = http_resp.new()
    send_downstream(response, response_body, False)

class Reactor(BaseReactor):
    def serve(self, req: int, body: int) -> None:
        init()
        try:
            do_serve(req, body)
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
