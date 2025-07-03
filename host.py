from hello_host import Root
from wasmtime import Config, Engine, Store

config = Config()
config.cache = True
engine = Engine(config)
store = Store(engine)
hello = Root(store)
print(f"component says: {hello.hello(store)}")
