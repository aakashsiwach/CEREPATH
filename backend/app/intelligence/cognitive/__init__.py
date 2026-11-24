"""Neuroscience-inspired cognitive components for Cerepath.

These are functional software analogies, not biological brain simulations.
"""
from .digital_mind import CognitiveContext, DigitalMind
from .hippocampal_indexing import HippocampalIndexer
from .metacognition import MetacognitiveMonitor
from .prefrontal_cortex import PrefrontalCognitiveController
from .prediction_error import RewardPredictionError
from .working_memory import BaddeleyWorkingMemory

__all__ = [
    "BaddeleyWorkingMemory",
    "CognitiveContext",
    "DigitalMind",
    "HippocampalIndexer",
    "MetacognitiveMonitor",
    "PrefrontalCognitiveController",
    "RewardPredictionError",
]
