"""Prompt contract for DeepSeek-only product relevance.

Keeping the long Spanish prompt out of the classifier keeps both modules under
the repository's per-file size gate.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from app.models.market_analysis import MarketAnalysisRequest
from app.models.sdd import MarketListingSample

SYSTEM_PROMPT = """Eres un clasificador estricto de anuncios de segunda mano.
Recibes un producto objetivo y una lista de anuncios. Decide si cada anuncio es
exactamente ese producto. Devuelve solo JSON válido con esta forma:
{"listings": [{"id": <id entero recibido>, "label": "<etiqueta>"}]}
Etiquetas permitidas: exact, different_model, accessory, single_item, broken,
unrelated, bundle.
Incluye una entrada por cada id recibido. No inventes ids ni anuncios.

Reglas:
- exact: mismo producto completo, misma generación y modelo, funciona y es una
  unidad.
- different_model: otro modelo, otra generación o cualquier duda razonable.
- accessory: funda, estuche, caja, cable, cargador, recambio o accesorio.
- single_item: una sola pieza o un solo lado del producto (p. ej. un auricular).
- broken: roto, averiado, no funciona o para piezas.
- bundle: pack o lote de varios productos o unidades.
- unrelated: no tiene relación con el producto objetivo.
- "con estuche" o "con caja" puede ser exact si el producto está completo; el
  accesorio por separado nunca es exact.
- Si dudas entre exact y otro modelo, usa different_model.

Ejemplos para el objetivo "Apple AirPods Pro 2":
- "AirPods Pro 2" -> exact
- "Apple AirPods Pro 2" -> exact
- "AirPods Pro 2nd generation" -> exact
- "AirPods Pro 2 con estuche" -> exact
- "AirPods 2" -> different_model
- "AirPods Pro" -> different_model
- "AirPods Pro 3" -> different_model
- "AirPods Pro 2 solo izquierdo" -> single_item
- "AirPods Pro 2 rotos" -> broken
- "Funda para AirPods Pro 2" -> accessory
- "Estuche AirPods Pro 2" -> accessory
- "AirPods Pro 2 para piezas" -> broken
- "Lote 2x AirPods Pro 2" -> bundle
"""



def build_user_prompt(
    request: MarketAnalysisRequest, batch: Sequence[tuple[int, MarketListingSample]]
) -> str:
    payload = {
        "target": {
            "name": request.name,
            "brand": request.brand,
            "model": request.model,
            "category": request.category,
            "description": request.description,
            "conditionLabel": request.condition_label,
            "conditionScore": request.condition_score,
        },
        "listings": [
            {
                "id": index,
                "title": listing.title,
                "price": listing.price,
                "condition": listing.condition,
            }
            for index, listing in batch
        ],
    }
    return json.dumps(payload, ensure_ascii=False)
