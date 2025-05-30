# Configuration file for the Sphinx documentation builder.
import importlib
import inspect
import logging
import os
import sys

print(f'Running in {os.getcwd()}')

sys.path.insert(0, os.path.abspath('src'))

print(f'Adding to path: {os.path.abspath("../src")}')

# -- Project information

project = 'Thunderbird Accounts'
copyright = '2025, MZLA Technologies Corporation'
author = 'Thunderbird Services'

release = '0.4'
version = '0.4.0'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.linkcode',
    'myst_parser',
    'sphinxcontrib_django',
    'sphinxcontrib.mermaid',
]
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

autosummary_generate = True

autodoc_member_order = 'bysource'
autodoc_default_options = {
    'members': True,
    'show-inheritance': True,
}

# -- Options for HTML output

# html_theme = 'sphinx_rtd_light_dark'
html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'

# Django
django_settings = 'thunderbird_accounts.settings'

# Mermaid
mermaid_d3_zoom = True

source_code_repository = 'https://github.com/thunderbird/thunderbird-pro-services'
source_code_repository_branch = 'main'

# Set APP_ENV to docs, this should disable redis and use a local cache to prevent errors
os.environ['APP_ENV'] = 'docs'
os.environ['SECRET_KEY'] = 'its-just-the-docs'


def linkcode_resolve(domain, info):
    """Resolve our external repo links, including code to highlight the function.
    Code line resolving thanks to: https://github.com/readthedocs/sphinx-autoapi/issues/202"""
    objname = None
    attrname = None
    try:
        if domain != 'py':
            return None
        if not info['module']:
            return None

        mod = importlib.import_module(info['module'])
        if '.' in info['fullname']:
            objname, attrname = info['fullname'].split('.')
            obj = getattr(mod, objname)
            obj = inspect.unwrap(obj)
            try:
                # object is a method of a class
                obj = getattr(obj, attrname)
            except AttributeError:
                # object is an attribute of a class
                return None
        else:
            obj = getattr(mod, info['fullname'])

        try:
            file = inspect.getsourcefile(obj)
            lines = inspect.getsourcelines(obj)
        except TypeError:
            # e.g. object is a typing.Union
            return None

        file = os.path.relpath(file, os.path.abspath('.'))

        # Depending on where the docs are built from this could be slightly different...
        if file.startswith('../'):
            file = file[3:]

        if not file.startswith('src/thunderbird_accounts'):
            print(f'Ignoring {file}')
            # e.g. object is a typing.NewType
            return None

        start, end = lines[1], lines[1] + len(lines[0]) - 1
        return f'{source_code_repository}/tree/{source_code_repository_branch}/{file}#L{start}-L{end}'
    except Exception as e:
        # We'll encounter errors with Django and any magic exceptions (like Model.DoesNotExist.)
        module = info['module']
        if objname:
            module += f'.{objname}'
        if attrname:
            module += f'.{attrname}'
        logging.warning(f'[linkcode_resolve] Could not resolve link for {module}. Error: {e}')
