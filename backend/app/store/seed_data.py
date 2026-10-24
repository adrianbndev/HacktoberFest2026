"""Datos de demo: perfil inicial desde la cuenta de Google y 3 productos con histórico de 3 escaneos (MOD-00 §3)."""
import base64
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from urllib.parse import quote

from app.mcp.pricing_math import triplet_from_base
from app.models.domain import InventoryItem, MarketListingSample, PricePoint, UserProfile

PLATFORMS = ["wallapop", "vinted", "milanuncios", "ebay"]
SEARCH_URLS = {
    "wallapop": "https://es.wallapop.com/app/search?keywords={}",
    "vinted": "https://www.vinted.es/catalog?search_text={}",
    "milanuncios": "https://www.milanuncios.com/anuncios/?s={}",
    "ebay": "https://www.ebay.es/sch/i.html?_nkw={}",
}
LISTING_PRICE_FACTORS = {"wallapop": 0.95, "vinted": 0.9, "milanuncios": 1.0, "ebay": 1.1}
DEFAULT_CITY = "Madrid"
DEFAULT_FAVORITE_LANGUAGES = ["TypeScript", "Python"]
PHOTOS_DIR = Path(__file__).parent / "demo_photos"  # fotos libres de Wikimedia Commons (ver CREDITS.md)

# (foto, nombre, categoría, marca, modelo, salud, etiqueta, diagnóstico, título SEO,
#  P_base en €, variación % entre escaneos, estado). Una subida, una bajada y uno estable para el Nivel 2.
DEMO_ITEMS = [
    ("switch-oled.jpg", "Nintendo Switch OLED 64GB Blanca", "Consolas y Videojuegos", "Nintendo",
     "Switch OLED HEG-001", 88, "Como nuevo", "Pantalla sin arañazos y Joy-Con sin drift; leve marca de uso en el dock.",
     "Nintendo Switch OLED Blanca 64GB como nueva + dock", 225, 4, "listed"),
    ("iphone-13.jpg", "iPhone 13 128GB Blanco estrella", "Móviles y Telefonía", "Apple", "iPhone 13 A2633",
     76, "Buen estado", "Batería al 86 % y pequeños roces en el marco; pantalla intacta.",
     "iPhone 13 128GB Blanco estrella libre · batería 86 %", 340, -3, "in_stock"),
    ("sony-wh-1000xm3.jpg", "Sony WH-1000XM3 Negros", "Audio y Sonido", "Sony", "WH-1000XM3", 82, "Como nuevo",
     "Almohadillas en buen estado y funda original; sin golpes visibles.",
     "Sony WH-1000XM3 cancelación de ruido + funda", 110, 0, "in_stock"),
]


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _svg_data_url(label: str, color: str) -> str:
    """Imagen SVG embebida (sin red): la demo nunca depende de un CDN de imágenes."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
        f'<rect width="120" height="120" fill="{color}"/>'
        '<text x="60" y="80" font-size="56" text-anchor="middle" font-family="sans-serif" fill="#fff">'
        f"{label}</text></svg>"
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


@cache
def _photo_data_url(filename: str) -> str:
    """Foto JPEG embebida como data URL (≤ 800 px, < 60 KB): cabe en el documento de Firestore."""
    return "data:image/jpeg;base64," + base64.b64encode((PHOTOS_DIR / filename).read_bytes()).decode()


def new_profile(uid: str, name: str, email: str | None, picture: str | None) -> UserProfile:
    """Perfil del primer acceso a partir de la cuenta de Google; ciudad y lenguajes se podrán editar."""
    return UserProfile(
        id=uid, name=name, email=email, role="Vendedor de segunda mano",
        avatar_url=picture or _svg_data_url(name[:1].upper() or "?", "#8b5cf6"),
        city=DEFAULT_CITY, favorite_languages=DEFAULT_FAVORITE_LANGUAGES, created_at=_iso(_now()),
    )


def _item(index: int, row: tuple, uid: str, city: str, now: datetime) -> InventoryItem:
    photo, name, category, brand, model, score, label, reasoning, seo_title, base, drift, status = row
    history = []
    for days_ago in (2, 1, 0):
        price_min, price_avg, price_max = triplet_from_base(base * (1 - days_ago * drift / 100), score)
        history.append(PricePoint(
            timestamp=_iso(now - timedelta(days=days_ago)), price_min=price_min, price_avg=price_avg,
            price_max=price_max, sample_size=18 + (index * 7 + days_ago) % 23, platforms=PLATFORMS,
        ))
    current, previous = history[-1], history[-2]
    delta_eur = current.price_avg - previous.price_avg
    query = quote(" ".join(name.split()[:4]))
    return InventoryItem(
        id=f"demo-{index + 1}", user_id=uid, photo_url=_photo_data_url(photo),
        name=name, category=category, brand=brand, model=model,
        condition_score=score, condition_label=label, condition_reasoning=reasoning,
        seo_title=seo_title,
        seo_description=(
            f"✅ {name} · Estado: {label} ({score} %).\n🔍 {reasoning}\n"
            f"📦 Envío por Wallapop o entrega en mano en {city}.\n💬 ¡Escríbeme sin compromiso!"
        ),
        price_min=current.price_min, price_avg=current.price_avg, price_max=current.price_max,
        price_trend="up" if delta_eur > 0 else "down" if delta_eur < 0 else "stable",
        price_delta_percent=round(delta_eur / previous.price_avg * 100, 1), price_delta_eur=delta_eur,
        price_history=history,
        comparable_listings=[
            MarketListingSample(title=name, price=round(current.price_avg * factor), platform=platform,
                                condition=label, url=SEARCH_URLS[platform].format(query))
            for platform, factor in LISTING_PRICE_FACTORS.items()
        ],
        status=status, created_at=history[0].timestamp, last_updated_at=current.timestamp,
    )


def demo_items(uid: str, city: str = DEFAULT_CITY) -> list[InventoryItem]:
    now = _now()
    return [_item(index, row, uid, city, now) for index, row in enumerate(DEMO_ITEMS)]
