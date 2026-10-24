"""Dynamic category-specific field schemas and attribute enrichment for Vision AI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from app.models.sdd import VisionDynamicField

FieldKind = Literal["text", "select", "number"]
FieldSpec = tuple[str, str, FieldKind, list[str], str]

_DOTENV_LOADED = False


def ensure_dotenv_loaded() -> None:
    """Loads root .env into os.environ once so FastAPI/Uvicorn reads LAN Ollama settings."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[3] / ".env"):
        if candidate.is_file():
            for raw_line in candidate.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = val
            break


CATEGORY_FIELD_SPECS: dict[str, list[FieldSpec]] = {
    "motor": [
        ("fuelType", "Tipo de combustible", "select", ["Gasolina", "Diésel", "Híbrido (HEV)", "Híbrido Enchufable (PHEV)", "Eléctrico (EV)", "GLP / GNC"], "Gasolina"),
        ("transmission", "Cambio / Transmisión", "select", ["Manual", "Automático"], "Manual"),
        ("bodyType", "Carrocería / Tipo", "select", ["Turismo / Compacto", "SUV / Todoterreno", "Berlina", "Familiar", "Coupé / Deportivo", "Furgoneta", "Motocicleta / Scooter"], "Turismo / Compacto"),
        ("year", "Año de matriculación", "text", [], "Ej. 2020"),
        ("mileageKm", "Kilometraje (km)", "text", [], "Ej. 85.000 km"),
        ("horsepower", "Potencia (CV)", "text", [], "Ej. 120 CV"),
        ("environmentalBadge", "Distintivo ambiental DGT", "select", ["C (Verde)", "ECO", "0 Emisiones (Azul)", "B (Amarilla)", "Sin etiqueta"], "C (Verde)"),
        ("color", "Color exterior", "text", [], "Ej. Blanco, Negro, Rojo"),
    ],
    "moviles": [
        ("storage", "Capacidad de almacenamiento", "select", ["64 GB", "128 GB", "256 GB", "512 GB", "1 TB", "32 GB"], "128 GB"),
        ("ram", "Memoria RAM", "select", ["4 GB", "6 GB", "8 GB", "12 GB", "16 GB"], "8 GB"),
        ("batteryHealth", "Salud de batería (%)", "text", [], "Ej. 88%"),
        ("color", "Color / Acabado", "text", [], "Ej. Negro espacial, Plata"),
        ("carrierLock", "Estado de operador", "select", ["Libre de fábrica", "Vinculado a operador"], "Libre de fábrica"),
        ("screenStatus", "Estado de pantalla", "select", ["Impecable sin marcas", "Micro-arañazos leves", "Con cristal templado", "Grieta o marca visible"], "Impecable sin marcas"),
        ("accessories", "Caja y accesorios", "select", ["Caja y cable original", "Con cargador y funda", "Solo teléfono", "Completo con factura"], "Caja y cable original"),
    ],
    "consolas": [
        ("edition", "Edición / Capacidad", "select", ["OLED 64 GB", "Estándar 32 GB", "Edición Disco (825 GB / 1 TB)", "Edición Digital", "Portátil / Lite", "Retro / Coleccionista"], "OLED 64 GB"),
        ("controllers", "Mandos incluidos", "select", ["1 mando original", "2 mandos originales", "Pareja Joy-Con original", "Sin mandos"], "Pareja Joy-Con original"),
        ("packaging", "Caja y dock/cables", "select", ["Completa con caja y cables", "Con cables originales sin caja", "Solo consola"], "Completa con caja y cables"),
        ("includedGames", "Juegos incluidos", "text", [], "Ej. Ninguno, Mario Kart 8..."),
        ("color", "Color / Edición", "text", [], "Ej. Blanca, Neón"),
    ],
    "informatica": [
        ("processor", "Procesador / Chip", "text", [], "Ej. Apple M2, Intel Core i7, Ryzen 7"),
        ("ram", "Memoria RAM", "select", ["8 GB", "16 GB", "32 GB", "64 GB", "4 GB"], "8 GB"),
        ("storage", "Almacenamiento SSD", "select", ["256 GB SSD", "512 GB SSD", "1 TB SSD", "2 TB SSD", "128 GB"], "256 GB SSD"),
        ("screenSize", "Tamaño de pantalla", "select", ["13.3 - 13.6 pulgadas", "14 pulgadas", "15.6 pulgadas", "16 pulgadas", "10.9 - 11 pulgadas", "24 - 27 pulgadas"], "13.3 - 13.6 pulgadas"),
        ("keyboardLayout", "Teclado / Distribución", "select", ["Español (con Ñ)", "Inglés (US/UK)", "No aplica (Monitor/Tablet)"], "Español (con Ñ)"),
        ("color", "Color", "text", [], "Ej. Gris espacial, Plata"),
    ],
    "audio": [
        ("connectivity", "Conectividad", "select", ["Bluetooth inalámbrico", "Bluetooth + Cable Jack", "Solo cable", "Wi-Fi / Multiroom"], "Bluetooth + Cable Jack"),
        ("noiseCancelling", "Cancelación de ruido (ANC)", "select", ["Sí, ANC activa", "Aislamiento pasivo", "No"], "Sí, ANC activa"),
        ("formFactor", "Formato de audio", "select", ["Diadema (Over-Ear)", "In-Ear / True Wireless", "Altavoz portátil", "Equipo de estudio / Hi-Fi"], "Diadema (Over-Ear)"),
        ("accessories", "Estuche y cables", "select", ["Con estuche y cables originales", "Con caja original completa", "Solo dispositivo"], "Con estuche y cables originales"),
        ("color", "Color", "text", [], "Ej. Negro, Plata"),
    ],
    "camaras": [
        ("cameraType", "Tipo de cámara", "select", ["Cámara Réflex (DSLR)", "Mirrorless / Sin espejo", "Compacta Digital", "Objetivo / Lente", "Cámara de acción"], "Cámara Réflex (DSLR)"),
        ("lensIncluded", "Objetivo incluido", "text", [], "Ej. Kit 18-55mm IS, Solo cuerpo"),
        ("shutterCount", "Disparos / Uso", "select", ["Poco uso (< 10.000 disparos)", "Uso medio (10.000 - 30.000)", "Más de 30.000 disparos", "Desconocido"], "Poco uso (< 10.000 disparos)"),
        ("accessories", "Batería y accesorios", "select", ["Batería, cargador y correa", "Con funda y tarjeta SD", "Solo cuerpo"], "Batería, cargador y correa"),
    ],
    "bicicletas": [
        ("bikeType", "Tipo de vehículo", "select", ["MTB / Montaña", "Carretera", "Urbana / Paseo", "Gravel", "Bicicleta eléctrica (E-Bike)", "Patinete eléctrico"], "MTB / Montaña"),
        ("frameSize", "Talla del cuadro", "select", ["Talla S", "Talla M", "Talla L", "Talla XL", "Talla única"], "Talla L"),
        ("wheelSize", "Tamaño de rueda", "select", ["29 pulgadas", "27.5 pulgadas", "26 pulgadas", "700c / 28 pulgadas", "8.5 - 10 pulgadas"], "29 pulgadas"),
        ("frameMaterial", "Material del cuadro", "select", ["Aluminio", "Fibra de carbono", "Acero"], "Aluminio"),
        ("color", "Color", "text", [], "Ej. Negro/Rojo"),
    ],
    "mobiliario": [
        ("material", "Material principal", "select", ["Madera maciza", "Madera / Melamina", "Metal / Acero", "Tapizado / Tela", "Piel / Polipiel", "Cristal", "Plástico / Polipropileno"], "Madera maciza"),
        ("style", "Estilo decorativo", "select", ["Moderno / Contemporáneo", "Nórdico / Escandinavo", "Clásico / Rústico", "Industrial", "Vintage / Retro"], "Clásico / Rústico"),
        ("dimensions", "Dimensiones aprox. (An x Fo x Al)", "text", [], "Ej. 50 x 50 x 85 cm"),
        ("assembly", "Entrega y montaje", "select", ["Se entrega montado", "Desmontable para transporte", "Requiere montaje"], "Se entrega montado"),
        ("color", "Color / Acabado", "text", [], "Ej. Roble, Nogal, Blanco"),
    ],
    "moda": [
        ("size", "Talla", "text", [], "Ej. M, L, 42 EU, Talla única"),
        ("material", "Material / Tejido", "select", ["Algodón / Textil", "Piel / Cuero", "Sintético / Técnico", "Vaquero / Denim", "Lana / Punto"], "Algodón / Textil"),
        ("authenticity", "Etiquetas / Caja", "select", ["Con etiquetas o caja original", "Sin etiquetas (Original)", "Con ticket de compra"], "Sin etiquetas (Original)"),
        ("color", "Color principal", "text", [], "Ej. Blanco, Negro, Azul"),
    ],
    "hogar": [
        ("applianceType", "Tipo de aparato", "select", ["Pequeño electrodoméstico", "Limpieza / Aspiración", "Cafetera / Cocina", "Climatización", "Bricolaje / Herramienta eléctrica"], "Pequeño electrodoméstico"),
        ("powerSource", "Alimentación / Potencia", "select", ["Cable eléctrico (220V)", "Batería recargable", "Manual / Sin motor"], "Cable eléctrico (220V)"),
        ("accessories", "Accesorios o maletín", "select", ["Completo con accesorios", "En caja o maletín original", "Solo aparato principal"], "Completo con accesorios"),
        ("color", "Color / Acabado", "text", [], "Ej. Acero, Blanco"),
    ],
}


def resolve_category_family(category: str, name: str, brand: str = "", model: str = "") -> str:
    """Determines the dynamic field schema family from category and product text."""
    blob = f"{category} {name} {brand} {model}".lower()
    if any(k in blob for k in ("coche", "auto", "vehículo", "vehiculo", "motor", "moto", "furgoneta", "suv", "berlina", "seat", "bmw", "audi", "mercedes", "volkswagen", "toyota", "renault", "peugeot", "ford", "hyundai", "kia", "tesla", "mazda", "nissan", "opel", "citroen", "fiat", "porsche", "honda", "yamaha")):
        return "motor"
    if any(k in blob for k in ("móvil", "movil", "telefon", "teléfono", "iphone", "smartphone", "galaxy", "xiaomi", "redmi", "pixel", "oneplus", "oppo", "realme")):
        return "moviles"
    if any(k in blob for k in ("consola", "videojuego", "switch", "playstation", "ps5", "ps4", "xbox", "joy-con", "joycon", "steam deck")):
        return "consolas"
    if any(k in blob for k in ("portátil", "portatil", "macbook", "laptop", "informática", "informatica", "ipad", "tablet", "monitor", "teclado", "periférico", "periferico", "pc", "ordenador")):
        return "informatica"
    if any(k in blob for k in ("audio", "auricular", "cascos", "altavoz", "wh-1000", "airpods", "sonido", "bose", "sennheiser")):
        return "audio"
    if any(k in blob for k in ("cámara", "camara", "fotograf", "eos", "canon", "nikon", "fujifilm", "réflex", "reflex", "dslr", "objetivo", "lente")):
        return "camaras"
    if any(k in blob for k in ("bici", "orbea", "mtb", "patinete", "ciclismo", "trek", "specialized")):
        return "bicicletas"
    if any(k in blob for k in ("silla", "mesa", "sofá", "sofa", "mueble", "mobiliario", "armario", "estantería", "estanteria", "butaca", "escritorio", "cama", "lámpara", "lampara", "decoración", "madera")):
        return "mobiliario"
    if any(k in blob for k in ("moda", "ropa", "zapatilla", "calzado", "chaqueta", "camiseta", "pantalón", "bolso", "reloj", "gafas", "nike", "adidas", "zara")):
        return "moda"
    return "hogar"


_KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "fuelType": ("combustible", "tipo de combustible", "motor", "fuel"),
    "transmission": ("transmision", "transmisión", "cambio", "caja de cambios"),
    "bodyType": ("carroceria", "carrocería", "tipo vehiculo", "segmento"),
    "year": ("anio", "año", "matriculacion", "año aproximado"),
    "mileageKm": ("kilometros", "kilómetros", "kilometraje", "km"),
    "horsepower": ("potencia", "cv", "caballos"),
    "environmentalBadge": ("etiqueta", "distintivo dgt", "etiqueta dgt"),
    "storage": ("almacenamiento", "capacidad", "memoria interna", "ssd", "gb"),
    "ram": ("memoria ram", "ram"),
    "batteryHealth": ("bateria", "batería", "salud bateria", "estado bateria"),
    "color": ("color", "acabado", "color exterior", "color principal"),
    "material": ("material", "material principal", "tejido"),
    "style": ("estilo", "estilo decorativo", "diseño"),
    "size": ("talla", "tamaño", "medidas"),
    "dimensions": ("dimensiones", "medidas", "tamaño"),
}


def build_dynamic_fields(
    category: str,
    name: str,
    brand: str,
    model: str,
    color_name_es: str,
    raw_attributes: dict[str, str] | None = None,
) -> list[VisionDynamicField]:
    """Builds pre-populated dynamic fields tailored to the detected product family."""
    family = resolve_category_family(category, name, brand, model)
    specs = CATEGORY_FIELD_SPECS.get(family, CATEGORY_FIELD_SPECS["hogar"])
    attrs = {k.lower().strip(): v.strip() for k, v in (raw_attributes or {}).items() if v and v.strip()}
    low_blob = f"{name} {model}".lower()
    fields: list[VisionDynamicField] = []

    for key, label, field_type, options, default_hint in specs:
        candidates = (key.lower(), label.lower(), *_KEY_ALIASES.get(key, ()))
        val = next((attrs[c] for c in candidates if c in attrs), "")
        if val.lower() in ("no especificado", "desconocido", "n/a", "none", "null", "sin especificar"):
            val = ""
        if not val:
            if key == "color":
                val = color_name_es
            elif key == "storage" and any(cap in low_blob for cap in ("64gb", "128gb", "256gb", "512gb", "1tb", "32gb")):
                for cap, fmt in (("32gb", "32 GB"), ("64gb", "64 GB"), ("128gb", "128 GB"), ("256gb", "256 GB"), ("512gb", "512 GB"), ("1tb", "1 TB")):
                    if cap in low_blob:
                        val = fmt if family != "informatica" else f"{fmt} SSD"
                        break
            elif key == "fuelType":
                if any(w in low_blob for w in ("tdi", "dci", "hdi", "diesel", "diésel")):
                    val = "Diésel"
                elif any(w in low_blob for w in ("híbrido", "hibrido", "hybrid", "hev")):
                    val = "Híbrido (HEV)"
                elif any(w in low_blob for w in ("eléctrico", "electrico", "ev", "tesla", "id.3", "id.4")):
                    val = "Eléctrico (EV)"
                else:
                    val = default_hint
            elif field_type == "select" and options:
                val = default_hint if default_hint in options else options[0]

        if field_type == "select" and val and val not in options:
            options = [val, *options]

        fields.append(
            VisionDynamicField(
                key=key,
                label=label,
                value=val,
                field_type=field_type,
                options=list(options),
                placeholder=default_hint if field_type != "select" else None,
            )
        )
    return fields
