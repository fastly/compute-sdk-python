from wit_world.exports import Reactor as BaseReactor
from wit_world.imports.log import write, endpoint_get


class Reactor(BaseReactor):
    def serve(self, req: int, body: int) -> None:
        handle = endpoint_get("")
        write(handle, b"orly?")
