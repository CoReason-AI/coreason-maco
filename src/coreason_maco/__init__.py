# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

"""
A new Python project.
"""

__version__ = "0.3.2"
__author__ = "Gowtham A Rao"
__email__ = "gowtham.rao@coreason.ai"

from .client import Service, ServiceAsync
from .core.controller import WorkflowController
from .engine.runner import WorkflowRunner
from .events.protocol import GraphEvent
from .main import hello_world

__all__ = [
    "WorkflowController",
    "WorkflowRunner",
    "GraphEvent",
    "hello_world",
    "ServiceAsync",
    "Service",
]
