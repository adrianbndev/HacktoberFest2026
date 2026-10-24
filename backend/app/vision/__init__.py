"""Vision AI package (MOD-03 — Track B)."""

from app.vision.fallback_provider import DeterministicVisionProvider
from app.vision.image_processor import decode_image_source, prepare_and_inspect_image
from app.vision.ollama_provider import PREFERRED_MAC_VISION_MODELS, OllamaVisionProvider
from app.vision.openai_provider import OpenAIVisionProvider
from app.vision.orchestrator import ResilientVisionOrchestrator
from app.vision.protocol import (
    ImageVisualMetrics,
    VisionProviderProtocol,
    build_seo_description,
    build_seo_title,
)

__all__ = [
    "PREFERRED_MAC_VISION_MODELS",
    "DeterministicVisionProvider",
    "ImageVisualMetrics",
    "OllamaVisionProvider",
    "OpenAIVisionProvider",
    "ResilientVisionOrchestrator",
    "VisionProviderProtocol",
    "build_seo_description",
    "build_seo_title",
    "decode_image_source",
    "prepare_and_inspect_image",
]
