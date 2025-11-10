from enum import Enum


class MemoryType(Enum):
    VECTOR = "vector"
    GRAPH = "graph"
    SUMMARY = "summary"
    ENUMS = ["default", "vector", "graph", "summary"]
