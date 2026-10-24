# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Público principal:** el jurado y el resto de participantes de Hacktoberfest 2026, viendo una demo en directo de 3-5 minutos que presenta el propio equipo (Ales, Adri y Matías). Ven el dashboard en un proyector mientras un presentador hace la foto con su móvil.
- **Usuario que la demo representa:** una persona en España con objetos de segunda mano en casa que quiere saber cuánto valen y venderlos en Wallapop, Vinted, Milanuncios o eBay.

## Product Purpose

Tasar objetos de segunda mano con una foto. La Visión IA identifica el producto (nombre, marca, modelo, categoría) y su estado (`conditionScore` 0-100 y una de 5 etiquetas: Nuevo, Como nuevo, Buen estado, Desgaste visible, Para piezas), y escribe un título y una descripción listos para publicar. El motor MCP consulta 4 plataformas y devuelve 3 precios ajustados al estado. El objeto queda en "Mi Inventario", que suma el valor total.

Éxito: en la demo, la foto llega sola del móvil al PC y en menos de 6 s se ven el estado, el anuncio y los 3 precios, sin fallos y con aspecto de producto terminado.

## Positioning

Tasación instantánea: una foto con el móvil da el estado del objeto y 3 precios sacados de 4 plataformas en menos de 6 segundos, ajustados a ese estado.

## Operating Context

- Presentación en directo en el recinto: portátil conectado a un proyector con el dashboard; el móvil escanea un QR y hace la foto con su cámara.
- La red del recinto puede bloquear peticiones o aislar dispositivos: hay fallbacks deterministas, túnel HTTPS (`cloudflared`) y un botón para simular la captura desde el PC.
- Inicio de sesión con Google (un usuario por navegador). Cada usuario nuevo empieza con 3 productos de demo, y `POST /api/store/reset` los restaura antes de presentar.

## Capabilities and Constraints

- **Los 3 precios:** mínimo (venta rápida, si vendes hoy), medio (valor real de mercado) y máximo (techo para un artículo impecable). Siempre se cumple 0 < mínimo < medio < máximo.
- **Interfaz en español.** Next.js (App Router, TypeScript estricto, Tailwind, `lucide-react`) y backend FastAPI. Los datos viven en Firestore y solo se accede a ellos a través del backend.
- **Por niveles:** solo se construye la interfaz del nivel desbloqueado (ver `.agent/roadmap.md`). Las tendencias, alertas, planes, clima, calendario y buscador de GitHub pertenecen a los niveles 2-4 y no se muestran hasta que se cierre el nivel anterior.
- **Producto terminado en cualquier minuto:** nada de botones muertos, vistas "en construcción" ni `TODO` a la vista.
- **Límites técnicos:** toda llamada externa responde en menos de 6 s con fallback, las fotos del móvil se comprimen a ≤ 800 px en JPEG, y se usa Firebase en el plan gratuito Spark (sin Cloud Storage).

## Brand Commitments

- **Nombre: SmartLoot** (elegido el 2026-10-24). Sustituye en la interfaz a "LifeOS & ReCommerce AI"; la documentación del repo aún usa el nombre antiguo.
- **Voz:** español de España, tuteo, directa y práctica (ej. "Tasa tus objetos de segunda mano con una foto del móvil").
- Wallapop, Vinted, Milanuncios y eBay son marcas de terceros: se nombran como fuentes de precios, sin usarlas como si fueran propias.

## Evidence on Hand

- **Datos de demo:** 3 productos sembrados por usuario (Nintendo Switch OLED, iPhone 13, Sony WH-1000XM4) en `backend/app/store/seed_data.py`. Sus "fotos" son emojis sobre un color plano: todavía no hay fotos reales de producto.
- Cada tasación indica su origen (`source`: `live_mcp` o `stealth_fallback`). No se puede presentar un precio de fallback como dato en vivo.
- No hay testimonios, clientes, métricas de uso, prensa ni logotipo propio. No inventarlos.

## Product Principles

1. **La tasación es la protagonista:** foto → estado → 3 precios. Todo lo demás acompaña.
2. **Cada cifra se explica:** de dónde sale, de cuántos anuncios y de cuándo es.
3. **La demo no puede fallar:** siempre hay respuesta en menos de 6 s y nunca se ve un error técnico.
4. **Se entiende en 5 segundos desde la sala:** quien no conoce el producto sabe qué hace y qué está viendo.
