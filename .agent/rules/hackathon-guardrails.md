# 🛡️ Hackathon Guardrails & Reglas de Supervivencia (`.agent/rules/hackathon-guardrails.md`)

> **Aplicación:** Regla activa siempre (`always_on`) para **Antigravity CLI**, **Claude Code** y **OpenCode**. Estas restricciones protegen la demo frente al jurado y garantizan velocidad de desarrollo en las 9 horas.

---

## 1. Guardrails Técnicos para Captura Móvil $\leftrightarrow$ PC (Cero Errores CORS / HTTPS / AP Isolation)

1. **Prohibido depender exclusivamente de `navigator.mediaDevices.getUserMedia` para la cámara móvil:**
   * **Por qué:** Los navegadores móviles (Safari iOS y Chrome Android) bloquean `getUserMedia()` si el servidor local se abre por IP de red local (`http://192.168.x.x:3000`) sin HTTPS válido.
   * **Solución Obligatoria:** Usar `<input type="file" accept="image/*" capture="environment" />` estilizado como un botón nativo de cámara gigante, que funciona al **100% tanto en HTTP local como en HTTPS**, permitiendo además elegir una foto de la galería o usar `getUserMedia` como mejora progresiva si hay contexto seguro.
2. **Compresión de Imagen en el Cliente antes de Subir:**
   * Las cámaras móviles actuales generan fotos de $5\text{ MB}$ a $15\text{ MB}$, lo que rompe límites de body en Next.js o ralentiza el Wi-Fi del recinto.
   * **Regla:** Antes de hacer `PUT /api/capture-session/[sessionId]`, el navegador móvil debe redimensionar la imagen en un `<canvas>` a un máximo de **$1024\text{ px}$** en su lado mayor y comprimirla en JPEG (`quality: 0.78`), asegurando un payload $< 350\text{ KB}$ y una transmisión en $< 400\text{ ms}$.
3. **Doble vía de Sincronización (SSE + Short-Polling $1\text{ s}$):**
   * El PC debe escuchar cambios de la sesión cada $\le 1\text{ s}$ para que, en cuanto el móvil suba la foto, la pantalla del PC transicione sola al análisis sin que el usuario tenga que tocar el teclado ni refrescar la página.
2. **Protocolo Anti-AP-Isolation (Wi-Fi del Hackathon bloqueando IPs locales):**
   * En redes de eventos donde el router bloquea tráfico entre dispositivos (`192.168.x.x` inaccesible desde el móvil), el modal del QR debe:
     1. Detectar automáticamente `window.location.origin` y las IPs LAN locales (`os.networkInterfaces()`).
     2. Incluir un **input editable en vivo para la URL base del QR**, permitiendo pegar al instante un túnel público (`npx cloudflared tunnel --url http://localhost:3000`) o usar el Hotspot del teléfono.
     3. Incluir siempre un botón **"🧪 Simular Captura Móvil / Subir Foto"** en el propio modal para que la demo sea 100% indestructible incluso sin cobertura móvil.
3. **Compresión de Imagen en el Cliente antes de Subir ($< 200\text{ KB}$):**
   * Las cámaras móviles actuales generan fotos de $5\text{ MB}$ a $15\text{ MB}$, lo que rompe límites de body en Next.js o engorda `/data/store.json`.
   * **Regla:** Antes de hacer `PUT /api/capture-session/[sessionId]`, el navegador móvil debe redimensionar la imagen en un `<canvas>` a un máximo de **$800\text{ px}$** en su lado mayor y comprimirla en JPEG (`quality: 0.75`), asegurando un payload $< 200\text{ KB}$ y una transmisión en $< 300\text{ ms}$.
4. **Doble vía de Sincronización (SSE + Short-Polling $1.2\text{ s}$):**
   * El PC debe escuchar cambios de la sesión cada $\le 1.2\text{ s}$ para que, en cuanto el móvil suba la foto, la pantalla del PC transicione sola al análisis sin que el usuario tenga que tocar el teclado ni refrescar la página.

---

## 2. Presupuesto Estricto de Latencia Desglosado ($< 6\text{ Segundos}$)

1. **Tiempo Máximo de Tasación End-to-End ($\le 6.0\text{ s}$):**
   * Desde que la foto llega al PC hasta que se muestran el estado de salud ($0-100\%$), la descripción SEO y los 3 precios ($P_{\min}, P_{\text{avg}}, P_{\max}$), **no pueden pasar más de $6\text{ segundos}$**.
   * `AbortSignal.timeout(3000)` obligatorio en Visión IA; el MCP tiene un *deadline* total de $2500\text{ ms}$ con el jitter incluido (ver [`stealth-market-mcp.md`](../mcp/stealth-market-mcp.md) §2.1).
1. **Desglose Matemático End-to-End ($\le 5.3\text{ s} < 6.0\text{ s}$):**
   * Para evitar que la suma en serie de Visión IA + Jitter MCP + Scraping supere los $6\text{ segundos}$, cada etapa tiene un presupuesto duro:
     * **Compresión y subida desde móvil:** $\le 400\text{ ms}$.
     * **Visión IA (`/api/vision/analyze`):** `AbortSignal.timeout(2500)` ($\le 2.5\text{ s}$). Si excede o falla, activa `DeterministicVisionProvider` en $< 30\text{ ms}$.
     * **Tasación MCP (`/api/market/valuate`):** Jitter humano ($650-1200\text{ ms}$) + conectores en paralelo con `AbortSignal.timeout(1600)` ($\le 2.8\text{ s}$ total). Si excede o recibe `403`, activa `DeterministicMarketFallback` en $< 10\text{ ms}$.
     * **Total máximo acumulado en el peor caso:** $2.5\text{ s} + 2.8\text{ s} = \mathbf{5.3\text{ s}} < 6.0\text{ s}$.
2. **Feedback Visual Progresivo en la UI:**
   * Mientras transcurren los $2\text{ s} - 4\text{ s}$ de análisis + jitter humano del MCP, la UI debe mostrar pasos animados en vivo:
     1. *"📸 Imagen recibida desde el móvil..."*
     2. *"🔍 Evaluando estado y salud del producto con Visión IA..."*
     3. *"🕵️ Consultando Wallapop, Vinted y Milanuncios vía MCP Stealth..."*
     4. *"✅ Tasación completada ($P_{\min}, P_{\text{avg}}, P_{\max}$)"*

---

## 3. Persistencia Atómica sin Race Conditions y Datos Semilla para el Jurado

1. **Singleton en `globalThis` + Escritura Atómica en Disco:**
   * En Next.js (modo dev HMR o múltiples peticiones concurrentes de polling + subida móvil), escribir directamente con `fs.writeFileSync('/data/store.json')` puede corromper el archivo JSON a mitad de escritura.
   * **Regla:** Mantener el estado en memoria en `globalThis.__LIFEOS_STORE__` y persistir en disco escribiendo primero en `/data/store.json.tmp` seguido de `fs.renameSync('/data/store.json.tmp', '/data/store.json')`.
2. **Perfiles Listos desde el Minuto 1 + Botón de Reset Demo:**
   * El sistema debe incluir perfiles preconfigurados para **Ales**, **Adri**, **Matías** y **Jurado**, con al menos 3 artículos realistas ya cargados en el inventario semilla para poder demostrar el Nivel 2, 3 y 4 al instante, además de un endpoint/botón `POST /api/store/reset` para restaurar el estado inicial antes de salir a presentar ante el jurado.

---

## 4. Disciplina de Producto Terminado por Nivel

1. **Cero Elementos Rotos o Placeholders:**
   * Nunca renderizar botones que no hagan nada, enlaces con `href="#"` vacíos o textos tipo *"Próximamente en Nivel 3"*.
   * Si estamos en el Nivel 1, la interfaz es un dashboard de ReCommerce & Inventario IA 100% completo y coherente. Cuando se desbloquea el Nivel 2, 3 o 4, el Bento Grid se expande orgánicamente.
2. **Botones de Demo de 1 Clic:**
   * Todo proceso asíncrono o periódico (como el rastreo de precios del Nivel 2 o el filtro Hacktoberfest del Nivel 4) debe tener un botón explícito en la UI para que **Ales, Adri o Matías** puedan activarlo en vivo durante los 3-5 minutos de pitch ante el jurado.
