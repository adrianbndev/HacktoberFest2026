# 🕵️ Especificación Técnica: Motor MCP "Human-Like" (`stealth-market-mcp`)

> **Responsable:** Track C (**Matías**)
> **Ubicación de Implementación:** `src/lib/mcp/stealth-engine.ts`, `src/mcp/server.ts` y `/api/market/valuate`

---

## 1. Propósito del Servidor MCP

El motor `stealth-market-mcp` proporciona herramientas bajo el estándar **Model Context Protocol (MCP)** para tasar artículos de segunda mano en tiempo real consultando plataformas del mercado español/europeo (**Wallapop, Vinted, Milanuncios y eBay**), imitando a un comprador/vendedor humano y ajustando las **3 medidas obligatorias de precio** ($P_{\min}, P_{\text{avg}}, P_{\max}$) según la salud visual del objeto (`conditionScore` de $0$ a $100\%$).

---

## 2. Comportamiento Humano ("Stealth & Anti-Bot Engine")

Para evitar bloqueos `403 Forbidden` / Cloudflare / Akamai durante el hackathon, toda petición saliente debe aplicar las siguientes técnicas:

### 2.1 Jitter Temporal Aleatorio ($800\text{ ms} - 2200\text{ ms}$)
* Antes de despachar la consulta de mercado, aplicar una pausa asíncrona con distribución uniforme entre **$800\text{ ms}$ y $2200\text{ ms}$**:
  ```typescript
  export const humanJitter = (minMs = 800, maxMs = 2200): Promise<void> => {
    const delay = Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;
    return new Promise((resolve) => setTimeout(resolve, delay));
  };
  ```
* Las consultas a múltiples plataformas se ejecutan en paralelo (`Promise.allSettled`) con un *timeout* duro de **$3500\text{ ms}$** por plataforma, garantizando que el pipeline completo (Visión IA + MCP) nunca supere el guardrail global de **$6\text{ s}$**.

### 2.2 Rotación de Huella HTTP y User-Agents Reales
* Mantener un pool rotativo de al menos 6 `User-Agent` modernos (Chrome 128+ en macOS/Windows/Linux, Safari 17+ iOS/macOS, Firefox 130+).
* Incluir cabeceras realistas de navegador en España:
  ```typescript
  const STEALTH_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Linux"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
  };
  ```

---

## 3. Algoritmo de las 3 Medidas de Precio y Ponderación por Salud

Una vez obtenida la muestra de precios brutos de mercado $S = \{p_1, p_2, \dots, p_n\}$ (filtrando *outliers* extremos mediante rango intercuartílico IQR para descartar cajas vacías o anuncios de $1\text{ €}$ falsos):

### 3.1 Factor de Ponderación por Estado/Salud ($W_{\text{health}}$)
La IA de Visión entrega un `conditionScore` $\in [0, 100]$. Definimos el multiplicador de condición $W_{\text{health}}$ respecto a la media de segunda mano estándar ($\approx 75\%$):

$$\text{Si } \text{score} = 75 \implies W_{\text{health}} = 1.00$$

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

1. **Intento Primario (Live Stealth Fetch):** Consulta en vivo con *jitter* humano y *timeout* máximo de $3.5\text{ s}$.
2. **Fallback Determinista Inteligente (Zero-Downtime):**
   * Si la red falla, devuelve `403/429`, o la lista de resultados es vacía:
   * El motor consulta un **Catálogo Semilla de Mercado Curado** (con precios reales de 2026 en España para consolas, móviles, monitores, auriculares, portátiles, cámaras, bicicletas, ropa vintage, periféricos, libros, etc.) combinado con un **estimador determinista por hash de marca/modelo + categoría**.
   * Genera una muestra realista de `comparableListings` en Wallapop, Vinted, Milanuncios y eBay y aplica exactamente la misma fórmula de ponderación $W_{\text{health}}$.
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
