import { HomeView } from "@/components/dashboard/HomeView";

// Sin sesión, DashboardShell muestra el login en lugar de esta página (la sesión solo se conoce en el navegador).
export const instant = false;

export default function Home() {
  return <HomeView />;
}
