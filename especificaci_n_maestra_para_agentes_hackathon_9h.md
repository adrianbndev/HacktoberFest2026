# 🚀 PROJECT BOOTSTRAP: LifeOS & ReCommerce AI (Hacktoberfest 2026 - 9h Edition)

> **INSTRUCCIÓN CRÍTICA PARA EL AGENTE (ANTIGRAVITY CLI / CLAUDE CODE):**
> Lee este documento completo antes de escribir cualquier línea de código. Tu primera tarea es **generar la infraestructura de configuración agéntica** (`AGENTS.md`, `CLAUDE.md`, y el directorio `.agent/`) basándote en estas especificaciones. Una vez generados, debes construir el proyecto **estrictamente nivel por nivel**. NUNCA pases al siguiente nivel sin que el nivel actual sea 100% funcional, visualmente atractivo y demostrable.

---

## 1. Contexto del Proyecto y Equipo

* **Evento:** Hacktoberfest 2026 (Timebox: **9 horas**).
* **Equipo de Desarrollo:** **Ales, Adri y Matías**.
* **Visión del Producto:** Una plataforma web inteligente con inicio de sesión y perfil de usuario centrada en **tasación y gestión de inventario de segunda mano en tiempo real (Wallapop y plataformas similares)** mediante Visión Artificial y MCP, integrada dentro de un **Dashboard de Vida (LifeOS)** que conecta el valor de tus objetos con tu calendario, el clima, planes locales y tu trabajo en GitHub.

### Principios Innegociables de Supervivencia (9 Horas):
1. **Cada nivel es un producto terminado:** Si el tiempo se acaba al terminar el Nivel 1 o el Nivel 2, la aplicación debe verse 100% completa, sin botones rotos ni secciones "En construcción".
2. **Prioridad Absoluta al Core (Inventario + Wallapop + Móvil-PC):** No se escribe ni una línea de código del calendario, planes o GitHub hasta que el flujo de sacar foto con el móvil, analizar estado e historial de precios con MCP y guardarlo en el perfil funcione de principio a fin.
3. **MCP con Comportamiento Humano + Fallback Blindado:** El servidor MCP debe simular navegación humana (User-Agents rotativos, esperas con *jitter* aleatorio, cabeceras realistas) para consultar múltiples webs de segunda mano sin ser bloqueado por sistemas anti-bots. Además, **SIEMPRE** debe tener una capa de *fallback* inteligente por si la red del recinto bloquea el tráfico en mitad de la demo.

---

## 2. Reparto Sugerido para el Equipo (Ales, Adri y Matías)

El archivo `AGENTS.md` deberá estructurar el proyecto de forma modular para que **Ales, Adri y Matías** puedan trabajar en paralelo sin conflictos de Git:

* **Track A (Frontend, UI Bento Grid & Perfil/Notificaciones):** Diseño del dashboard, autenticación/perfil, gráficas de los 3 precios (Mínimo, Medio, Más Alto) y centro de alertas.
* **Track B (Sincronización Móvil-PC & Visión IA):** Flujo de código QR / sesión en vivo para abrir cámara en el teléfono, volver automáticamente a la web en el PC con la foto e inferir producto + **estado/salud del artículo** + descripción SEO.
* **Track C (MCP Stealth Engine, Cron de Precios & Módulos LifeOS):** Servidor MCP anti-bots multi-web, motor de actualización periódica de precios y APIs de Clima/Planes/GitHub.

---

## 3. Plan de Ejecución por Niveles (Priorizado por Impacto)

### 🟢 NIVEL 1: El Core Absoluto — Inventario IA, Sync Móvil-PC, MCP Stealth y Login (Horas 0:00 - 3:30)
**Objetivo:** Tener la aplicación web principal funcionando al 100%. Un usuario inicia sesión, pide sacar una foto desde la web, usa su móvil para fotografiar el producto, la foto aparece al instante en el PC, la IA evalúa su estado de salud y el MCP busca precios en Wallapop y otras webs devolviendo las 3 métricas clave y la descripción lista para vender.

* **1.1. Inicio de Sesión y Perfil de Usuario:**
  * Sistema de Login rápido (NextAuth / Supabase / Local Session persistente por usuario para Ales, Adri, Matías o Jurado).
  * Vista de **"Mi Inventario"** dentro del perfil donde se guardan todos los productos fotografiados y su valoración total acumulada.
* **1.2. Flujo Cámara Móvil $\leftrightarrow$ Web PC sin fricción:**
  * En la web del PC, el usuario pulsa *"Añadir Producto con el Móvil"*.
  * Se genera un QR o link único de sesión (`/mobile-capture/[sessionId]`).
  * El usuario abre el enlace en el móvil, saca la foto directamente desde el navegador (`capture="environment"`), y **automáticamente la pantalla del PC recibe la imagen en tiempo real** (vía SSE / WebSockets / Polling rápido de $1.5\text{ s}$) e inicia el análisis sin tocar nada más.
* **1.3. Reconocimiento por Visión + Salud/Estado del Producto:**
  * La IA analiza la foto recibida e identifica: **Nombre exacto, categoría, marca/modelo** y realiza un diagnóstico del **Estado o Salud del producto** (ej. *Nuevo, Como nuevo, Buen estado, Desgaste visible*, con una puntuación de salud de $0$ a $100\%$).
  * Generador automático de **Título SEO y Descripción persuasiva** optimizada para Wallapop según el estado detectado.
* **1.4. Motor MCP "Human-Like" (Anti-Bot) y las 3 Medidas de Precio:**
  * Herramienta MCP que busca el producto en diferentes webs de segunda mano (Wallapop, Vinted, Milanuncios/eBay) comportándose como un humano (delays naturales, headers de navegador real) y ajustando el valor según el **estado/salud del producto**.
  * Muestra claramente las **3 medidas obligatorias**:
    1. 📉 **Precio Mínimo** ($P_{\min}$ — para venta inmediata).
    2. 🎯 **Precio Medio** ($P_{\text{avg}}$ — valor real de mercado).
    3. 📈 **Precio Más Alto** ($P_{\max}$ — techo de mercado para artículos impecables).

> ✅ **Criterio de Cierre Nivel 1:** El usuario se loguea, saca una foto desde el teléfono, la ve aparecer en la web del PC, obtiene el estado de salud, la descripción y los 3 precios (mínimo, medio, más alto) vía MCP, y el producto queda guardado en su perfil. **Esto ya es un MVP ganador.**

---

### 🟡 NIVEL 2: Rastreo Periódico de Precios y Sistema de Notificaciones (Horas 3:30 - 5:30)
**Objetivo:** Hacer que el inventario esté "vivo". Los precios se actualizan periódicamente y el usuario recibe avisos cuando el mercado sube o baja.

* **2.1. Actualización Periódica de Precios (Background + Botón Demo):**
  * Job periódico que vuelve a consultar el MCP para los productos guardados en el perfil del usuario.
  * **Botón especial "Forzar Actualización de Mercado (Demo Mode)":** Permite que durante la presentación ante el jurado se dispare una actualización en vivo sin esperar horas.
* **2.2. Alertas, Tendencias y Notificaciones en el Perfil:**
  * Cada producto del inventario muestra indicadores visuales ($\uparrow$ verde / $\downarrow$ rojo) indicando si la media es más alta o más baja respecto al último escaneo.
  * **Centro de Notificaciones:** Avisos claros en el perfil del tipo:
    * *"🔔 ¡Subida detectada! El **precio medio** de tu Nintendo Switch ha subido un $+12\%$ ($185\text{ €} \rightarrow 207\text{ €}$). ¡Buen momento para publicar!"*
    * *"📉 El **precio mínimo** de los monitores LG ha bajado $10\text{ €}$ esta semana."*
  * Histórico rápido de evolución de las 3 medidas ($P_{\min}, P_{\text{avg}}, P_{\max}$).

> ✅ **Criterio de Cierre Nivel 2:** El perfil guarda todos los productos fotografiados, actualiza sus precios periódicamente y notifica visualmente cualquier subida o bajada en el precio mínimo, medio o más alto.

---

### 🟠 NIVEL 3: Expansión a LifeOS — Planes en tu Zona + Día a Día (Horas 5:30 - 7:30)
**Objetivo:** Transformar la herramienta de inventario en un Dashboard de Vida completo donde el dinero potencial de tus productos y tu agenda diaria te recomiendan planes reales.

* **3.1. Módulo de Planes Locales (Conectado a tu Inventario):**
  * Buscador y recomendador de cosas que hacer por tu zona (gastronomía, eventos, aire libre, cultura).
  * **Conexión Inteligente con Nivel 1 y 2:** Recomienda planes en función del valor o subida de tu inventario. Ejemplo: *"El valor medio de tu inventario ha subido $+25\text{ €}$ hoy y tienes $140\text{ €}$ acumulados en productos listos para vender: aquí tienes 3 planes increíbles por tu zona dentro de ese presupuesto"*.
* **3.2. Módulo Día a Día (Calendario, Clima y Entregas):**
  * Widget de clima actual y previsión semanal (condiciona si los planes recomendados son de interior o exterior).
  * Calendario diario/semanal donde se agendan tanto tus tareas personales como las citas de entrega o envíos de los productos vendidos en Wallapop.

> ✅ **Criterio de Cierre Nivel 3:** El dashboard integra tu inventario de segunda mano con tu agenda diaria, el tiempo meteorológico y planes personalizados en tu ciudad.

---

### 🔴 NIVEL 4: Módulo de Trabajo & Especial Hacktoberfest (Horas 7:30 - 8:30)
**Objetivo:** Añadir el toque técnico para desarrolladores aprovechando que estamos en **Hacktoberfest 2026**. *(Dejar los últimos 30 minutos de las 9h libres para probar la demo).*

* **4.1. Buscador Inteligente de Repositorios de GitHub:**
  * Módulo de trabajo con buscador de repositorios en vivo (GitHub API).
  * **Filtro Rápido "Hacktoberfest 2026":** Botón de un clic para encontrar repositorios con issues abiertas etiquetadas como `hacktoberfest` o `good-first-issue` según el lenguaje favorito de Ales, Adri o Matías.
  * **Resumen con IA:** Explicación en 2 líneas de la arquitectura del repo y cómo contribuir rápido.

> ✅ **Criterio de Cierre Nivel 4:** Ecosistema LifeOS 100% completado (Inventario Wallapop + Alertas + Día a Día + Planes + Trabajo/GitHub).

---

## 4. Archivos que el Agente DEBE Generar en el Paso 1

Al ejecutar el comando inicial en **Antigravity CLI** o **Claude Code**, el agente debe crear automáticamente esta estructura antes de programar el Nivel 1:

1. **`AGENTS.md` y `CLAUDE.md`:**
   * Reglas globales del repositorio, stack tecnológico (Next.js App Router, Tailwind CSS, Lucide Icons, TypeScript), convención de commits para **Ales, Adri y Matías**, y prohibición estricta de saltar de nivel sin validar el anterior.
2. **`.agent/roadmap.md`:**
   * Checklist detallado con los **Niveles 1, 2, 3 y 4** exactamente con el orden de prioridad definido en este documento.
3. **`.agent/architecture.md`:**
   * Esquema de datos del Usuario, Producto (`id`, `photoUrl`, `conditionScore`, `conditionLabel`, `priceMin`, `priceAvg`, `priceMax`, `priceHistory`, `seoTitle`, `seoDescription`), Notificaciones (`type`, `metricChanged`, `oldValue`, `newValue`) y endpoints REST/SSE.
4. **`.agent/mcp/stealth-market-mcp.md`:**
   * Especificación técnica del servidor MCP: rotación de cabeceras HTTP, delays aleatorios entre $800\text{ ms}$ y $2200\text{ ms}$ para imitar comportamiento humano en Wallapop y webs de segunda mano, ponderación del precio según el estado/salud del producto y sistema de *fallback* determinista si hay bloqueo de red.
5. **`.agent/rules/hackathon-guardrails.md`:**
   * Reglas de seguridad para la demo: soporte móvil sin errores de CORS/HTTPS en la captura de cámara, persistencia inmediata de fotos y tiempos de respuesta máximos de $6\text{ s}$.

---

## 5. Prompt de Arranque Rápido (Copia y pega esto en Antigravity CLI o Claude Code)

```text
Lee el archivo BOOTSTRAP.md completo. Somos Ales, Adri y Matías creando este proyecto para Hacktoberfest 2026 en 9 horas.
Paso 1: Genera inmediatamente AGENTS.md, CLAUDE.md y toda la carpeta .agent/ (roadmap.md, architecture.md, mcp/stealth-market-mcp.md y rules/hackathon-guardrails.md) respetando estrictamente la nueva priorización de los 4 niveles.
Paso 2: Inicializa el proyecto web (Next.js + Tailwind + Lucide) y empieza EXCLUSIVAMENTE por el NIVEL 1 (Login + Perfil + Sincronización de foto desde el móvil a la web del PC + Visión IA con estado/salud del producto + MCP con comportamiento humano que devuelva Precio Mínimo, Precio Medio y Precio Más Alto + Descripción SEO).
No pases al Nivel 2 hasta que podamos probar el flujo completo del Nivel 1 de extremo a extremo.
```