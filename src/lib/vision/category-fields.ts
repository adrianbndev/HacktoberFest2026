import type { ConditionLabel, VisionDynamicField } from "@/types/sdd";

export const PRODUCT_CATEGORIES: readonly string[] = [
  "Móviles y Telefonía",
  "Motor y Vehículos",
  "Periféricos · Ratones",
  "Periféricos · Teclados",
  "Monitores y Pantallas",
  "Informática y Portátiles",
  "Consolas y Videojuegos",
  "Audio y Sonido",
  "Cámaras y Fotografía",
  "Bicicletas y Movilidad",
  "Mobiliario y Decoración",
  "Moda y Accesorios",
  "Hogar y Electrodomésticos",
  "Bricolaje y Herramientas",
  "Instrumentos Musicales",
  "Segunda Mano y Ocasión",
];

type FieldTemplate = Omit<VisionDynamicField, "value"> & { defaultValue: string };

const FAMILY_TEMPLATES: Record<string, FieldTemplate[]> = {
  raton: [
    { key: "connectivity", label: "Conectividad", fieldType: "select", options: ["Inalámbrico 2.4GHz + Bluetooth", "Inalámbrico Bluetooth", "Receptor USB 2.4GHz", "Cable USB"], defaultValue: "Inalámbrico 2.4GHz + Bluetooth" },
    { key: "sensorType", label: "Sensor / Precisión DPI", fieldType: "select", options: ["Óptico de alta precisión", "Sensor Gaming (16.000+ DPI)", "Óptico estándar oficina", "Láser"], defaultValue: "Óptico de alta precisión" },
    { key: "buttons", label: "Número de botones", fieldType: "select", options: ["5-6 botones (con laterales)", "3 botones estándar + rueda", "Programable / Gaming (+7 botones)"], defaultValue: "5-6 botones (con laterales)" },
    { key: "ergonomics", label: "Ergonomía / Mano", fieldType: "select", options: ["Diestro ergonómico", "Ambidiestro / Simétrico", "Vertical ergonómico", "Compacto de viaje"], defaultValue: "Diestro ergonómico" },
    { key: "powerSource", label: "Alimentación", fieldType: "select", options: ["Batería recargable USB-C", "Pila AA / AAA", "Alimentación por cable USB"], defaultValue: "Batería recargable USB-C" },
    { key: "color", label: "Color / Acabado", fieldType: "text", placeholder: "Ej. Negro mate, Blanco", defaultValue: "" },
  ],
  teclado: [
    { key: "switchType", label: "Tipo de interruptores (Switches)", fieldType: "select", options: ["Mecánico Táctil (Brown)", "Mecánico Lineal (Red)", "Mecánico Clicky (Blue)", "Membrana / Tijera", "Óptico"], defaultValue: "Mecánico Táctil (Brown)" },
    { key: "keyboardFormat", label: "Formato / Tamaño", fieldType: "select", options: ["75% Compacto", "TKL (80% sin bloque numérico)", "100% Completo", "60% / 65% Mini"], defaultValue: "75% Compacto" },
    { key: "keyboardLayout", label: "Distribución de idioma", fieldType: "select", options: ["Español ISO (con Ñ)", "Inglés ANSI (US)", "Inglés ISO (UK)"], defaultValue: "Español ISO (con Ñ)" },
    { key: "connectivity", label: "Conectividad", fieldType: "select", options: ["Inalámbrico Bluetooth + Cable USB-C", "Solo cable USB", "Inalámbrico 2.4GHz + Bluetooth"], defaultValue: "Inalámbrico Bluetooth + Cable USB-C" },
    { key: "backlight", label: "Iluminación", fieldType: "select", options: ["RGB personalizable", "Retroiluminación blanca", "Sin iluminación"], defaultValue: "RGB personalizable" },
    { key: "color", label: "Color", fieldType: "text", placeholder: "Ej. Negro/Gris, Blanco", defaultValue: "" },
  ],
  monitor: [
    { key: "screenSize", label: "Tamaño de pantalla", fieldType: "select", options: ["24 pulgadas", "27 pulgadas", "32 pulgadas", "34 pulgadas Ultrawide"], defaultValue: "27 pulgadas" },
    { key: "resolution", label: "Resolución", fieldType: "select", options: ["4K UHD (3840x2160)", "QHD 2K (2560x1440)", "Full HD (1920x1080)"], defaultValue: "4K UHD (3840x2160)" },
    { key: "refreshRate", label: "Tasa de refresco", fieldType: "select", options: ["60 - 75 Hz", "144 - 165 Hz Gaming", "240 Hz o superior"], defaultValue: "60 - 75 Hz" },
    { key: "panelType", label: "Tipo de panel", fieldType: "select", options: ["IPS", "OLED / QD-OLED", "VA", "TN"], defaultValue: "IPS" },
    { key: "color", label: "Color exterior", fieldType: "text", placeholder: "Ej. Negro, Plata", defaultValue: "" },
  ],
  motor: [
    { key: "fuelType", label: "Tipo de combustible", fieldType: "select", options: ["Gasolina", "Diésel", "Híbrido (HEV)", "Híbrido Enchufable (PHEV)", "Eléctrico (EV)", "GLP / GNC"], defaultValue: "Gasolina" },
    { key: "transmission", label: "Cambio / Transmisión", fieldType: "select", options: ["Manual", "Automático"], defaultValue: "Manual" },
    { key: "bodyType", label: "Carrocería / Tipo", fieldType: "select", options: ["Turismo / Compacto", "SUV / Todoterreno", "Berlina", "Familiar", "Coupé / Deportivo", "Furgoneta", "Motocicleta / Scooter"], defaultValue: "Turismo / Compacto" },
    { key: "year", label: "Año de matriculación", fieldType: "text", placeholder: "Ej. 2020", defaultValue: "" },
    { key: "mileageKm", label: "Kilometraje (km)", fieldType: "text", placeholder: "Ej. 85.000 km", defaultValue: "" },
    { key: "horsepower", label: "Potencia (CV)", fieldType: "text", placeholder: "Ej. 120 CV", defaultValue: "" },
    { key: "environmentalBadge", label: "Distintivo ambiental DGT", fieldType: "select", options: ["C (Verde)", "ECO", "0 Emisiones (Azul)", "B (Amarilla)", "Sin etiqueta"], defaultValue: "C (Verde)" },
    { key: "color", label: "Color exterior", fieldType: "text", placeholder: "Ej. Blanco, Negro, Rojo", defaultValue: "" },
  ],
  moviles: [
    { key: "storage", label: "Capacidad de almacenamiento", fieldType: "select", options: ["64 GB", "128 GB", "256 GB", "512 GB", "1 TB", "32 GB"], defaultValue: "128 GB" },
    { key: "ram", label: "Memoria RAM", fieldType: "select", options: ["4 GB", "6 GB", "8 GB", "12 GB", "16 GB"], defaultValue: "8 GB" },
    { key: "batteryHealth", label: "Salud de batería (%)", fieldType: "text", placeholder: "Ej. 88%", defaultValue: "" },
    { key: "color", label: "Color / Acabado", fieldType: "text", placeholder: "Ej. Negro espacial, Plata", defaultValue: "" },
    { key: "carrierLock", label: "Estado de operador", fieldType: "select", options: ["Libre de fábrica", "Vinculado a operador"], defaultValue: "Libre de fábrica" },
    { key: "screenStatus", label: "Estado de pantalla", fieldType: "select", options: ["Impecable sin marcas", "Micro-arañazos leves", "Con cristal templado", "Grieta o marca visible"], defaultValue: "Impecable sin marcas" },
    { key: "accessories", label: "Caja y accesorios", fieldType: "select", options: ["Caja y cable original", "Con cargador y funda", "Solo teléfono", "Completo con factura"], defaultValue: "Caja y cable original" },
  ],
  consolas: [
    { key: "edition", label: "Edición / Capacidad", fieldType: "select", options: ["OLED 64 GB", "Estándar 32 GB", "Edición Disco (825 GB / 1 TB)", "Edición Digital", "Portátil / Lite", "Retro / Coleccionista"], defaultValue: "OLED 64 GB" },
    { key: "controllers", label: "Mandos incluidos", fieldType: "select", options: ["1 mando original", "2 mandos originales", "Pareja Joy-Con original", "Sin mandos"], defaultValue: "Pareja Joy-Con original" },
    { key: "packaging", label: "Caja y dock/cables", fieldType: "select", options: ["Completa con caja y cables", "Con cables originales sin caja", "Solo consola"], defaultValue: "Completa con caja y cables" },
    { key: "includedGames", label: "Juegos incluidos", fieldType: "text", placeholder: "Ej. Ninguno, Mario Kart 8...", defaultValue: "" },
    { key: "color", label: "Color / Edición", fieldType: "text", placeholder: "Ej. Blanca, Neón", defaultValue: "" },
  ],
  informatica: [
    { key: "processor", label: "Procesador / Chip", fieldType: "text", placeholder: "Ej. Apple M2, Intel Core i7, Ryzen 7", defaultValue: "" },
    { key: "ram", label: "Memoria RAM", fieldType: "select", options: ["8 GB", "16 GB", "32 GB", "64 GB", "4 GB"], defaultValue: "8 GB" },
    { key: "storage", label: "Almacenamiento SSD", fieldType: "select", options: ["256 GB SSD", "512 GB SSD", "1 TB SSD", "2 TB SSD", "128 GB"], defaultValue: "256 GB SSD" },
    { key: "screenSize", label: "Tamaño de pantalla", fieldType: "select", options: ["13.3 - 13.6 pulgadas", "14 pulgadas", "15.6 pulgadas", "16 pulgadas", "10.9 - 11 pulgadas"], defaultValue: "13.3 - 13.6 pulgadas" },
    { key: "keyboardLayout", label: "Teclado / Distribución", fieldType: "select", options: ["Español (con Ñ)", "Inglés (US/UK)", "No aplica (Tablet/Sobremesa)"], defaultValue: "Español (con Ñ)" },
    { key: "color", label: "Color", fieldType: "text", placeholder: "Ej. Gris espacial, Plata", defaultValue: "" },
  ],
  audio: [
    { key: "connectivity", label: "Conectividad", fieldType: "select", options: ["Bluetooth inalámbrico", "Bluetooth + Cable Jack", "Solo cable", "Wi-Fi / Multiroom"], defaultValue: "Bluetooth + Cable Jack" },
    { key: "noiseCancelling", label: "Cancelación de ruido (ANC)", fieldType: "select", options: ["Sí, ANC activa", "Aislamiento pasivo", "No"], defaultValue: "Sí, ANC activa" },
    { key: "formFactor", label: "Formato de audio", fieldType: "select", options: ["Diadema (Over-Ear)", "In-Ear / True Wireless", "Altavoz portátil", "Equipo de estudio / Hi-Fi"], defaultValue: "Diadema (Over-Ear)" },
    { key: "accessories", label: "Estuche y cables", fieldType: "select", options: ["Con estuche y cables originales", "Con caja original completa", "Solo dispositivo"], defaultValue: "Con estuche y cables originales" },
    { key: "color", label: "Color", fieldType: "text", placeholder: "Ej. Negro, Plata", defaultValue: "" },
  ],
  camaras: [
    { key: "cameraType", label: "Tipo de cámara", fieldType: "select", options: ["Cámara Réflex (DSLR)", "Mirrorless / Sin espejo", "Compacta Digital", "Objetivo / Lente", "Cámara de acción"], defaultValue: "Cámara Réflex (DSLR)" },
    { key: "lensIncluded", label: "Objetivo incluido", fieldType: "text", placeholder: "Ej. Kit 18-55mm IS, Solo cuerpo", defaultValue: "" },
    { key: "shutterCount", label: "Disparos / Uso", fieldType: "select", options: ["Poco uso (< 10.000 disparos)", "Uso medio (10.000 - 30.000)", "Más de 30.000 disparos", "Desconocido"], defaultValue: "Poco uso (< 10.000 disparos)" },
    { key: "accessories", label: "Batería y accesorios", fieldType: "select", options: ["Batería, cargador y correa", "Con funda y tarjeta SD", "Solo cuerpo"], defaultValue: "Batería, cargador y correa" },
  ],
  bicicletas: [
    { key: "bikeType", label: "Tipo de vehículo", fieldType: "select", options: ["MTB / Montaña", "Carretera", "Urbana / Paseo", "Gravel", "Bicicleta eléctrica (E-Bike)", "Patinete eléctrico"], defaultValue: "MTB / Montaña" },
    { key: "frameSize", label: "Talla del cuadro", fieldType: "select", options: ["Talla S", "Talla M", "Talla L", "Talla XL", "Talla única"], defaultValue: "Talla L" },
    { key: "wheelSize", label: "Tamaño de rueda", fieldType: "select", options: ["29 pulgadas", "27.5 pulgadas", "26 pulgadas", "700c / 28 pulgadas", "8.5 - 10 pulgadas"], defaultValue: "29 pulgadas" },
    { key: "frameMaterial", label: "Material del cuadro", fieldType: "select", options: ["Aluminio", "Fibra de carbono", "Acero"], defaultValue: "Aluminio" },
    { key: "color", label: "Color", fieldType: "text", placeholder: "Ej. Negro/Rojo", defaultValue: "" },
  ],
  mobiliario: [
    { key: "material", label: "Material principal", fieldType: "select", options: ["Madera maciza", "Madera / Melamina", "Metal / Acero", "Tapizado / Tela", "Piel / Polipiel", "Cristal", "Plástico / Polipropileno"], defaultValue: "Madera maciza" },
    { key: "style", label: "Estilo decorativo", fieldType: "select", options: ["Moderno / Contemporáneo", "Nórdico / Escandinavo", "Clásico / Rústico", "Industrial", "Vintage / Retro"], defaultValue: "Clásico / Rústico" },
    { key: "dimensions", label: "Dimensiones aprox. (An x Fo x Al)", fieldType: "text", placeholder: "Ej. 50 x 50 x 85 cm", defaultValue: "" },
    { key: "assembly", label: "Entrega y montaje", fieldType: "select", options: ["Se entrega montado", "Desmontable para transporte", "Requiere montaje"], defaultValue: "Se entrega montado" },
    { key: "color", label: "Color / Acabado", fieldType: "text", placeholder: "Ej. Roble, Nogal, Blanco", defaultValue: "" },
  ],
  moda: [
    { key: "size", label: "Talla", fieldType: "text", placeholder: "Ej. M, L, 42 EU, Talla única", defaultValue: "" },
    { key: "material", label: "Material / Tejido", fieldType: "select", options: ["Algodón / Textil", "Piel / Cuero", "Sintético / Técnico", "Vaquero / Denim", "Lana / Punto"], defaultValue: "Algodón / Textil" },
    { key: "authenticity", label: "Etiquetas / Caja", fieldType: "select", options: ["Con etiquetas o caja original", "Sin etiquetas (Original)", "Con ticket de compra"], defaultValue: "Sin etiquetas (Original)" },
    { key: "color", label: "Color principal", fieldType: "text", placeholder: "Ej. Blanco, Negro, Azul", defaultValue: "" },
  ],
  hogar: [
    { key: "applianceType", label: "Tipo de artículo", fieldType: "select", options: ["Pequeño electrodoméstico", "Limpieza / Aspiración", "Cafetera / Cocina", "Bricolaje / Herramienta", "Artículo general"], defaultValue: "Pequeño electrodoméstico" },
    { key: "powerSource", label: "Alimentación / Funcionamiento", fieldType: "select", options: ["Cable eléctrico (220V)", "Batería recargable", "Manual / Sin motor"], defaultValue: "Cable eléctrico (220V)" },
    { key: "accessories", label: "Accesorios o caja", fieldType: "select", options: ["Completo con accesorios", "En caja o maletín original", "Solo artículo principal"], defaultValue: "Completo con accesorios" },
    { key: "color", label: "Color / Acabado", fieldType: "text", placeholder: "Ej. Acero, Blanco", defaultValue: "" },
  ],
};

export function resolveCategoryFamily(category: string, name = ""): string {
  const blob = `${category} ${name}`.toLowerCase();
  if (/(rat[oó]n|mouse|mx master|deathadder|superlight|g502|trackball)/.test(blob)) return "raton";
  if (/(teclado|keyboard|keychron|switches|keycaps)/.test(blob)) return "teclado";
  if (/(audio|auricular|cascos|altavoz|wh-1000|wf-1000|airpods|earbuds|sonido|bose|sennheiser|jbl|marshall)/.test(blob)) return "audio";
  if (/(c[aá]mara|fotograf|eos|canon|nikon|fujifilm|r[eé]flex|dslr|objetivo|lente)/.test(blob)) return "camaras";
  if (/(bici|orbea|mtb|patinete|ciclismo|movilidad)/.test(blob)) return "bicicletas";
  if (/(monitor|pantalla|ultrawide|display)/.test(blob)) return "monitor";
  if (/(coche|auto|veh[ií]culo|motor|moto|furgoneta|suv|berlina|seat|bmw|audi|mercedes|volkswagen|toyota|renault|peugeot|ford|tesla)/.test(blob)) return "motor";
  if (/(m[oó]vil|telefon|iphone|smartphone|galaxy|xiaomi|redmi|pixel)/.test(blob)) return "moviles";
  if (/(consola|videojuego|switch|playstation|ps5|ps4|xbox|joy-?con)/.test(blob)) return "consolas";
  if (/(port[aá]til|macbook|laptop|inform[aá]tica|ipad|tablet|ordenador)/.test(blob)) return "informatica";
  if (/(silla|mesa|sof[aá]|mueble|mobiliario|armario|estanter[ií]a|butaca|escritorio|decoraci[oó]n|madera)/.test(blob)) return "mobiliario";
  if (/(moda|ropa|zapatilla|calzado|chaqueta|camiseta|bolso|reloj|gafas|nike|adidas)/.test(blob)) return "moda";
  return "hogar";
}

export function buildDynamicFieldsForCategory(
  category: string,
  name: string,
  existingFields: VisionDynamicField[] = [],
): VisionDynamicField[] {
  const family = resolveCategoryFamily(category, name);
  const templates = FAMILY_TEMPLATES[family] ?? FAMILY_TEMPLATES.hogar;
  const previousByKey = new Map(existingFields.map((f) => [f.key, f.value]));

  return templates.map((tpl) => {
    const prevValue = previousByKey.get(tpl.key);
    const value = prevValue !== undefined && prevValue !== "" ? prevValue : tpl.defaultValue;
    const options = tpl.options && value && !tpl.options.includes(value) ? [value, ...tpl.options] : tpl.options;
    return {
      key: tpl.key,
      label: tpl.label,
      value,
      fieldType: tpl.fieldType,
      options,
      placeholder: tpl.placeholder,
    };
  });
}

export function mapScoreToConditionLabel(score: number): ConditionLabel {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  if (clamped >= 90) return "Nuevo";
  if (clamped >= 80) return "Como nuevo";
  if (clamped >= 65) return "Buen estado";
  if (clamped >= 40) return "Desgaste visible";
  return "Para piezas";
}

export function formatDynamicFieldsSummary(fields: VisionDynamicField[], extraNotes?: string): string {
  const lines = fields
    .filter((f) => f.value.trim().length > 0)
    .map((f) => `• ${f.label}: ${f.value.trim()}`);
  if (extraNotes && extraNotes.trim().length > 0) {
    lines.push(`• Notas adicionales: ${extraNotes.trim()}`);
  }
  return lines.join("\n");
}

export interface SeoDescriptionInput {
  name: string;
  brand: string;
  model: string;
  category: string;
  conditionScore: number;
  conditionLabel: ConditionLabel;
  conditionReasoning: string;
  dynamicFields: VisionDynamicField[];
  extraNotes?: string;
}

export function buildSeoDescriptionFromFields(input: SeoDescriptionInput): string {
  const cleanName = input.name.trim() || "Artículo";
  const cleanBrand = input.brand.trim();
  const cleanModel = input.model.trim();
  const lowName = cleanName.toLowerCase();
  let itemRef = "";
  if (cleanBrand && cleanBrand.toLowerCase() !== "genérica" && !lowName.includes(cleanBrand.toLowerCase())) {
    itemRef =
      cleanModel && cleanModel.toLowerCase() !== "estándar" && !lowName.includes(cleanModel.toLowerCase())
        ? ` (${cleanBrand} ${cleanModel})`
        : ` (${cleanBrand})`;
  } else if (cleanModel && cleanModel.toLowerCase() !== "estándar" && !lowName.includes(cleanModel.toLowerCase())) {
    itemRef = ` (ref. ${cleanModel})`;
  }

  const specsSummary = formatDynamicFieldsSummary(input.dynamicFields, input.extraNotes);
  const tags = [
    cleanBrand,
    cleanModel.split(/\s+/)[0] ?? "",
    input.category.split(/\s+/)[0] ?? "",
    "segundamano",
    "oportunidad",
  ]
    .map((t) => t.toLowerCase().replace(/[^a-záéíóúñ0-9]/gi, ""))
    .filter((t) => t && !["desconocida", "generico", "generica", "estandar", "na"].includes(t));
  const hashtagLine = Array.from(new Set(tags)).map((t) => `#${t}`).join(" ");

  const sections = [
    `✨ Se vende ${cleanName}${itemRef} en estado '${input.conditionLabel}'.`,
    `🔍 Diagnóstico visual IA (${Math.round(input.conditionScore)}/100%): ${input.conditionReasoning.trim()}`,
  ];
  if (specsSummary) {
    sections.push(`📋 Características y detalles:\n${specsSummary}`);
  }
  sections.push(
    "📦 Listo para entrega en mano o envío protegido por Wallapop/Vinted. Se puede ver y probar sin compromiso.",
    `🏷️ ${hashtagLine}`,
  );
  return sections.join("\n");
}
