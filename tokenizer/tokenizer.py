from __future__ import annotations
from typing import Self
from abc import ABC


class LinkedListNode(ABC):
    __slots__ = ["prev", "next"]
    prev: Self | None
    next: Self | None

    def __init__(self):
        self.prev = None
        self.next = None

    def append(self, node: Self):
        """Insert a node after the current node."""
        node.prev = self
        node.next = self.next

        if self.next:
            self.next.prev = node
        self.next = node

    def unlink(self):
        """Unlink the current node from the list."""
        if self.prev:
            self.prev.next = self.next
        if self.next:
            self.next.prev = self.prev
        self.prev = None
        self.next = None


class CorpusNode(LinkedListNode):
    __slots__ = ["value", "back_ref"]
    value: str
    back_ref: PosListNode | None

    def __init__(
        self,
        value: str,
    ):
        super().__init__()
        self.value = value
        self.back_ref = None


class PosListNode:
    __slots__ = ["corpus_node", "prev", "next"]
    corpus_node: CorpusNode
    prev: Self | None
    next: Self | None

    def __init__(self, prev: Self | None, next: Self | None, corpus_node: CorpusNode):
        self.prev = prev
        self.next = next
        self.corpus_node = corpus_node


class FreqBucketNode:
    __slots__ = ["value", "prev", "next", "freq"]
    value: str
    prev: Self | None
    next: Self | None
    freq: int

    def __init__(self, prev: Self | None, next: Self | None, value: str, freq: int):
        self.prev = prev
        self.next = next
        self.value = value
        self.freq = freq
