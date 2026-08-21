"""GraphDB database connection.

Ontotext GraphDB is an enterprise RDF triplestore. It speaks standard
RDF4J protocol for query and bulk upload (`/repositories/<id>` +
`/repositories/<id>/statements`) and exposes a GraphDB-specific REST API
for repository management (`/rest/repositories`).

The connection talks to a single repository, configured via the
`CIMG_URL` environment variable, which is expected to point at the
SPARQL endpoint form:

    http://localhost:7200/repositories/<repo_id>

`configure()` auto-creates the repository if it doesn't already exist,
so a fresh `docker-compose up -d graphdb` followed by a first upload
"just works" without a workbench round-trip.
"""

from __future__ import annotations

import logging

import requests

from cimgraph.databases import get_cim_profile, get_iec61970_552, get_namespace, get_url
from cimloader.databases import ConnectionInterface, QueryResponse
from cimloader.databases._config_utils import clear_cim_config_cache
from SPARQLWrapper import JSON, POST, SPARQLWrapper

_log = logging.getLogger(__name__)


# RDF4J TTL template for a default GraphDB repository. The GraphDB REST
# API expects this shape as the `config` multipart field. Parameters
# match GraphDB 11.x defaults (rdfsplus-optimized ruleset, file-repository).
_REPO_CONFIG_TEMPLATE = """\
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rep:  <http://www.openrdf.org/config/repository#> .
@prefix sail: <http://www.openrdf.org/config/sail#> .

<#{repo_id}> a rep:Repository ;
    rep:repositoryID "{repo_id}" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        <http://www.openrdf.org/config/repository/sail#sailImpl> [
            <http://www.ontotext.com/config/graphdb#base-URL> "http://example.org/owlim#" ;
            <http://www.ontotext.com/config/graphdb#check-for-inconsistencies> "false" ;
            <http://www.ontotext.com/config/graphdb#defaultNS> "" ;
            <http://www.ontotext.com/config/graphdb#disable-sameAs> "true" ;
            <http://www.ontotext.com/config/graphdb#enable-context-index> "false" ;
            <http://www.ontotext.com/config/graphdb#enable-fts-index> "false" ;
            <http://www.ontotext.com/config/graphdb#enable-literal-index> "true" ;
            <http://www.ontotext.com/config/graphdb#enablePredicateList> "true" ;
            <http://www.ontotext.com/config/graphdb#entity-id-size> "32" ;
            <http://www.ontotext.com/config/graphdb#entity-index-size> "10000000" ;
            <http://www.ontotext.com/config/graphdb#imports> "" ;
            <http://www.ontotext.com/config/graphdb#in-memory-literal-properties> "true" ;
            <http://www.ontotext.com/config/graphdb#query-limit-results> "0" ;
            <http://www.ontotext.com/config/graphdb#query-timeout> "0" ;
            <http://www.ontotext.com/config/graphdb#read-only> "false" ;
            <http://www.ontotext.com/config/graphdb#repository-type> "file-repository" ;
            <http://www.ontotext.com/config/graphdb#ruleset> "rdfsplus-optimized" ;
            <http://www.ontotext.com/config/graphdb#storage-folder> "storage" ;
            <http://www.ontotext.com/config/graphdb#throw-QueryEvaluationException-on-timeout> "false" ;
            sail:sailType "graphdb:Sail"
        ]
    ] ;
    rdfs:label "CIM-Loader repository" .
"""


class GraphDBConnection(ConnectionInterface):
    def __init__(self) -> None:
        clear_cim_config_cache()

        self.sparql_obj = None
        self.url = get_url()
        self.namespace = get_namespace()
        self.iec61970_552 = get_iec61970_552()
        self.cim_profile, self.cim = get_cim_profile()

        # CIMG_URL points at the SPARQL endpoint: .../repositories/<id>
        # Derive both the repo ID and the server root for the management API.
        stripped = self.url.rstrip('/')
        if '/repositories/' not in stripped:
            raise ValueError(
                f"GraphDB CIMG_URL must be of the form "
                f"http://host:port/repositories/<id>, got {self.url!r}"
            )
        self.server_url, self.repo_id = stripped.rsplit('/repositories/', 1)
        self.statements_endpoint = f"{stripped}/statements"

    def connect(self):
        if not self.sparql_obj:
            self.sparql_obj = SPARQLWrapper(self.url)
            self.sparql_obj.setReturnFormat(JSON)

    def configure(self):
        """Create the repository if it doesn't already exist.

        Idempotent: a `GET /rest/repositories/<id>` that returns 200
        means the repo is live and we return without side effects.
        A 404 triggers a `POST /rest/repositories` with a multipart
        `config` field carrying the RDF4J Turtle template.
        """
        info_url = f"{self.server_url}/rest/repositories/{self.repo_id}"
        resp = requests.get(info_url)
        if resp.status_code == 200:
            return
        if resp.status_code != 404:
            resp.raise_for_status()

        config_ttl = _REPO_CONFIG_TEMPLATE.format(repo_id=self.repo_id)
        create_url = f"{self.server_url}/rest/repositories"
        create_resp = requests.post(
            create_url,
            files={'config': (f'{self.repo_id}.ttl', config_ttl, 'application/x-turtle')},
        )
        create_resp.raise_for_status()
        _log.info("Created GraphDB repository %s", self.repo_id)

    def drop_all(self):
        self.update('DROP ALL')

    def disconnect(self):
        self.sparql_obj = None

    def execute(self, query_message: str) -> QueryResponse:
        self.connect()
        self.sparql_obj.setQuery(query_message)
        self.sparql_obj.setMethod(POST)
        return self.sparql_obj.query().convert()

    def update(self, query_message: str) -> QueryResponse:
        """Execute a SPARQL UPDATE against the RDF4J statements endpoint.

        GraphDB's `/statements` accepts both SPARQL UPDATE bodies
        (Content-Type application/sparql-update) and RDF payloads
        (Content-Type application/rdf+xml, etc.) — differentiated purely
        by the Content-Type header. Using `requests` directly avoids the
        SPARQLWrapper-update issues we already hit with Oxigraph.
        """
        resp = requests.post(
            self.statements_endpoint,
            data=query_message.encode('utf-8'),
            headers={'Content-Type': 'application/sparql-update'},
        )
        resp.raise_for_status()
        return resp
