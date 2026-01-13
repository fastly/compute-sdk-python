# Documentation Infrastructure Design

## Overview

Proposal for the documentation generation and hosting infrastructure for the Fastly Compute Python SDK.

## Tooling Selection

**Sphinx** with **reStructuredText (RST)**.

**Rationale**:
- The standard for Python documentation (used by Python docs, Requests, Django, etc.).
- Robust support for Python domain (signatures, types, cross-referencing).
- `autodoc` extension provides powerful API documentation generation from docstrings.
- Flexible and extensible.

## Configuration

`conf.py`:

```python
project = 'Fastly Compute Python SDK'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Support for Google/NumPy style docstrings
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_rtd_theme',     # Read the Docs theme (standard choice)
]

html_theme = 'sphinx_rtd_theme'
```

## Structure

```text
docs/
  conf.py
  index.rst           # Landing page
  guides/
    index.rst
    getting-started.rst
    kv-store.rst
    ...
  reference/
    index.rst
    api.rst           # .. automodule:: fastly_compute
```

## Automation

- **GitHub Actions**: Build via `sphinx-build` and deploy to `gh-pages` branch on merge to main.
- **Versioning**: Can use `sphinx-multiversion` or similar if needed.
