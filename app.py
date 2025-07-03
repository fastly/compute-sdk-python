from wit_world.exports import Reactor as BaseReactor
from wit_world.imports import log
from wit_world.imports import http_req
import sys
import traceback
import io


def init():
    global log_ep
    log_ep = log.endpoint_get("")


def print(msg):
    log.write(log_ep, msg.encode())


def do_serve(req: int, body: int) -> None:
    print("In do_serve")
    print("Test")
    fail


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
