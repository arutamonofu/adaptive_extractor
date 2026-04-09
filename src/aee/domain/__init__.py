"""Domain layer for AutoEvoExtractor.

The domain layer contains the core business logic and entities,
independent of infrastructure concerns.
"""

from . import agents, entities, tasks
from . import evaluation  # lazy via __getattr__ in evaluation/__init__.py

__all__ = [
    "agents",
    "entities",
    "evaluation",
    "tasks",
]
