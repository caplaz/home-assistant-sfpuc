"""Utility functions for SFPUC integration."""
from .const import TIER_1_LIMIT, TIER_2_LIMIT, TIER_1_RATE, TIER_2_RATE, TIER_3_RATE


def calculate_water_cost(usage_ccf: float) -> float:
    """Calculate water cost based on SFPUC tiered rates."""
    if usage_ccf <= TIER_1_LIMIT:
        return usage_ccf * TIER_1_RATE
    elif usage_ccf <= TIER_2_LIMIT:
        tier1_cost = TIER_1_LIMIT * TIER_1_RATE
        tier2_usage = usage_ccf - TIER_1_LIMIT
        tier2_cost = tier2_usage * TIER_2_RATE
        return tier1_cost + tier2_cost
    else:
        tier1_cost = TIER_1_LIMIT * TIER_1_RATE
        tier2_cost = (TIER_2_LIMIT - TIER_1_LIMIT) * TIER_2_RATE
        tier3_usage = usage_ccf - TIER_2_LIMIT
        tier3_cost = tier3_usage * TIER_3_RATE
        return tier1_cost + tier2_cost + tier3_cost