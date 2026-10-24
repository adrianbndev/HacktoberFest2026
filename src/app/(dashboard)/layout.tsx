import { DashboardShell } from "@/components/dashboard/DashboardShell";

export default function DashboardLayout({ children }: LayoutProps<"/">) {
  return <DashboardShell>{children}</DashboardShell>;
}
