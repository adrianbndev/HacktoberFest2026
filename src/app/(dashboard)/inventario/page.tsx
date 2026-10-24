import { InventoryView } from "@/components/inventory/InventoryView";

// Sin sesión, DashboardShell muestra el login en lugar de esta página (la sesión solo se conoce en el navegador).
export const instant = false;

export default function InventoryPage() {
  return <InventoryView />;
}
