from __future__ import annotations

import asyncio
import logging
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from comfystream.client import ComfyStreamClient

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    """Pipeline lifecycle states."""

    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    STREAMING = auto()
    ERROR = auto()


class PipelineStateManager:
    """Manages pipeline state transitions and runner lifecycle."""

    def __init__(self, client: ComfyStreamClient):
        self.client = client
        self._state = PipelineState.UNINITIALIZED
        self._state_lock = asyncio.Lock()

    @property
    def state(self) -> PipelineState:
        return self._state

    async def transition_to(self, new_state: PipelineState):
        """Transition to a new state with automatic runner management."""
        # Fast path for no-op transitions
        if new_state == self._state:
            logger.debug("Pipeline state unchanged: %s", new_state.name)
            return

        async with self._state_lock:
            if new_state == self._state:
                logger.debug("Pipeline state unchanged (locked): %s", new_state.name)
                return

            old_state = self._state

            if not self._is_valid_transition(old_state, new_state):
                raise ValueError(f"Invalid transition: {old_state.name} -> {new_state.name}")

            await self._on_exit_state(old_state)
            self._state = new_state
            await self._on_enter_state(new_state)

            logger.info("Pipeline state: %s -> %s", old_state.name, new_state.name)

    def _is_valid_transition(self, from_state: PipelineState, to_state: PipelineState) -> bool:
        """Define valid state transitions."""
        valid_transitions = {
            PipelineState.UNINITIALIZED: {
                PipelineState.INITIALIZING,
                PipelineState.READY,
                PipelineState.ERROR,
            },
            PipelineState.INITIALIZING: {
                PipelineState.READY,
                PipelineState.ERROR,
            },
            PipelineState.READY: {
                PipelineState.INITIALIZING,
                PipelineState.STREAMING,
                PipelineState.UNINITIALIZED,
                PipelineState.ERROR,
            },
            PipelineState.STREAMING: {
                PipelineState.READY,
                PipelineState.ERROR,
            },
            PipelineState.ERROR: {
                PipelineState.INITIALIZING,
                PipelineState.READY,
                PipelineState.UNINITIALIZED,
            },
        }

        return to_state in valid_transitions.get(from_state, set())

    async def _on_enter_state(self, state: PipelineState):
        """Actions executed when entering a state."""
        if state == PipelineState.INITIALIZING:
            await self.client.resume_prompts()
        elif state == PipelineState.READY:
            self.client.pause_prompts()
        elif state == PipelineState.STREAMING:
            await self.client.resume_prompts()
        elif state == PipelineState.ERROR:
            self.client.pause_prompts()
        elif state == PipelineState.UNINITIALIZED:
            self.client.pause_prompts()

    async def _on_exit_state(self, _state: PipelineState):
        """Actions executed when exiting a state."""
        return

    def can_stream(self) -> bool:
        """Check if pipeline is ready to stream."""
        return self._state in {PipelineState.READY, PipelineState.STREAMING}

    def is_initialized(self) -> bool:
        """Check if pipeline has been initialized with prompts."""
        return self._state != PipelineState.UNINITIALIZED
