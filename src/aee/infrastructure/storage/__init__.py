"""Storage infrastructure for AutoEvoExtractor.

This module provides repository pattern implementations for managing
various types of data: agents, ground truth, extractions, documents, and splits.
"""

from .agents import AgentMetadata, AgentRepository
from .documents import DocumentRepository
from .extractions import ExtractionRepository
from .ground_truth import GroundTruthRepository
from .splits import DataSplitRepository
from .migrations import (
    AgentMigrator,
    GroundTruthMigrator,
    migrate_all_agents,
    migrate_all_ground_truth,
)

__all__ = [
    "AgentMetadata",
    "AgentRepository",
    "ExtractionRepository",
    "GroundTruthRepository",
    "DocumentRepository",
    "DataSplitRepository",
    # Migrations
    "AgentMigrator",
    "GroundTruthMigrator",
    "migrate_all_agents",
    "migrate_all_ground_truth",
]
