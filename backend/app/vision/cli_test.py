"""Standalone CLI tool to test Vision Recognition without needing the Web UI."""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

# Ensure backend root is in sys.path and load .env automatically when invoked directly
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_ENV_FILE = _REPO_ROOT / ".env"
if _ENV_FILE.is_file():
    import os
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _clean = _line.strip()
        if _clean and not _clean.startswith("#") and "=" in _clean:
            _k, _v = _clean.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from app.vision.image_processor import decode_image_source, prepare_and_inspect_image  # noqa: E402
from app.vision.ollama_provider import OllamaVisionProvider  # noqa: E402
from app.vision.orchestrator import ResilientVisionOrchestrator  # noqa: E402


def _generate_synthetic_product_photo(preset: str) -> bytes:
    """Generates a realistic test image using Pillow when no local photo is passed."""
    presets = {
        "switch": ((235, 238, 242), (220, 40, 45), "NINTENDO SWITCH OLED 64GB HEG-001"),
        "iphone": ((48, 50, 56), (90, 95, 110), "APPLE IPHONE 14 PRO 128GB SPACE BLACK"),
        "macbook": ((210, 214, 220), (40, 45, 55), "APPLE MACBOOK AIR M2 13.6 A2681"),
        "sony": ((35, 36, 40), (180, 155, 110), "SONY WH-1000XM5 WIRELESS ANC"),
        "canon": ((30, 30, 35), (160, 40, 40), "CANON EOS 2000D DSLR EF-S 18-55MM"),
        "keychron": ((40, 42, 48), (210, 140, 60), "KEYCHRON K2 V2 MECHANICAL KEYBOARD"),
    }
    bg_rgb, accent_rgb, label_text = presets.get(preset.lower(), presets["switch"])

    img = Image.new("RGB", (1200, 900), color=bg_rgb)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((220, 160, 980, 740), radius=36, fill=accent_rgb, outline=(20, 20, 20), width=6)
    draw.rectangle((290, 220, 910, 640), fill=(248, 248, 250), outline=(60, 60, 60), width=4)
    for offset in range(260, 620, 45):
        draw.line((320, offset, 880, offset), fill=(180, 185, 195), width=2)
    draw.text((340, 410), label_text, fill=(15, 15, 20))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


async def _run_cli(args: argparse.Namespace) -> int:
    ollama_provider = OllamaVisionProvider(
        base_url=args.ollama_url,
        model_name=args.model,
        request_timeout_sec=args.timeout,
    )

    if args.check_node:
        status = await ollama_provider.check_node_health(force=True)
        print("🔌 Estado del Nodo de Visión (Mac de Matías / Ollama):")
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0 if status.get("reachable") else 1

    if args.image:
        img_path = Path(args.image)
        if not img_path.is_file():
            print(f"❌ No existe el archivo de imagen: {img_path}")
            return 1
        source: str | bytes | Path = img_path
        default_hint = args.hint or img_path.stem.replace("_", " ").replace("-", " ")
    else:
        source = _generate_synthetic_product_photo(args.sample)
        default_hint = args.hint or args.sample

    pil_img = decode_image_source(source)
    _, metrics = prepare_and_inspect_image(pil_img)
    print("🖼️  Métricas Físicas Locales (Pillow <20ms):")
    print(
        f"   • Dimensiones: {metrics.width}x{metrics.height} (aspect={metrics.aspect_ratio})\n"
        f"   • Color central: {metrics.color_name_es} RGB{metrics.dominant_rgb}\n"
        f"   • Brillo: {metrics.brightness}/255 | Contraste: {metrics.contrast} | Nitidez: {metrics.sharpness}\n"
        f"   • Payload JPEG optimizado: {len(metrics.optimized_jpeg_b64) // 1024} KB"
    )

    orchestrator = ResilientVisionOrchestrator(
        providers=[ollama_provider],
        timeout_sec=args.timeout,
    )
    result = await orchestrator.analyze_photo(photo_source=source, user_hint=default_hint)

    if ollama_provider.last_error:
        print(f"\n⚠️  Aviso del nodo Ollama (se activó fallback local): {ollama_provider.last_error}")

    print("\n✅ Resultado Estructurado para Pre-rellenar el Formulario (VisionAnalysisResult):")
    print(json.dumps(result.model_dump(by_alias=True), indent=2, ensure_ascii=False))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI de prueba para el Módulo de Visión (MOD-03)")
    parser.add_argument("image", nargs="?", help="Ruta a una foto real (.jpg, .png, .webp)")
    parser.add_argument("--sample", default="switch", choices=["switch", "iphone", "macbook", "sony", "canon", "keychron"])
    parser.add_argument("--hint", default=None, help="Pista opcional (ej. 'switch oled')")
    parser.add_argument("--ollama-url", default=None, help="URL de Ollama")
    parser.add_argument("--model", default=None, help="Modelo VLM")
    parser.add_argument("--timeout", type=float, default=2.5, help="Timeout máximo en segundos (default: 2.5)")
    parser.add_argument("--check-node", action="store_true", help="Solo comprueba conexión con Ollama")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run_cli(args)))


if __name__ == "__main__":
    main()
