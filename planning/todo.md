# Fastly Compute Python SDK - Work Overview

This document provides an overview of the development work planned for the Fastly Compute Python SDK. Each feature links to a detailed design document.

## Core SDK Features

### HTTP Request & Response
- **Full Request Coverage** - [request-response.md](./request-response.md)
- **Full Response Coverage** - [request-response.md](./request-response.md)
- **Trailers** - [trailers.md](./trailers.md)

### Security & Access Control
- **ACL (Blocklists)** - [acl.md](./acl.md)
- **NGWAF (Security)** - [ngwaf.md](./ngwaf.md)

### Geographic & Client Intelligence
- **Geo API** - [geo.md](./geo.md)
- **Device Detection** - [device-detection.md](./device-detection.md)

### Rate Limiting
- **Edge Rate Limiting (ERL)** - [erl.md](./erl.md)

### Data Storage
- **KV Store** - [kv-store.md](./kv-store.md)
- **Secret Store** - [secret-store.md](./secret-store.md)
- **Config Store** - [config-store.md](./config-store.md)

### Caching
- **Core Cache API** - [cache.md](./cache.md)
- **HTTP Cache API** - [http-cache.md](./http-cache.md)
- **Cache Purge** - [cache-purge.md](./cache-purge.md)

### Content Optimization
- **Image Optimization** - [image-opto.md](./image-opto.md)

### Runtime & Diagnostics
- **General Runtime Info** - [runtime-info.md](./runtime-info.md)
- **Logging** - [logging.md](./logging.md)

### API Improvements
- **WIT drop() Support** - [wit-drop.md](./wit-drop.md)
- **Idiomatic Exceptions** - [exceptions.md](./exceptions.md)

## Developer Tooling
- **Fastly-Py Build Tool** - [devtools.md](./devtools.md)
- **Fastly CLI Integration** - [cli-integration.md](./cli-integration.md)

## Documentation
- **Documentation Infrastructure (Sphinx)** - [docs-infra.md](./docs-infra.md)
- **Documentation & Polish** - [docs-polish.md](./docs-polish.md)

## Deferred / Exploratory
- **Async Support** - [async.md](./async.md) (Analysis complete, implementation deferred)
- **Shielding API** - Testing challenges; lower priority
- **Unify Testing with JS** - Out of scope but noted for consideration
- **Numpy 2, Pandas, SciPy** - Gated by Cython compatibility issues
