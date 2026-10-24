"""Catalog templates and heuristic category/brand definitions for vision fallback."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogItemTemplate:
    keywords: tuple[str, ...]
    name: str
    category: str
    brand: str
    model: str
    base_score: int


CATALOG_TEMPLATES: tuple[CatalogItemTemplate, ...] = (
    CatalogItemTemplate(
        keywords=("switch", "nintendo", "oled", "joycon", "consola"),
        name="Nintendo Switch OLED 64GB",
        category="Consolas y Videojuegos",
        brand="Nintendo",
        model="Switch OLED HEG-001",
        base_score=88,
    ),
    CatalogItemTemplate(
        keywords=("iphone", "apple", "ios", "pro", "movil", "móvil", "telefono"),
        name="Apple iPhone 14 Pro 128GB",
        category="Móviles y Telefonía",
        brand="Apple",
        model="iPhone 14 Pro A2890",
        base_score=85,
    ),
    CatalogItemTemplate(
        keywords=("macbook", "portatil", "portátil", "laptop", "mac", "air", "m1", "m2", "m3"),
        name="MacBook Air M2 13.6 8GB/256GB",
        category="Informática y Portátiles",
        brand="Apple",
        model="MacBook Air M2 A2681",
        base_score=91,
    ),
    CatalogItemTemplate(
        keywords=("sony", "wh-1000xm5", "xm5", "xm4", "auriculares", "cascos", "audio"),
        name="Auriculares Sony WH-1000XM5 ANC",
        category="Audio",
        brand="Sony",
        model="WH-1000XM5",
        base_score=84,
    ),
    CatalogItemTemplate(
        keywords=("ps5", "playstation", "dualsense", "mando", "consola sony"),
        name="PlayStation 5 Edición Disco 825GB",
        category="Consolas y Videojuegos",
        brand="Sony",
        model="PS5 CFI-1216A",
        base_score=86,
    ),
    CatalogItemTemplate(
        keywords=("canon", "eos", "camara", "cámara", "reflex", "réflex", "fotografia"),
        name="Canon EOS 2000D + 18-55mm",
        category="Cámaras y Fotografía",
        brand="Canon",
        model="EOS 2000D",
        base_score=80,
    ),
    CatalogItemTemplate(
        keywords=("monitor", "pantalla", "lg", "4k", "ips", "display"),
        name="Monitor LG 27\" 4K UHD IPS",
        category="Monitores",
        brand="LG",
        model="27UL500-W",
        base_score=86,
    ),
    CatalogItemTemplate(
        keywords=("bicicleta", "bici", "orbea", "mtb", "ciclismo"),
        name="Bicicleta Orbea MX 29 Talla L",
        category="Bicicletas",
        brand="Orbea",
        model="MX 29 30",
        base_score=75,
    ),
    CatalogItemTemplate(
        keywords=("keychron", "teclado", "keyboard", "mecanico", "mecánico"),
        name="Teclado mecánico Keychron K2 V2",
        category="Periféricos",
        brand="Keychron",
        model="K2 V2 Gateron Brown",
        base_score=90,
    ),
    CatalogItemTemplate(
        keywords=("ipad", "tablet", "tableta", "air"),
        name="Apple iPad Air 10.9 64GB",
        category="Informática y Portátiles",
        brand="Apple",
        model="iPad Air 5ª Gen A2588",
        base_score=87,
    ),
    CatalogItemTemplate(
        keywords=("coche", "auto", "vehiculo", "vehículo", "seat", "leon", "león", "ibiza", "volkswagen", "golf", "bmw", "toyota", "audi"),
        name="SEAT León 1.5 TSI 130CV Style",
        category="Motor y Vehículos",
        brand="SEAT",
        model="León 1.5 TSI",
        base_score=84,
    ),
    CatalogItemTemplate(
        keywords=("silla", "mesa", "sofa", "sofá", "mueble", "mobiliario", "butaca", "armario", "madera"),
        name="Silla de comedor en madera maciza",
        category="Mobiliario y Decoración",
        brand="Artesanal",
        model="Clásica Madera",
        base_score=85,
    ),
)

KNOWN_BRANDS: tuple[str, ...] = (
    "Apple", "Sony", "Nintendo", "Canon", "LG", "Samsung", "Orbea", "Keychron",
    "Bosch", "Dell", "Lenovo", "HP", "Xiaomi", "Asus", "Logitech", "Microsoft",
    "Nike", "Adidas", "Fender", "Yamaha", "Sennheiser", "Bose", "Dyson", "Cecotec",
    "SEAT", "Volkswagen", "BMW", "Audi", "Mercedes", "Toyota", "Renault", "Peugeot", "Ford", "Tesla", "IKEA",
)


def synthesize_template_from_hint(hint: str) -> CatalogItemTemplate:
    """Synthesizes a clean template when user_hint does not match preset keywords."""
    words = [w for w in hint.strip().split() if w]
    brand = words[0].capitalize() if words else "Genérica"
    low = hint.lower()
    for b in KNOWN_BRANDS:
        if b.lower() in low.split():
            brand = b
            break

    model_words = [w for w in words if w.lower() != brand.lower()]
    model = " ".join(model_words) if model_words else "Estándar"

    if any(k in low for k in ("coche", "auto", "vehiculo", "vehículo", "moto", "seat", "bmw", "audi", "volkswagen", "toyota", "mercedes", "renault", "peugeot", "ford", "tesla")):
        category = "Motor y Vehículos"
    elif any(k in low for k in ("consola", "juego", "play", "game", "xbox", "nintendo")):
        category = "Consolas y Videojuegos"
    elif any(k in low for k in ("movil", "móvil", "telefono", "phone", "smartphone", "iphone")):
        category = "Móviles y Telefonía"
    elif any(k in low for k in ("portatil", "portátil", "laptop", "pc", "ordenador", "macbook")):
        category = "Informática y Portátiles"
    elif any(k in low for k in ("audio", "auricular", "altavoz", "sound", "micro")):
        category = "Audio"
    elif any(k in low for k in ("foto", "camara", "cámara", "lente", "objetivo")):
        category = "Cámaras y Fotografía"
    elif any(k in low for k in ("bici", "bicicleta", "patinete", "deporte")):
        category = "Bicicletas"
    elif any(k in low for k in ("teclado", "raton", "ratón", "mouse", "monitor")):
        category = "Periféricos"
    elif any(k in low for k in ("herramienta", "taladro", "sierra", "lijadora", "bricolaje")):
        category = "Bricolaje y Herramientas"
    elif any(k in low for k in ("silla", "mesa", "sofa", "sofá", "mueble", "mobiliario", "armario", "estanteria", "estantería", "butaca")):
        category = "Mobiliario y Decoración"
    elif any(k in low for k in ("cafetera", "aspirador", "robot", "hogar", "electrodoméstico")):
        category = "Hogar y Electrodomésticos"
    elif any(k in low for k in ("zapatilla", "deportiva", "ropa", "chaqueta", "moda")):
        category = "Moda y Accesorios"
    elif any(k in low for k in ("guitarra", "bajo", "piano", "instrumento")):
        category = "Instrumentos Musicales"
    else:
        category = "Segunda Mano y Ocasión"

    return CatalogItemTemplate(
        keywords=(hint.lower(),),
        name=hint.strip(),
        category=category,
        brand=brand,
        model=model,
        base_score=85,
    )
