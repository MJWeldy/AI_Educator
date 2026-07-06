"""Prerequisite DAG utilities: cycle detection, depth ranks, unlock logic."""

from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Mastery, Topic, TopicEdge, UserTopicState


class CycleError(Exception):
    pass


class TopicGraph:
    """In-memory view of the prerequisite DAG over active topics."""

    def __init__(self, topics: list[Topic], edges: list[TopicEdge]):
        self.topics: dict[int, Topic] = {t.id: t for t in topics}
        self.hard_prereqs: dict[int, set[int]] = defaultdict(set)
        self.soft_prereqs: dict[int, set[int]] = defaultdict(set)
        self.dependents: dict[int, set[int]] = defaultdict(set)
        for e in edges:
            if e.prereq_id not in self.topics or e.topic_id not in self.topics:
                continue
            if e.kind == "hard":
                self.hard_prereqs[e.topic_id].add(e.prereq_id)
            else:
                self.soft_prereqs[e.topic_id].add(e.prereq_id)
            self.dependents[e.prereq_id].add(e.topic_id)

    @classmethod
    def load(cls, db: Session, include_draft: bool = False) -> "TopicGraph":
        q = select(Topic)
        if not include_draft:
            q = q.where(Topic.status == "active")
        topics = list(db.scalars(q))
        edges = list(db.scalars(select(TopicEdge)))
        return cls(topics, edges)

    def all_prereqs(self, topic_id: int) -> set[int]:
        return self.hard_prereqs[topic_id] | self.soft_prereqs[topic_id]

    def topological_order(self) -> list[int]:
        """Kahn's algorithm over all (hard+soft) edges. Raises CycleError."""
        indegree = {tid: len(self.all_prereqs(tid)) for tid in self.topics}
        queue = deque(sorted(tid for tid, d in indegree.items() if d == 0))
        order: list[int] = []
        while queue:
            tid = queue.popleft()
            order.append(tid)
            for dep in self.dependents[tid]:
                indegree[dep] -= 1
                if indegree[dep] == 0:
                    queue.append(dep)
        if len(order) != len(self.topics):
            remaining = set(self.topics) - set(order)
            slugs = [self.topics[t].slug for t in sorted(remaining)][:10]
            raise CycleError(f"prerequisite cycle involving: {slugs}")
        return order

    def depth_ranks(self) -> dict[int, int]:
        """Longest prerequisite chain length per topic (roots = 0)."""
        ranks: dict[int, int] = {}
        for tid in self.topological_order():
            prereqs = self.all_prereqs(tid)
            ranks[tid] = 1 + max((ranks[p] for p in prereqs), default=-1)
        return ranks

    def ancestors(self, topic_id: int) -> set[int]:
        seen: set[int] = set()
        stack = list(self.all_prereqs(topic_id))
        while stack:
            t = stack.pop()
            if t not in seen:
                seen.add(t)
                stack.extend(self.all_prereqs(t))
        return seen

    def descendants(self, topic_id: int) -> set[int]:
        seen: set[int] = set()
        stack = list(self.dependents[topic_id])
        while stack:
            t = stack.pop()
            if t not in seen:
                seen.add(t)
                stack.extend(self.dependents[t])
        return seen


KNOWN_STATES = {Mastery.learned.value, Mastery.mastered.value}


def effective_masteries(db: Session, graph: TopicGraph, profile_id: int) -> dict[int, str]:
    """Mastery per topic. Topics without a state row derive locked/unlocked
    from the graph; rows only exist once a topic has real history."""
    rows = db.scalars(
        select(UserTopicState).where(UserTopicState.profile_id == profile_id)
    ).all()
    stored = {r.topic_id: r.mastery for r in rows if r.topic_id in graph.topics}

    result: dict[int, str] = {}
    for tid in graph.topological_order():
        if tid in stored:
            result[tid] = stored[tid]
            continue
        prereqs = graph.hard_prereqs[tid]
        if all(result.get(p) in KNOWN_STATES for p in prereqs):
            result[tid] = Mastery.unlocked.value
        else:
            result[tid] = Mastery.locked.value
    return result


def frontier(graph: TopicGraph, masteries: dict[int, str]) -> list[int]:
    """Unlocked topics not yet learned — the learning frontier."""
    return [
        tid
        for tid, m in masteries.items()
        if m in (Mastery.unlocked.value, Mastery.learning.value)
    ]
