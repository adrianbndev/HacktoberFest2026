"use client";

import { useState } from "react";
import { CircleCheck, Ellipsis, House, Pencil, Store, Trash2, type LucideIcon } from "lucide-react";
import type { InventoryItem } from "@/types/sdd";
import { useDashboard } from "@/components/dashboard/DashboardShell";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Menu, type MenuItem } from "@/components/ui/Menu";
import { EditItemDialog } from "./EditItemDialog";

const STATUS_ACTIONS: { status: InventoryItem["status"]; label: string; icon: LucideIcon; done: string }[] = [
  { status: "listed", label: "Marcar como publicado", icon: Store, done: "marcado como publicado" },
  { status: "sold", label: "Marcar como vendido", icon: CircleCheck, done: "marcado como vendido" },
  { status: "in_stock", label: "Volver a «En casa»", icon: House, done: "de vuelta en casa" },
];

export function ItemActions({ item }: { item: InventoryItem }) {
  const { updateItem, deleteItem } = useDashboard();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editing, setEditing] = useState(false);

  const items: MenuItem[] = [
    { label: "Editar", icon: Pencil, onSelect: () => setEditing(true) },
    ...STATUS_ACTIONS.filter(({ status }) => status !== item.status).map(({ status, label, icon, done }) => ({
      label,
      icon,
      onSelect: () =>
        updateItem({ ...item, status, lastUpdatedAt: new Date().toISOString() }, `${item.name}: ${done}.`),
    })),
    { label: "Eliminar", icon: Trash2, danger: true, onSelect: () => setConfirmDelete(true) },
  ];

  return (
    <>
      <Menu
        buttonLabel={`Más acciones para ${item.name}`}
        buttonClassName="grid size-11 place-items-center rounded-full bg-paper transition-colors hover:bg-fog-2"
        buttonContent={<Ellipsis className="size-5" aria-hidden />}
        items={items}
        placement="up"
      />
      <EditItemDialog open={editing} item={item} onClose={() => setEditing(false)} />
      <ConfirmDialog
        open={confirmDelete}
        title={`¿Eliminar ${item.name}?`}
        body="Se quitará de tu inventario y de tu patrimonio. No se puede deshacer."
        confirmLabel="Eliminar"
        onConfirm={() => {
          setConfirmDelete(false);
          deleteItem(item);
        }}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}
