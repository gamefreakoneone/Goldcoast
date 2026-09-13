import hashlib
import ipaddress
import re
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AwareDatetime, Field

from goldcoast.studio.brand import StrictModel


def canonical_url(value):
    parts = urlsplit(value)
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme not in {"https", "http"} or parts.username or parts.password or not host:
        raise ValueError("Only public HTTP(S) evidence URLs are accepted")
    if parts.port not in {None, 80, 443} or host == "localhost" or "." not in host:
        raise ValueError("Private or nonstandard evidence URL")
    if host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Private evidence URL")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("Private evidence URL")
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query)
            if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
        )
    )
    return urlunsplit((parts.scheme.lower(), host, parts.path or "/", query, ""))


def stable_id(value):
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def normalized(value):
    return re.sub(r"\s+", " ", value).strip().casefold()


class EvidenceSource(StrictModel):
    id: str
    url: str
    title: str = Field(max_length=300)
    text: str = Field(max_length=8000)
    provider: Literal["tavily", "ticketmaster", "video", "demo"]
    retrieved_at: AwareDatetime
    expires_at: AwareDatetime
    content_hash: str


class GraphClaim(StrictModel):
    subject: str = Field(min_length=1, max_length=150)
    predicate: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)
    source_id: str
    quote: str = Field(min_length=12, max_length=800)
    valid_until: AwareDatetime | None = None


class ClaimSet(StrictModel):
    claims: list[GraphClaim] = Field(default_factory=list, max_length=80)


class GraphNode(StrictModel):
    id: str
    label: str
    kind: Literal["entity", "source"]


class GraphEdge(StrictModel):
    source: str
    target: str
    predicate: str
    value: str
    quote: str
    state: Literal["supported", "disputed", "stale"]
    valid_until: AwareDatetime


class EvidenceGraph(StrictModel):
    sources: list[EvidenceSource] = Field(max_length=40)
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    built_at: AwareDatetime


def build_graph(sources, claims, now=None):
    now = now or datetime.now(UTC)
    sources = {s.id: s for s in sources}
    if len(sources) > 40:
        raise ValueError("Evidence graph supports at most 40 sources")
    groups = {}
    unique = {}
    for claim in ClaimSet(claims=claims).claims:
        source = sources.get(claim.source_id)
        if source is None or normalized(claim.quote) not in normalized(source.text):
            raise ValueError("Claim must quote an available source verbatim")
        key = (normalized(claim.subject), normalized(claim.predicate))
        groups.setdefault(key, set()).add(normalized(claim.value))
        unique[(*key, normalized(claim.value), claim.source_id)] = claim
    nodes = {s.id: GraphNode(id=s.id, label=s.title, kind="source") for s in sources.values()}
    edges = []
    for key, claim in unique.items():
        source = sources[claim.source_id]
        entity = stable_id("entity:" + key[0])
        nodes[entity] = GraphNode(id=entity, label=claim.subject, kind="entity")
        deadline = min(source.expires_at, claim.valid_until or source.expires_at)
        state = (
            "stale" if deadline <= now else "disputed" if len(groups[key[:2]]) > 1 else "supported"
        )
        edges.append(
            GraphEdge(
                source=entity,
                target=source.id,
                predicate=claim.predicate,
                value=claim.value,
                quote=claim.quote,
                state=state,
                valid_until=deadline,
            )
        )
    return EvidenceGraph(
        sources=list(sources.values()), nodes=list(nodes.values()), edges=edges, built_at=now
    )
