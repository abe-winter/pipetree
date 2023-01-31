import dataclasses, enum, collections
from datetime import timedelta
from typing import Dict, Callable, TypeVar, Tuple, Any, Optional, NamedTuple, Iterable, Hashable, List, Set, Generator

NodeType = TypeVar('NodeType')

class Degree(NamedTuple):
    node: NodeType
    in_: int
    out: int

@dataclasses.dataclass
class SourceSink:
    sources: List[NodeType] = dataclasses.field(default_factory=list)
    sinks: List[NodeType] = dataclasses.field(default_factory=list)

class LoopError(Exception):
    "this would have infinite-looped but hit a guard"

@dataclasses.dataclass
class Minigraph:
    "miniature (directed) graph class with basics we need; I don't want to depend on (good but heavy) networkx"
    edges: List[Tuple[NodeType, NodeType]]
    node_to_key: Callable[[NodeType], Hashable] = lambda x: x

    def degrees(self) -> Iterable[Degree]:
        in_ = collections.Counter()
        out = collections.Counter()
        lookup = {}
        for a, b in self.edges:
            out[self.node_to_key(a)] += 1
            in_[self.node_to_key(b)] += 1
            lookup.setdefault(self.node_to_key(a), a)
            lookup.setdefault(self.node_to_key(b), b)
        for id_ in set(in_) | set(out):
            yield Degree(lookup[id_], in_[id_], out[id_])

    def outlinks(self) -> dict:
        "return {node_or_key: List[node_or_key]}"
        outlinks = collections.defaultdict(list)
        for a, b in self.edges:
            outlinks[self.node_to_key(a)].append(self.node_to_key(b))
        return outlinks

    def source_sink(self, degrees = None) -> SourceSink:
        degrees = degrees if degrees is not None else self.degrees()
        ret = SourceSink()
        for deg in degrees:
            if deg.in_ == deg.out == 0:
                continue
            if deg.in_ == 0:
                ret.sources.append(deg.node)
            if deg.out == 0:
                ret.sinks.append(deg.node)
        return ret

    def cycles(self, source_sink = None, degrees = None):
        ""
        source_sink = source_sink or self.source_sink(degrees)
        if not source_sink.sources:
            raise NotImplementedError("unhandled case: no sources in graph")
        links = self.outlinks()
        cycles = []
        limiter = len(self.edges) + 1
        for source in source_sink.sources:
            yield from walk_outlinks(source, links, set(), limiter)

    def to_dot(self) -> str:
        "convert to graphviz format"
        # todo: figure out escaping for spaces etc
        return "digraph {\n" + '\n'.join(f'  {self.node_to_key(a)} -> {self.node_to_key(b)}' for a, b in self.edges) + "\n}"

KeyType = TypeVar('KeyType')
def walk_outlinks(start: KeyType, links: Dict[KeyType, List[KeyType]], seen: Set[KeyType], limiter: int) -> Generator: # Generator[Tuple[KeyType, KeyType]]:
    "helper for Minigraph.cycles(). limiter should start as # edges"
    limiter -= 1
    if limiter < 0:
        raise LoopError
    seen.add(start)
    for dest in links[start]:
        if dest in seen:
            yield (start, dest)
        else:
            yield from walk_outlinks(dest, links, seen, limiter)
