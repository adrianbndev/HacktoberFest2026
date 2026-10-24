# 🕵️ Especificación Técnica: Motor MCP "Human-Like" en Python (`stealth-market-mcp`)

> **Responsable:** Track C (**Matías**)
> **Ubicación de Implementación:** `backend/app/mcp/stealth_engine.py`, `backend/app/mcp/pricing_math.py`, `backend/mcp_server.py` y `backend/app/routers/market.py` (`/api/market/valuate`)

---

## 1. Propósito del Servidor MCP en Python

El motor `stealth-market-mcp` proporciona herramientas bajo el estándar **Model Context Protocol (MCP)** usando **`FastMCP` (`mcp` Python SDK)** y peticiones asíncronas con **`httpx` + `BeautifulSoup4`** para tasar artículos de segunda mano en tiempo real consultando plataformas del mercado español/europeo (**Wallapop, Vinted, Milanuncios y eBay**), imitando a un comprador/vendedor humano y ajustando las **3 medidas obligatorias de precio** ($P_{\min}, P_{\text{avg}}, P_{\max}$) según la salud visual del objeto (`conditionScore` de $0$ a $100\%$).

---

## 2. Comportamiento Humano ("Stealth & Anti-Bot Engine" en Python)

Para evitar bloqueos `403 Forbidden` / Cloudflare / Akamai durante el hackathon, toda petición saliente debe aplicar las siguientes técnicas:

### 2.1 Jitter Temporal Aleatorio y Presupuesto de Latencia ($< 2.8\text{ s}$ Total)
* **Peligro evitado:** Si se sumaran $2.2\text{ s}$ de jitter + $3.5\text{ s}$ de red + $2.8\text{ s}$ de Visión IA, se superarían los $6.0\text{ s}$ máximos del hackathon.
* **Regla de Presupuesto MCP en Python:**
  1. Antes de despachar la consulta en vivo, aplicar una pausa asíncrona acotada (`await human_jitter(0.65, 1.20)` en modo interactivo web; configurable a `0.0` en `pytest`):
     ```python
     import asyncio
     import random

     async def human_jitter(min_sec: float = 0.65, max_sec: float = 1.20) -> None:
         if max_sec <= 0:
             return
         await asyncio.sleep(random.uniform(min_sec, max_sec))
     ```
  2. Las consultas a las 4 plataformas (`wallapop`, `vinted`, `milanuncios`, `ebay`) se lanzan en paralelo (`asyncio.gather(..., return_exceptions=True)`) con un *timeout* duro de **$1.6\text{ s}$** (`httpx.Timeout(1.6)`) tras el jitter.
  3. De este modo, el motor MCP responde siempre en **$\le 2.8\text{ s}$**, asegurando que `Visión IA Python (≤ 2.5s) + MCP Python (≤ 2.8s) = ≤ 5.3s < 6.0s`.

### 2.2 Normalización de Query y Filtrado Léxico Anti-Basura
* **Normalización de Búsqueda:** La IA de Visión puede devolver nombres largos (ej. `"Consola Nintendo Switch OLED 64GB Blanca en excelente estado"`). Antes de consultar los conectores, el motor simplifica la búsqueda a `brand + model` o a las primeras 4-5 palabras clave significativas (`"Nintendo Switch OLED"`).
* **Filtro Léxico de Falsos Positivos:** Antes del cálculo estadístico, descartar cualquier anuncio cuyo título contenga palabras de accesorios o engaños (`"caja vacía"`, `"solo caja"`, `"funda"`, `"protector"`, `"cable"`, `"carcasa"`) o precios simbólicos ($\le 3\text{ €}$).

### 2.3 Rotación de Huella HTTP y User-Agents Reales
* Mantener un pool rotativo de al menos 6 `User-Agent` modernos (Chrome 128+ en macOS/Windows/Linux, Safari 17+ iOS/macOS, Firefox 130+).
* Incluir cabeceras realistas de navegador en España:
  ```python
  STEALTH_HEADERS_BASE = {
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
      "Cache-Control": "no-cache",
      "Pragma": "no-cache",
      "Sec-Ch-Ua-Mobile": "?0",
      "Sec-Ch-Ua-Platform": '"Linux"',
      "Sec-Fetch-Dest": "empty",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Site": "same-site",
  }
  ```

---

## 3. Algoritmo de las 3 Medidas de Precio y Ponderación por Salud

Una vez obtenida la muestra de precios brutos de mercado $S = \{p_1, p_2, \dots, p_n\}$ (filtrando *outliers* extremos mediante rango intercuartílico IQR para descartar cajas vacías o anuncios de $1\text{ €}$ falsos):

### 3.1 Factor de Ponderación por Estado/Salud ($W_{\text{health}}$)
La IA de Visión entrega un `conditionScore` $\in [0, 100]$. Definimos el multiplicador de condición $W_{\text{health}}$ respecto a la media de segunda mano estándar ($\approx 70\%$):

$$\text{Si } \text{score} = 70 \implies W_{\text{health}} = 1.00$$

$$W_{\text{health}} = 0.65 + 0.50 \times \left(\frac{\text{conditionScore}}{100}\right)$$

| Etiqueta de Salud (`conditionLabel`) | Rango `conditionScore` | Multiplicador $W_{\text{health}}$ | Impacto en Tasación |
| :--- | :---: | :---: | :--- |
| **Nuevo** (Precintado / Impecable) | $90 - 100\%$ | $1.10\times - 1.15\times$ | Cerca del techo del mercado |
| **Como nuevo** | $80 - 89\%$ | $1.05\times - 1.09\times$ | Por encima de la media |
| **Buen estado** | $65 - 79\%$ | $0.97\times - 1.04\times$ | Valor estándar de mercado |
| **Desgaste visible** | $40 - 64\%$ | $0.85\times - 0.96\times$ | Descuento para venta rápida |
| **Para piezas** | $0 - 39\%$ | $0.65\times - 0.84\times$ | Liquidación / reacondicionado |

### 3.2 Cálculo de las 3 Medidas Obligatorias
Sea $P_{\text{base}}$ la mediana/media recortada del mercado para ese modelo:
1. 🎯 **Precio Medio ($P_{\text{avg}}$ — Valor Real de Mercado):**
   $$P_{\text{avg}} = \text{round}\left(P_{\text{base}} \times W_{\text{health}}\right)$$
2. 📉 **Precio Mínimo ($P_{\min}$ — Venta Inmediata en $<24\text{h}$):**
   $$P_{\min} = \text{round}\left(\min(\text{Percentil}_{20}(S), P_{\text{avg}} \times 0.82)\right)$$
3. 📈 **Precio Más Alto ($P_{\max}$ — Techo de Mercado Impecable):**
   $$P_{\max} = \text{round}\left(\max(\text{Percentil}_{85}(S), P_{\text{avg}} \times 1.24)\right)$$

> **Invariante SDD Obligatoria:** Siempre debe cumplirse estrictamente que $0 < P_{\min} < P_{\text{avg}} < P_{\max}$.

---

## 4. Capa de Fallback Determinista Blindado (Anti-Fallo en Demo)

En un hackathon, el Wi-Fi del recinto o los firewalls pueden bloquear peticiones hacia Wallapop/Vinted en mitad de la presentación ante el jurado. Por tanto, el motor MCP **SIEMPRE** debe ejecutar una estrategia de doble capa:

1. **Intento Primario (Live Stealth Fetch):** Consulta en vivo con *jitter* humano dentro del *deadline* total de $2.5\text{ s}$ (§2.1).
2. **Fallback Determinista Inteligente (Zero-Downtime):**
   * Si la red falla, devuelve `403/429`, o la lista de resultados es vacía:
   * El motor consulta un **Catálogo Semilla de Mercado Curado** (con precios reales de 2026 en España para consolas, móviles, monitores, auriculares, portátiles, cámaras, bicicletas, ropa vintage, periféricos, libros, etc.) combinado con un **estimador determinista por hash de marca/modelo + categoría**.
   * Genera una muestra realista de `comparableListings` en Wallapop, Vinted, Milanuncios y eBay y aplica exactamente la misma fórmula de ponderación $W_{\text{health}}$.
   * **Enlaces Reales de Búsqueda (Deep Links):** Cada elemento de `comparableListings` debe incluir siempre un campo `url` funcional apuntando al anuncio real o a la búsqueda activa en la plataforma correspondiente (ej. `https://es.wallapop.com/app/search?keywords=${encodeURIComponent(query)}`, `https://www.vinted.es/catalog?search_text=...`, `https://www.ebay.es/sch/i.html?_nkw=...`) para que el jurado pueda abrirlo en 1 clic sin recibir jamás un `404`.
   * **Nunca devuelve `null`, `NaN`, `0 €` ni lanza un error HTTP 500 hacia el frontend.**

---

## 5. Definición de Herramientas MCP Expuestas

El servidor MCP expone las siguientes tools para consumo interno y externo:

1. `search_secondhand_market`:
   * **Inputs:** `{ query: string, category?: string, conditionScore: number }`
   * **Output:** `{ priceMin, priceAvg, priceMax, sampleSize, platforms, comparableListings }`
2. `simulate_market_tick`:
   * **Inputs:** `{ itemId: string, currentPriceAvg: number, demoVolatility?: boolean }`
   * **Output:** `{ newPriceMin, newPriceAvg, newPriceMax, deltaPercent, deltaEur, notificationMessage }`
