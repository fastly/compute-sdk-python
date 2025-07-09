This is the experimental beginning of a Python SDK for [Fastly Compute](https://www.fastly.com/products/edge-compute).

# Status

Currently, this demonstrates…

* Building arbitrary pure Python into a component
* Creating Python bindings from Fastly's WIT files
* Hosting arbitrary web frameworks by adapting Fastly's API, through those bindings, to WSGI

# Caveats

* Any native Python modules need to be compiled against WASI. Few are at the moment. However, [Joel has done some](https://github.com/dicej/wasi-wheels/releases/), and the changes needed aren't extensive.
* Most popular web frameworks we tried [wouldn't work because they depended on zlib](https://github.com/bytecodealliance/componentize-py/issues/96) and other native-code compression stdlibs which haven't been compiled against WASI yet. Moving componentize-py to a new Python may help, as [WASIp1 is now a Tier 2 supported platform](https://peps.python.org/pep-0011/#tier-2).
* It crashes every time something tries to write to stdout or stderr. It may be that those aren't in the preopens; adding those to the preopens should be possible with changes to Viceroy. We're also using `--stub-wasi` at the moment, which means things like `fd_write` are coded to immediately trap; that probably doesn't help. Finally, it may be possible to monkeypatch in Python and redirect them to a logging endpoint, but our initial attempts were unsuccessful.

# Install Dependencies

1. `pip install componentize-py`
2. `pip install -r requirements.txt`
3. Install [Viceroy](https://github.com/fastly/Viceroy). Make sure you have [a branch with up-to-date WIT files](https://github.com/fastly/Viceroy/tree/sunfishcode/sync-wit) so it can run components.

# Build and Run

1. `make serve`
2. Visit http://127.0.0.1:7676/hello/fred in a browser.

You are seeing Bottle, a simple Python web framework, run on a Fastly Compute worker!
