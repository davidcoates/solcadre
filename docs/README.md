# Solcadre Documentation

This directory contains the MkDocs documentation for Solcadre.

## Building Locally

To build the documentation locally, you'll need to install the documentation dependencies:

```bash
pip install -e ".[docs]"
```

Then, from the project root, you can build and serve the documentation:

```bash
mkdocs serve
```

This will start a local development server at `http://127.0.0.1:8000`.

To build static HTML files:

```bash
mkdocs build
```

The built documentation will be in the `site/` directory.

## Read the Docs

This documentation is configured to be automatically built and hosted on Read the Docs. The configuration is in `.readthedocs.yaml` at the project root.
