"""Datos semilla de la demo: 4 perfiles con 3 artículos cada uno e histórico de 3 escaneos (MOD-00 §3)."""
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from app.mcp.pricing_math import triplet_from_base
from app.models.sdd import AppStoreState, InventoryItem, MarketListingSample, PricePoint, UserProfile

PLATFORMS = ["wallapop", "vinted", "milanuncios", "ebay"]
SEARCH_URLS = {
    "wallapop": "https://es.wallapop.com/app/search?keywords={}",
    "vinted": "https://www.vinted.es/catalog?search_text={}",
    "milanuncios": "https://www.milanuncios.com/anuncios/?s={}",
    "ebay": "https://www.ebay.es/sch/i.html?_nkw={}",
}
LISTING_PRICE_FACTORS = {"wallapop": 0.95, "vinted": 0.9, "milanuncios": 1.0, "ebay": 1.1}

# (id, nombre, rol, ciudad, lenguajes favoritos, color del avatar)
PROFILES = [
    ("ales", "Ales", "Frontend & UX · Track A", "Madrid", ["TypeScript", "React", "Next.js"], "#8b5cf6"),
    ("adri", "Adri", "Visión IA & Sync Móvil · Track B", "Barcelona", ["Python", "TypeScript", "AI/Vision"], "#06b6d4"),
    ("matias", "Matías", "MCP Stealth & LifeOS · Track C", "Valencia", ["Rust", "TypeScript", "Node.js"], "#f59e0b"),
    ("jurado", "Jurado", "Jurado Hacktoberfest 2026", "Madrid", ["TypeScript", "Python", "Go"], "#10b981"),
]

# (usuario, emoji, color, nombre, categoría, marca, modelo, salud, etiqueta, diagnóstico, título SEO,
#  P_base en €, variación % entre escaneos, estado)
ITEMS = [
    ("ales", "🎮", "#ef4444", "Nintendo Switch OLED 64GB Blanca", "Consolas y Videojuegos", "Nintendo",
     "Switch OLED HEG-001", 88, "Como nuevo", "Pantalla sin arañazos y Joy-Con sin drift; leve marca de uso en el dock.",
     "Nintendo Switch OLED Blanca 64GB como nueva + dock", 225, 4, "listed"),
    ("ales", "📱", "#334155", "iPhone 13 128GB Medianoche", "Móviles y Telefonía", "Apple", "iPhone 13 A2633",
     76, "Buen estado", "Batería al 86 % y pequeños roces en el marco; pantalla intacta.",
     "iPhone 13 128GB Medianoche libre · batería 86 %", 340, -3, "in_stock"),
    ("ales", "🎧", "#0f172a", "Sony WH-1000XM4 Negros", "Audio", "Sony", "WH-1000XM4", 82, "Como nuevo",
     "Almohadillas en buen estado y funda original; sin golpes visibles.",
     "Sony WH-1000XM4 cancelación de ruido + funda", 150, 0, "in_stock"),
    ("adri", "💻", "#64748b", "MacBook Air M1 8GB 256GB Gris espacial", "Informática y Portátiles", "Apple",
     "MacBook Air M1 A2337", 79, "Buen estado", "Micro-arañazos en la tapa; teclado y pantalla perfectos, 212 ciclos.",
     "MacBook Air M1 8GB 256GB · 212 ciclos de batería", 520, 3, "listed"),
    ("adri", "📷", "#1e293b", "Canon EOS 2000D + 18-55mm", "Cámaras y Fotografía", "Canon", "EOS 2000D", 72,
     "Buen estado", "Desgaste leve en la empuñadura; objetivo sin hongos ni rayas.",
     "Canon EOS 2000D + objetivo 18-55 · ideal para empezar", 290, -4, "in_stock"),
    ("adri", "🖥️", "#0ea5e9", "Monitor LG 27\" 4K UHD", "Monitores", "LG", "27UL500-W", 85, "Como nuevo",
     "Panel sin píxeles muertos y peana sin marcas; incluye cable HDMI.",
     "Monitor LG 27 pulgadas 4K UHD IPS HDR10", 185, 2, "reserved"),
    ("matias", "🚲", "#16a34a", "Bicicleta Orbea MX 29 30 talla L", "Bicicletas", "Orbea", "MX 29 30", 58,
     "Desgaste visible", "Desconchones en la pintura del cuadro y transmisión con uso; frenos revisados.",
     "Bicicleta MTB Orbea MX 29 talla L revisada", 410, -2, "in_stock"),
    ("matias", "⌨️", "#a855f7", "Teclado mecánico Keychron K2 V2", "Periféricos", "Keychron", "K2 V2 Gateron Brown",
     91, "Nuevo", "Prácticamente sin uso, keycaps sin brillo y caja original.",
     "Keychron K2 V2 mecánico inalámbrico Gateron Brown", 72, 5, "listed"),
    ("matias", "🕹️", "#f8fafc", "PlayStation 5 Slim Digital 1TB", "Consolas y Videojuegos", "Sony",
     "PS5 Slim CFI-2016", 84, "Como nuevo", "Carcasa impecable y DualSense sin drift; con caja.",
     "PS5 Slim Digital 1TB como nueva + DualSense", 335, 3, "in_stock"),
    ("jurado", "🧥", "#2563eb", "Chaqueta vaquera Levi's Trucker vintage talla M", "Ropa vintage", "Levi's",
     "Trucker 70500", 68, "Buen estado", "Lavado desgastado de origen y costuras firmes; sin roturas.",
     "Chaqueta vaquera Levi's Trucker vintage talla M", 48, 6, "listed"),
    ("jurado", "🎵", "#e2e8f0", "AirPods Pro 2 USB-C", "Audio", "Apple", "AirPods Pro 2 A3047", 93, "Nuevo",
     "Precintados con ticket de compra y garantía Apple vigente.",
     "AirPods Pro 2 USB-C precintados con garantía", 175, -3, "in_stock"),
    ("jurado", "📚", "#78716c", "Kindle Paperwhite 11ª gen 16GB", "Libros y E-readers", "Amazon",
     "Paperwhite M2L3EK", 35, "Para piezas", "Pantalla con líneas fijas tras un golpe; enciende y carga.",
     "Kindle Paperwhite 11ª gen para piezas o reparar", 105, 0, "in_stock"),
]


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _svg_data_url(label: str, color: str) -> str:
    """Imagen SVG embebida (sin red): la demo nunca depende de un CDN de imágenes."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
        f'<rect width="120" height="120" fill="{color}"/>'
        '<text x="60" y="80" font-size="56" text-anchor="middle" font-family="sans-serif" fill="#fff">'
        f"{label}</text></svg>"
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


def _item(index: int, row: tuple, now: datetime, cities: dict[str, str]) -> InventoryItem:
    user, emoji, color, name, category, brand, model, score, label, reasoning, seo_title, base, drift, status = row
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
        id=f"seed-{user}-{index % 3 + 1}", user_id=user, photo_url=_svg_data_url(emoji, color),
        name=name, category=category, brand=brand, model=model,
        condition_score=score, condition_label=label, condition_reasoning=reasoning,
        seo_title=seo_title,
        seo_description=(
            f"✅ {name} · Estado: {label} ({score} %).\n🔍 {reasoning}\n"
            f"📦 Envío por Wallapop o entrega en mano en {cities[user]}.\n💬 ¡Escríbeme sin compromiso!"
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


def build_seed_state() -> AppStoreState:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    profiles = {
        user: UserProfile(id=user, name=name, role=role, avatar_url=_svg_data_url(name[0], color), city=city,
                          favorite_languages=languages, created_at=_iso(now - timedelta(days=30)))
        for user, name, role, city, languages, color in PROFILES
    }
    cities = {user: profile.city for user, profile in profiles.items()}
    return AppStoreState(
        active_user_id="jurado", profiles=profiles,
        inventory=[_item(index, row, now, cities) for index, row in enumerate(ITEMS)],
        capture_sessions={}, notifications=[], calendar_events=[], last_updated_at=_iso(now),
    )
