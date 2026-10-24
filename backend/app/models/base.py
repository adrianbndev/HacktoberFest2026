"""Tipos base de los contratos. Se importan siempre a través de app.models.sdd."""
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

TeamMemberId = Literal["ales", "adri", "matias"]
ConditionLabel = Literal["Nuevo", "Como nuevo", "Buen estado", "Desgaste visible", "Para piezas"]
MarketPlatform = Literal["wallapop", "vinted", "milanuncios", "ebay"]
CaptureSessionStatus = Literal[
    "waiting_for_mobile", "mobile_connected", "photo_uploaded", "analyzing", "completed", "error"
]
NotificationType = Literal["price_up", "price_down", "sell_opportunity", "delivery_reminder"]
MetricChanged = Literal["priceMin", "priceAvg", "priceMax"]
WeatherCondition = Literal["sunny", "cloudy", "rainy", "windy"]

# conditionScore siempre en [0, 100]: se recorta en vez de rechazar (la IA a veces devuelve 105 o 87.5).
ConditionScore = Annotated[int, BeforeValidator(lambda v: max(0, min(100, round(float(v)))))]


class CamelModel(BaseModel):
    """Serializa en camelCase (como sdd.ts) y acepta camelCase o snake_case al validar."""

    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, validate_by_alias=True, serialize_by_alias=True
    )


class PriceTriplet(CamelModel):
    """Las 3 medidas obligatorias con la invariante 0 < P_min < P_avg < P_max."""

    price_min: float
    price_avg: float
    price_max: float

    @model_validator(mode="after")
    def _strict_order(self) -> "PriceTriplet":
        if not 0 < self.price_min < self.price_avg < self.price_max:
            raise ValueError("Invariante SDD: 0 < priceMin < priceAvg < priceMax")
        return self
