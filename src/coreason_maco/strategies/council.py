# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import asyncio
from typing import Any, Dict, List

from coreason_identity.models import UserContext
from pydantic import BaseModel, ConfigDict, Field

from coreason_maco.core.interfaces import AgentExecutor
from coreason_maco.utils.logger import logger


class CouncilConfig(BaseModel):
    """Configuration for the Council of Models strategy."""

    model_config = ConfigDict(extra="forbid")

    agents: List[Dict[str, Any]] = Field(..., description="List of model configs for the debating agents")
    synthesizer: Dict[str, Any] = Field(..., description="Config for the synthesizer/judge agent")
    timeout_seconds: float = 30.0


class CouncilResult(BaseModel):
    """The result of a council execution."""

    model_config = ConfigDict(extra="forbid")

    consensus: str
    individual_votes: Dict[str, str]


class CouncilStrategy:
    """Orchestrates a Map-Reduce consensus process among multiple models."""

    def __init__(self, executor: AgentExecutor) -> None:
        """Initializes the CouncilStrategy.

        Args:
            executor: The agent executor to use for running models.
        """
        self.executor = executor

    async def execute(self, prompt: str, config: CouncilConfig, context: UserContext) -> CouncilResult:
        """Executes the council strategy.

        Fan out to multiple agents (Map), then synthesize results (Reduce).

        Args:
            prompt: The input prompt/question.
            config: The configuration for the council.
            context: The user context.

        Returns:
            CouncilResult: The synthesized consensus and individual votes.

        Raises:
            RuntimeError: If all agents fail or synthesizer fails.
            ValueError: If context is missing.
        """
        if context is None:
            raise ValueError("UserContext is required for Council Strategy")

        logger.debug("Executing Council Strategy", user_id=context.user_id)

        # Map Phase: Fan out to all agents
        tasks = []
        for agent_config in config.agents:
            tasks.append(asyncio.wait_for(self.executor.invoke(prompt, agent_config), timeout=config.timeout_seconds))

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_votes: Dict[str, str] = {}
        valid_votes_list: List[str] = []

        for i, result in enumerate(results):
            model_name = config.agents[i].get("model", f"agent-{i}")
            if isinstance(result, BaseException):
                # In a real system, we'd log this.
                # For now, we just skip the failed vote.
                continue

            # AgentExecutor returns AgentResponse protocol which has .content
            valid_votes[model_name] = result.content
            valid_votes_list.append(result.content)

        if not valid_votes:
            raise RuntimeError("All council agents failed or timed out.")

        # Reduce Phase: Synthesize consensus
        synthesis_prompt = f"Original Query: {prompt}\n\n---\n\n"
        for model, vote in valid_votes.items():
            synthesis_prompt += f"Model {model} Response:\n{vote}\n\n---\n\n"

        synthesis_prompt += (
            "Review the above responses. Identify points of agreement and disagreement. "
            "Synthesize a single, authoritative answer that represents the best consensus."
        )

        try:
            final_response = await asyncio.wait_for(
                self.executor.invoke(synthesis_prompt, config.synthesizer), timeout=config.timeout_seconds
            )
            consensus = final_response.content
        except Exception as e:
            raise RuntimeError("Synthesizer agent failed.") from e

        return CouncilResult(consensus=consensus, individual_votes=valid_votes)
