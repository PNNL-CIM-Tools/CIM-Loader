"""Shared RDF format detection.

Maps file extensions to content types used across all uploaders. Any
uploader-specific translation (e.g. the n10s 'RDF/XML' alias for Neo4j)
happens in the uploader itself, keyed off the content type returned here.
"""

_EXT_TO_CONTENT_TYPE = {
    'xml':      'application/rdf+xml',
    'rdf':      'application/rdf+xml',
    'ttl':      'text/turtle',
    'turtle':   'text/turtle',
    'nt':       'application/n-triples',
    'ntriples': 'application/n-triples',
    'nq':       'application/n-quads',
    'nquads':   'application/n-quads',
    'jsonld':   'application/ld+json',
    'json-ld':  'application/ld+json',
    'trig':     'application/trig',
}


def content_type_from_filename(filename: str) -> str:
    """Return the RDF content type for a filename based on its extension.

    Raises ValueError if the extension is not a recognized RDF format.
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in _EXT_TO_CONTENT_TYPE:
        supported = ', '.join(sorted({'.' + e for e in _EXT_TO_CONTENT_TYPE}))
        raise ValueError(
            f"Unsupported RDF format: {filename!r}. Supported extensions: {supported}"
        )
    return _EXT_TO_CONTENT_TYPE[ext]


def content_type_from_url(url: str) -> str:
    """Return the RDF content type for a URL based on its path extension.

    Strips query string and fragment, then reuses `content_type_from_filename`.
    """
    path = url.split('?', 1)[0].split('#', 1)[0]
    return content_type_from_filename(path)
