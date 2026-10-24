"""Unit & Integration Tests for MOD-03 Vision Recognition."""

from __future__ import annotations

import asyncio
import base64
import io
import unittest
from PIL import Image

try:
    from fastapi.testclient import TestClient
    from app.main import app
except ImportError:
    TestClient = None  # type: ignore[assignment,misc]
    app = None  # type: ignore[assignment]
from app.models.sdd import (
    SEO_TITLE_MAX_LENGTH,
    VisionAnalysisResult,
    clamp_condition_score,
    map_score_to_condition_label,
)
from app.vision.fallback_provider import DeterministicVisionProvider
from app.vision.image_processor import decode_image_source, prepare_and_inspect_image
from app.vision.ollama_provider import OllamaVisionProvider
from app.vision.openai_provider import OpenAIVisionProvider
from app.vision.orchestrator import ResilientVisionOrchestrator
from app.vision.protocol import ImageVisualMetrics


def _create_test_data_url(width: int = 400, height: int = 300, rgb: tuple[int, int, int] = (240, 240, 245)) -> str:
    img = Image.new("RGB", (width, height), color=rgb)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


class _MockMacOllamaProvider:
    provider_id = "ollama_local"

    async def analyze(
        self,
        image: Image.Image,
        metrics: ImageVisualMetrics,
        photo_data_url: str,
        user_hint: str | None = None,
    ) -> VisionAnalysisResult:
        del image, metrics, photo_data_url, user_hint
        return VisionAnalysisResult(
            name="Sony PlayStation 5 Edición Disco 825GB Blanca",
            category="Consolas y Videojuegos",
            brand="Sony",
            model="PS5 CFI-1216A",
            condition_score=94,
            condition_label="Como nuevo",  # Auto-normalizes to 'Nuevo'
            condition_reasoning="Caja y consola impecables sin marcas de uso.",
            seo_title="Sony PlayStation 5 Edición Disco 825GB Blanca Con Caja Original Impecable",
            seo_description="Descripción corta de prueba",
            source="ollama_local",
            model_used="qwen2.5-vl:7b-q8_0",
        )


class TestVisionModule(unittest.TestCase):
    """Verifies all MOD-03 quality gates, resilience, and SDD contracts."""

    def test_condition_label_boundaries_all_edges(self) -> None:
        expected = {
            0: "Para piezas", 39: "Para piezas", 40: "Desgaste visible", 64: "Desgaste visible",
            65: "Buen estado", 79: "Buen estado", 80: "Como nuevo", 89: "Como nuevo",
            90: "Nuevo", 100: "Nuevo",
        }
        for score, label in expected.items():
            with self.subTest(score=score):
                self.assertEqual(map_score_to_condition_label(score), label)

    def test_condition_score_clamping_and_normalization(self) -> None:
        self.assertEqual(clamp_condition_score(-25), 0)
        self.assertEqual(clamp_condition_score(145), 100)
        res = VisionAnalysisResult(
            name="iPhone X", category="Telefonía", brand="Apple", model="A1901",
            condition_score=-10, condition_label="Nuevo",
            condition_reasoning="Pantalla rota para repuestos.",
            seo_title="iPhone X para piezas", seo_description="Se vende iPhone X para piezas.",
        )
        self.assertEqual(res.condition_score, 0)
        self.assertEqual(res.condition_label, "Para piezas")

    def test_pillow_image_processor(self) -> None:
        data_url = _create_test_data_url(1200, 900, (245, 245, 250))
        raw_img = decode_image_source(data_url)
        enhanced, metrics = prepare_and_inspect_image(raw_img, max_dimension_px=800)
        self.assertLessEqual(max(enhanced.size), 800)
        self.assertEqual(metrics.color_name_es, "Blanco")
        self.assertGreater(metrics.brightness, 200.0)

    def test_hint_dynamic_synthesis_and_reasoning_coherence(self) -> None:
        fallback = DeterministicVisionProvider()
        data_url = _create_test_data_url()
        raw = decode_image_source(data_url)
        _, metrics = prepare_and_inspect_image(raw)

        res = asyncio.run(fallback.analyze(raw, metrics, data_url, user_hint="Taladro Percutor Bosch GSB 18V"))
        self.assertEqual(res.brand, "Bosch")
        self.assertEqual(res.category, "Bricolaje y Herramientas")
        self.assertIn("Bosch", res.name)
        self.assertIn(res.condition_label, ("Como nuevo", "Nuevo", "Buen estado"))
        self.assertIn(metrics.color_name_es.lower(), res.condition_reasoning.lower())

    def test_ollama_circuit_breaker_caches_unreachable_node(self) -> None:
        provider = OllamaVisionProvider(base_url="http://127.0.0.1:54321")
        provider.reset_circuit_breaker()
        first = asyncio.run(provider.check_node_health())
        self.assertFalse(first["reachable"])

        # Second call within TTL returns cached result instantly without socket attempt
        second = asyncio.run(provider.check_node_health())
        self.assertFalse(second["reachable"])
        self.assertEqual(first, second)

    def test_openai_provider_graceful_without_api_key(self) -> None:
        provider = OpenAIVisionProvider(api_key=None)
        self.assertFalse(provider.is_available())

    def test_orchestrator_mock_vlm_and_seo_bounds(self) -> None:
        data_url = _create_test_data_url()
        orchestrator = ResilientVisionOrchestrator(providers=[_MockMacOllamaProvider()], timeout_sec=1.0)
        res = asyncio.run(orchestrator.analyze_photo(data_url))
        self.assertEqual(res.source, "ollama_local")
        self.assertEqual(res.condition_label, "Nuevo")
        self.assertLessEqual(len(res.seo_title), SEO_TITLE_MAX_LENGTH)

    def test_orchestrator_fallback_under_sla_when_offline(self) -> None:
        data_url = _create_test_data_url()
        orchestrator = ResilientVisionOrchestrator(
            providers=[DeterministicVisionProvider()], timeout_sec=0.5
        )
        res = asyncio.run(orchestrator.analyze_photo(data_url, user_hint="Nintendo Switch OLED"))
        self.assertEqual(res.source, "deterministic_fallback")
        self.assertEqual(res.brand, "Nintendo")
        self.assertLess(res.latency_ms or 9999, 1000)

    @unittest.skipIf(TestClient is None, "FastAPI not installed in current Python environment")
    def test_fastapi_endpoints_via_test_client(self) -> None:
        client = TestClient(app)
        status_res = client.get("/api/vision/node-status")
        self.assertEqual(status_res.status_code, 200)
        self.assertIn("activeProviders", status_res.json())

        data_url = _create_test_data_url()
        analyze_res = client.post("/api/vision/analyze", json={"photoDataUrl": data_url, "userHint": "Canon EOS"})
        self.assertEqual(analyze_res.status_code, 200)
        body = analyze_res.json()
        self.assertIn("conditionScore", body)
        self.assertEqual(body["brand"], "Canon")

    def test_corrupted_image_raises_clean_value_error(self) -> None:
        with self.assertRaises(ValueError):
            decode_image_source("data:image/jpeg;base64,/9j/corrupted")


if __name__ == "__main__":
    unittest.main()
