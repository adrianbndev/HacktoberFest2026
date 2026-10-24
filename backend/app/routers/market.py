"""STUB de MOD-00: tasación determinista sin red. Track C (Matías) lo sustituye por el motor MCP en MOD-04."""
from fastapi import APIRouter

from app.mcp.pricing_math import triplet_from_base
from app.models.sdd import MarketValuationRequest, MarketValuationResult

router = APIRouter()


@router.post("/market/valuate", response_model=MarketValuationResult, response_model_exclude_none=True)
def valuate(body: MarketValuationRequest) -> MarketValuationResult:
    price_min, price_avg, price_max = triplet_from_base(200, body.condition_score)
    return MarketValuationResult(
        price_min=price_min, price_avg=price_avg, price_max=price_max, sample_size=0,
        platforms=["wallapop", "vinted", "milanuncios", "ebay"], comparable_listings=[], source="stealth_fallback",
    )
