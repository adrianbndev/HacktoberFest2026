"""Funciones puras de precio (.agent/mcp/stealth-market-mcp.md §3). Track C las amplía en MOD-04."""


def health_weight(condition_score: float) -> float:
    """W_health = 0.65 + 0.50 * score/100 (score 70 -> 1.00)."""
    return 0.65 + 0.50 * max(0.0, min(100.0, condition_score)) / 100


def triplet_from_base(base_price: float, condition_score: float) -> tuple[int, int, int]:
    """(P_min, P_avg, P_max) sin muestra de mercado: P_avg ponderado por salud, -18 % y +24 %."""
    avg = max(3, round(base_price * health_weight(condition_score)))
    return min(avg - 1, round(avg * 0.82)), avg, max(avg + 1, round(avg * 1.24))
