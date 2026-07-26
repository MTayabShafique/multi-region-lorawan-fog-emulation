import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ScalingPolicy:
    minimum_replicas: int = 2
    maximum_replicas: int = 8
    target_messages_per_second: float = 20.0
    scale_down_utilization: float = 0.5
    backlog_scale_up_threshold: int = 10
    scale_up_periods: int = 2
    scale_down_periods: int = 5
    scale_up_step: int = 2
    scale_down_step: int = 1
    cooldown_seconds: int = 120

    def __post_init__(self):
        if self.minimum_replicas < 1:
            raise ValueError("minimum_replicas must be at least 1")
        if self.maximum_replicas < self.minimum_replicas:
            raise ValueError("maximum_replicas must be >= minimum_replicas")
        if self.target_messages_per_second <= 0:
            raise ValueError("target_messages_per_second must be positive")
        if not 0 < self.scale_down_utilization < 1:
            raise ValueError("scale_down_utilization must be between 0 and 1")
        if self.scale_up_periods < 1 or self.scale_down_periods < 1:
            raise ValueError("stabilization periods must be positive")
        if self.scale_up_step < 1 or self.scale_down_step < 1:
            raise ValueError("scaling steps must be positive")
        if self.backlog_scale_up_threshold < 1:
            raise ValueError("backlog_scale_up_threshold must be positive")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative")


@dataclass(frozen=True)
class ScalingDecision:
    desired_replicas: int
    action: str
    reason: str


@dataclass
class _RegionState:
    scale_up_streak: int = 0
    scale_down_streak: int = 0
    last_scaled_at: float | None = None


class ScalingDecisionEngine:
    def __init__(self, policy):
        self.policy = policy
        self._states = {}

    def _state(self, region):
        return self._states.setdefault(region, _RegionState())

    def record_successful_scale(self, region, now):
        state = self._state(region)
        state.last_scaled_at = now
        state.scale_up_streak = 0
        state.scale_down_streak = 0

    def evaluate(self, region, current_replicas, message_rate, backlog, now):
        if current_replicas < 1:
            raise ValueError("current_replicas must be positive")
        if message_rate < 0 or backlog < 0:
            raise ValueError("observed metrics cannot be negative")

        state = self._state(region)
        if (
            state.last_scaled_at is not None
            and now - state.last_scaled_at < self.policy.cooldown_seconds
        ):
            state.scale_up_streak = 0
            state.scale_down_streak = 0
            return ScalingDecision(current_replicas, "hold", "cooldown")

        rate_target = math.ceil(
            message_rate / self.policy.target_messages_per_second
        )
        scale_up_target = max(self.policy.minimum_replicas, rate_target)
        if backlog >= self.policy.backlog_scale_up_threshold:
            scale_up_target = max(scale_up_target, current_replicas + 1)
        scale_up_target = min(scale_up_target, self.policy.maximum_replicas)

        if scale_up_target > current_replicas:
            state.scale_up_streak += 1
            state.scale_down_streak = 0
            if state.scale_up_streak < self.policy.scale_up_periods:
                return ScalingDecision(
                    current_replicas, "hold", "scale-up stabilization"
                )
            desired = min(
                scale_up_target,
                current_replicas + self.policy.scale_up_step,
                self.policy.maximum_replicas,
            )
            state.scale_up_streak = 0
            return ScalingDecision(desired, "scale_up", "load or backlog")

        down_capacity = (
            self.policy.target_messages_per_second
            * self.policy.scale_down_utilization
        )
        scale_down_target = max(
            self.policy.minimum_replicas,
            math.ceil(message_rate / down_capacity),
        )
        scale_down_target = min(scale_down_target, self.policy.maximum_replicas)

        if backlog == 0 and scale_down_target < current_replicas:
            state.scale_down_streak += 1
            state.scale_up_streak = 0
            if state.scale_down_streak < self.policy.scale_down_periods:
                return ScalingDecision(
                    current_replicas, "hold", "scale-down stabilization"
                )
            desired = max(
                scale_down_target,
                current_replicas - self.policy.scale_down_step,
                self.policy.minimum_replicas,
            )
            state.scale_down_streak = 0
            return ScalingDecision(desired, "scale_down", "sustained low load")

        state.scale_up_streak = 0
        state.scale_down_streak = 0
        return ScalingDecision(current_replicas, "hold", "within target")
