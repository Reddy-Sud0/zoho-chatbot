"""
agents/base_agent.py
────────────────────
Abstract base class for all LangGraph agents in this system.

Every concrete agent (QueryAgent, ActionAgent, RouterAgent) inherits from
BaseAgent, which provides:
  - A shared LLM factory
  - Standardised logging helpers
  - A contract via the abstract `run()` method
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base for all conversational agents.

    Subclasses must implement :meth:`run`, which receives the full
    LangGraph ``AgentState`` dict and returns an updated copy.
    """

    #: Model name used for all agents — override in subclasses if needed.
    MODEL_NAME: str = "gemini-2.5-flash"
    #: Temperature for LLM inference.
    TEMPERATURE: float = 0.0

    def __init__(self) -> None:
        self._llm: ChatGoogleGenerativeAI | None = None

    # ──────────────────────────────────────────────────────────────
    # LLM access (lazy singleton per agent instance)
    # ──────────────────────────────────────────────────────────────

    def get_llm(self) -> ChatGoogleGenerativeAI:
        """Return a cached LLM instance, creating it on first call."""
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=self.MODEL_NAME,
                temperature=self.TEMPERATURE,
            )
        return self._llm

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    def log_info(self, message: str, **extra: Any) -> None:
        logger.info("[%s] %s | %s", self.__class__.__name__, message, extra or "")

    def log_error(self, message: str, exc: BaseException | None = None) -> None:
        logger.error("[%s] %s", self.__class__.__name__, message, exc_info=exc)

    # ──────────────────────────────────────────────────────────────
    # Contract
    # ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def run(self, state: dict) -> dict:
        """
        Process the current graph state and return the updated state.

        Args:
            state: The LangGraph ``AgentState`` dict.

        Returns:
            Updated ``AgentState`` dict with new messages / flags.
        """
