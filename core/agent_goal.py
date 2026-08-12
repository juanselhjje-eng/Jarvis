from __future__ import annotations

"""General goal representation for JARVIS computer control.

The planner deliberately describes *what* must be accomplished rather than
hard-coding one function per application. Tool selection and UI interaction
are delegated to the runtime, which can observe the current computer state
and adapt when a step fails.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    REVIEW = "review"
    CONFIRM = "confirm"


@dataclass
class GoalStep:
    objective: str
    success_signal: str = ""
    risk: RiskLevel = RiskLevel.LOW
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    attempts: int = 0


@dataclass
class ComputerGoal:
    request: str
    steps: list[GoalStep] = field(default_factory=list)
    status: str = "planning"
    context: dict[str, Any] = field(default_factory=dict)

    def next_step(self) -> GoalStep | None:
        return next((s for s in self.steps if s.status == "pending"), None)

    def mark_success(self, step: GoalStep):
        step.status = "done"
        self.status = "completed" if self.next_step() is None else "running"

    def mark_failure(self, step: GoalStep):
        step.attempts += 1
        step.status = "retry" if step.attempts < 3 else "blocked"
        self.status = "blocked" if step.status == "blocked" else "running"

    def requires_confirmation(self, step: GoalStep) -> bool:
        return step.risk == RiskLevel.CONFIRM


def make_goal(request: str, steps: list[dict[str, Any]] | None = None) -> ComputerGoal:
    goal = ComputerGoal(request=request)
    for raw in steps or []:
        goal.steps.append(GoalStep(
            objective=str(raw.get("objective", "")),
            success_signal=str(raw.get("success_signal", "")),
            risk=RiskLevel(str(raw.get("risk", RiskLevel.LOW))),
            metadata=dict(raw.get("metadata", {})),
        ))
    goal.status = "running" if goal.steps else "planning"
    return goal
