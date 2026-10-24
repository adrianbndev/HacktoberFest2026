"""Unit & Integration Tests for MOD-03 Vision Recognition (unittest + pytest compatible)."""

from __future__ import annotations

import asyncio
import base64
import io
import unittest
from PIL import Image

from app.models.sdd import (
    SEO_TITLE_MAX_LENGTH,
    VisionAnalysisResult,
    clamp_condition_score,
    map_score_to_condition_label,
)
from app.vision.fallback_provider import DeterministicVisionProvider
from app.vision.image_processor import decode_image_source, prepare_and_inspect_image
from app.vision.ollama_provider import OllamaVisionProvider
from app.vision.orchestrator import ResilientVisionOrchestrator
from app.vision.protocol import ImageVisualMetrics


def _create_test_data_url(width: int = 1400, height: int = 1000, rgb: tuple[int, int, int] = (240, 240, 245)) -> str:
    img = Image.new("RGB", (width, height), color=rgb)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


class _SlowFailingProvider:
    provider_id = "slow_failing"

    async def analyze(
        self,
        image: Image.Image,
        metrics: ImageVisualMetrics,
        photo_data_url: str,
        user_hint: str | None = None,
    ) -> VisionAnalysisResult:
        del image, metrics, photo_data_url, user_hint
        await asyncio.sleep(5.0)
        raise TimeoutError("Simulated network stall")


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
            condition_label="Como nuevo",  # Should auto-normalize to 'Nuevo' because score=94
            condition_reasoning="Caja y consola impecables sin marcas de uso.",
            seo_title="Sony PlayStation 5 Edición Disco 825GB Blanca Con Caja Original Impecable y Mando DualSense Extra",
            seo_description="Descripción corta de prueba",
            source="ollama_local",
            model_used="qwen2.5-vl:7b-q8_0",
        )


class TestVisionModule(unittest.TestCase):
    """Verifies all MOD-03 quality gates and SDD invariants."""

    def test_condition_label_boundaries_all_edges(self) -> None:
        """Checklist #1: 100% boundary verification for [0, 39, 40, 64, 65, 79, 80, 89, 90, 100]."""
        expected_boundaries = {
            0: "Para piezas",
            39: "Para piezas",
            40: "Desgaste visible",
            64: "Desgaste visible",
            65: "Buen estado",
            79: "Buen estado",
            80: "Como nuevo",
            89: "Como nuevo",
            90: "Nuevo",
            100: "Nuevo",
        }
        for score, expected_label in expected_boundaries.items():
            with self.subTest(score=score):
                self.assertEqual(map_score_to_condition_label(score), expected_label)

    def test_condition_score_clamping_invariant(self) -> None:
        """Checklist #2: Clamping strictly to [0, 100] and label synchronization."""
        self.assertEqual(clamp_condition_score(-25), 0)
        self.assertEqual(clamp_condition_score(145), 100)

        res_low = VisionAnalysisResult(
            name="iPhone X",
            category="Telefonía",
            brand="Apple",
            model="A1901",
            condition_score=-10,
            condition_label="Nuevo",
            condition_reasoning="Pantalla rota para repuestos.",
            seo_title="iPhone X para piezas",
            seo_description="Se vende iPhone X para piezas o reparación.",
        )
        self.assertEqual(res_low.condition_score, 0)
        self.assertEqual(res_low.condition_label, "Para piezas")

    def test_pillow_image_processor_resizes_and_extracts_metrics(self) -> None:
        """Verifies Base64 Data URL decoding, resizing <= 896px, and color/brightness metrics."""
        data_url = _create_test_data_url(1600, 1200, (245, 245, 250))
        raw_img = decode_image_source(data_url)
        enhanced, metrics = prepare_and_inspect_image(raw_img, max_dimension_px=896)

        self.assertLessEqual(max(enhanced.size), 896)
        self.assertEqual(metrics.width, 1600)
        self.assertEqual(metrics.height, 1200)
        self.assertEqual(metrics.color_name_es, "Blanco")
        self.assertGreater(metrics.brightness, 200.0)
        self.assertTrue(len(metrics.optimized_jpeg_b64) > 100)

    def test_ollama_model_selection_prefers_high_precision_models(self) -> None:
        """Verifies priority selection on Matías's 16GB Mac using official Ollama tags."""
        provider = OllamaVisionProvider(model_name="llama3.2-vision")
        installed = ["moondream", "minicpm-v:8b", "llava:7b"]
        chosen = provider._pick_best_installed_model(installed)
        self.assertEqual(chosen, "minicpm-v:8b")

    def test_orchestrator_normalizes_mock_vlm_and_truncates_seo_title(self) -> None:
        """Checklist #4: SEO title <= 65 chars and enriched Spanish SEO description."""
        data_url = _create_test_data_url(800, 600)
        orchestrator = ResilientVisionOrchestrator(providers=[_MockMacOllamaProvider()], timeout_sec=1.0)
        result = asyncio.run(orchestrator.analyze_photo(data_url))

        self.assertEqual(result.source, "ollama_local")
        self.assertEqual(result.condition_score, 94)
        self.assertEqual(result.condition_label, "Nuevo")
        self.assertLessEqual(len(result.seo_title), SEO_TITLE_MAX_LENGTH)
        self.assertIn("#sony", result.seo_description.lower())

    def test_orchestrator_fallback_under_sla_when_mac_offline(self) -> None:
        """Checklist #3: Automatic fallback in < 3.5s if remote node fails or times out."""
        data_url = _create_test_data_url(900, 700)
        orchestrator = ResilientVisionOrchestrator(
            providers=[_SlowFailingProvider(), DeterministicVisionProvider()],
            timeout_sec=0.15,
        )
        result = asyncio.run(orchestrator.analyze_photo(data_url, user_hint="Nintendo Switch OLED"))

        self.assertEqual(result.source, "deterministic_fallback")
        self.assertEqual(result.brand, "Nintendo")
        self.assertLess(result.latency_ms or 9999, 1000)
        self.assertLessEqual(len(result.seo_title), SEO_TITLE_MAX_LENGTH)


if __name__ == "__main__":
    unittest.main()
