import {
  Bike,
  Camera,
  Car,
  Gamepad2,
  Guitar,
  Headphones,
  Laptop,
  Package,
  Shirt,
  Smartphone,
  Sofa,
  WashingMachine,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import type { InventoryItem, MarketPlatform } from "@/types/sdd";

const eur = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const shortDay = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short" });
const clock = new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit" });
const list = new Intl.ListFormat("es-ES", { type: "conjunction" });
const DAY_MS = 86_400_000;

export const formatEur = (amount: number) => eur.format(amount);
export const formatTime = (iso: string) => clock.format(new Date(iso));
export const formatShortDay = (iso: string) => shortDay.format(new Date(iso));

// "Hoy", "Ayer" o "24 oct", para agrupar las tasaciones como movimientos de un banco.
export function formatDayLabel(iso: string, now = new Date()) {
  const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const days = Math.round((startOfDay(now) - startOfDay(new Date(iso))) / DAY_MS);
  if (days === 0) return "Hoy";
  if (days === 1) return "Ayer";
  return formatShortDay(iso);
}

export const STATUS_LABEL: Record<InventoryItem["status"], string> = {
  in_stock: "En casa",
  listed: "Publicado",
  reserved: "Reservado",
  sold: "Vendido",
};

export const PLATFORM_LABEL: Record<MarketPlatform, string> = {
  wallapop: "Wallapop",
  vinted: "Vinted",
  milanuncios: "Milanuncios",
  ebay: "eBay",
};

export function formatPlatforms(item: InventoryItem) {
  const platforms = item.priceHistory.at(-1)?.platforms ?? item.comparableListings.map((listing) => listing.platform);
  return list.format([...new Set(platforms)].map((platform) => PLATFORM_LABEL[platform]));
}

// Las categorías vienen de la Visión IA en texto libre; se reconocen por palabra clave.
const CATEGORY_ICONS: [string, LucideIcon][] = [
  ["móvil", Smartphone],
  ["telefon", Smartphone],
  ["consola", Gamepad2],
  ["videojuego", Gamepad2],
  ["informática", Laptop],
  ["portátil", Laptop],
  ["audio", Headphones],
  ["sonido", Headphones],
  ["cámara", Camera],
  ["foto", Camera],
  ["bici", Bike],
  ["movilidad", Bike],
  ["motor", Car],
  ["mobiliario", Sofa],
  ["decoración", Sofa],
  ["moda", Shirt],
  ["ropa", Shirt],
  ["hogar", WashingMachine],
  ["electrodom", WashingMachine],
  ["bricolaje", Wrench],
  ["herramienta", Wrench],
  ["instrumento", Guitar],
];

export function categoryIcon(category: string): LucideIcon {
  const normalized = category.toLowerCase();
  return CATEGORY_ICONS.find(([keyword]) => normalized.includes(keyword))?.[1] ?? Package;
}
