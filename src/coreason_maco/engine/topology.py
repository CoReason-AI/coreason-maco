# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import List, Any, Dict

import networkx as nx

from coreason_maco.core.manifest import RecipeManifest, AgentNode, HumanNode


class CyclicDependencyError(Exception):
    """Raised when the graph contains a cycle."""

    pass


class GraphIntegrityError(Exception):
    """Raised when the graph has integrity issues (e.g., islands)."""

    pass


class TopologyEngine:
    """Responsible for validating the graph topology and determining execution order."""

    def build_graph(self, manifest: RecipeManifest) -> nx.DiGraph:
        """Builds a NetworkX DiGraph from the RecipeManifest.

        Validates the graph after building.

        Args:
            manifest: The RecipeManifest object.

        Returns:
            nx.DiGraph: A validated NetworkX DiGraph.
        """
        graph = nx.DiGraph(name=manifest.name)

        # Access graph topology from the 'topology' attribute
        # manifest.topology.nodes and manifest.topology.edges
        nodes = manifest.topology.nodes
        edges = manifest.topology.edges

        for node in nodes:
            # Store node attributes
            # id is used as the node key

            config: Dict[str, Any] = {}
            if isinstance(node, AgentNode):
                 # AgentNode has agent_name. Pass it in config.
                 config = node.model_dump(exclude={"id", "type", "visual"}, exclude_unset=True)
                 # Ensure council_config is accessible if present (it's in the dump, but let's be explicit if needed)
            elif isinstance(node, HumanNode):
                 config = node.model_dump(exclude={"id", "type", "visual"}, exclude_unset=True)
            else:
                 # Fallback for other nodes: use .config if available or dump
                 if hasattr(node, "config"):
                     config = node.config
                 else:
                     config = node.model_dump(exclude={"id", "type", "visual"}, exclude_unset=True)

            graph.add_node(node.id, type=node.type, config=config)

        for edge in edges:
            edge_attrs = {}
            if edge.condition:
                edge_attrs["condition"] = edge.condition

            # Kernel edges use source_node_id / target_node_id
            graph.add_edge(edge.source_node_id, edge.target_node_id, **edge_attrs)

        self.validate_graph(graph)

        return graph

    def validate_graph(self, graph: nx.DiGraph) -> None:
        """Validates that the graph is acyclic and connected.

        Args:
            graph: The NetworkX DiGraph to validate.

        Raises:
            CyclicDependencyError: If the graph contains a cycle.
            GraphIntegrityError: If the graph is not weakly connected (contains islands).
        """
        if not nx.is_directed_acyclic_graph(graph):
            raise CyclicDependencyError("The workflow graph contains a cycle.")

        if len(graph) > 0:
            if not nx.is_weakly_connected(graph):
                raise GraphIntegrityError("The workflow graph contains disconnected islands.")

    def get_execution_layers(self, graph: nx.DiGraph) -> List[List[str]]:
        """Returns the topological generations (execution layers) of the graph.

        Args:
            graph: The NetworkX DiGraph.

        Returns:
            List[List[str]]: A list of lists, where each inner list contains node IDs that can be executed in parallel.

        Raises:
            CyclicDependencyError: If the graph contains a cycle (should be caught by validate_graph).
        """
        try:
            layers = list(nx.topological_generations(graph))
            # topological_generations returns iterator of sets/lists. Convert to list of lists.
            return [list(layer) for layer in layers]
        except nx.NetworkXUnfeasible as e:
            raise CyclicDependencyError("Cannot determine execution layers for a cyclic graph.") from e
