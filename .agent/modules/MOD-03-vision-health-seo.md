# 👁️ MOD-03: Reconocimiento por Visión IA + Salud del Producto ($0-100\%$) + SEO

* **Nivel SDD:** 🟢 Nivel 1.3
* **Responsable:** **Track B (Adri)**
* **Estado Actual:** `⏳ READY`
* **SLA de Latencia:** $\le 2500\text{ ms}$ (con `asyncio.wait_for(..., timeout=2.5)` hacia fallback determinista)

---

## 1. Responsabilidad Única (SRP) y Diseño SOLID en Python (`Pillow` + Multimodal IA)

* **Principio de Inversión de Dependencias (DIP) y Sustitución de Liskov (LSP) en Python:**
  * Definimos el puerto `VisionProviderProtocol` en `backend/app/vision/`:
    ```python
    from typing import Protocol
    from PIL import Image
    from app.models.sdd import VisionAnalysisResult

    class VisionProviderProtocol(Protocol):
        provider_id: str
        async def analyze(
            self, image: Image.Image, photo_data_url: str, user_hint: str | None = None
        ) -> VisionAnalysisResult: ...
    ```
  * Implementaciones intercambiables en Python:
    1. `GeminiVisionProvider` (`GEMINI_API_KEY` — `google-genai` con `gemini-2.5-flash` pasando el objeto `PIL.Image` directamente y `response_schema=VisionAnalysisResult`).
    2. `OpenAIVisionProvider` (`OPENAI_API_KEY` — `openai` `gpt-4o-mini` con salida estructurada Pydantic).
    3. `DeterministicVisionProvider` (Fallback local en Python con `Pillow` que inspecciona brillo/contraste/dimensiones de la imagen y el catálogo local en $< 40\text{ ms}$, garantizando 100% de disponibilidad en la demo incluso sin internet).

---

## 2. Rúbrica de Diagnóstico de Salud (`conditionScore` $0-100\%$)

Para mantener consistencia con el motor MCP de Matías (`MOD-04`), el normalizador de salud aplica esta tabla estricta:

| Rango `conditionScore` | `conditionLabel` Oficial | Criterio Visual Analizado |
| :---: | :--- | :--- |
| **$90 - 100$** | `'Nuevo'` | Precintado, con caja original intacta o sin la más mínima huella de uso. |
| **$80 - 89$** | `'Como nuevo'` | Superficie limpia, sin rayones visibles, mandos/botones firmes, excelente conservación. |
| **$65 - 79$** | `'Buen estado'` | Uso normal doméstico, micro-marcas leves que no afectan al funcionamiento. |
| **$40 - 64$** | `'Desgaste visible'` | Arañazos apreciables, desgaste en esquinas o falta de accesorios secundarios. |
| **$0 - 39$** | `'Para piezas'` | Roturas visibles, pantalla fisurada o signos severos de deterioro. |

---

## 3. Generador de Copywriting SEO para Wallapop

El resultado incluye obligatoriamente:
* **`seoTitle`** ($\le 65$ caracteres): `[Marca + Modelo Exacto] - [Estado] + [Keyword Gancho]` (ej. *"Nintendo Switch OLED 64GB Blanca - Como Nueva (Salud 92%)"*).
* **`seoDescription`**: Texto persuasivo listo para pegar en Wallapop estructurado en:
  1. Gancho de apertura + modelo exacto.
  2. Diagnóstico transparente de estado (`conditionScore`% verificado por IA).
  3. Qué incluye y motivo de venta.
  4. Etiquetas/keywords de búsqueda al pie.

---

## 4. Archivos del Módulo en Python (`Track B`)

| Archivo | Propósito | Límite Líneas |
| :--- | :--- | :---: |
| `backend/app/vision/image_processor.py` | Decodificación Base64 a `PIL.Image`, validación y extracción de métricas visuales (`Pillow`) | $\le 90$ |
| `backend/app/vision/gemini_provider.py` | Adaptador multimodal Python `google-genai` (Gemini 2.5 Flash) | $\le 120$ |
| `backend/app/vision/openai_provider.py` | Adaptador multimodal Python `openai` (`gpt-4o-mini`) | $\le 120$ |
| `backend/app/vision/fallback_provider.py` | Reconocedor determinista local en Python con análisis `Pillow` + catálogo | $\le 140$ |
| `backend/app/vision/orchestrator.py` | Cadena de responsabilidad con `asyncio.wait_for(timeout=2.5)` y normalización de `conditionLabel` | $\le 100$ |
| `backend/app/routers/vision.py` | Endpoint FastAPI `POST /api/vision/analyze` que valida el payload con Pydantic y devuelve `VisionAnalysisResult` | $\le 55$ |

---

## 5. Checklist de Control y Calidad (MOD-03)

- [ ] Función pura `mapScoreToConditionLabel(score: number): ConditionLabel` testeada al 100% para todos los bordes ($0, 39, 40, 64, 65, 79, 80, 89, 90, 100$).
- [ ] El modelo Pydantic v2 garantiza que `conditionScore` siempre se recorta (*clamp*) al intervalo $[0, 100]$.
- [ ] `ResilientVisionOrchestrator` hace fallback automático en $\le 2.5\text{ s}$ si no hay API key configurada o si la red falla.
- [ ] `seoTitle` y `seoDescription` generados en español natural, persuasivo y sin placeholders vacíos.
