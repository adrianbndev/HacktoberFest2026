"use client";

import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { X } from "lucide-react";
import type { InventoryItem } from "@/types/sdd";
import { useDashboard } from "@/components/dashboard/DashboardShell";
import { PRODUCT_CATEGORIES } from "@/lib/vision/category-fields";
import { STATUS_LABEL, formatEur } from "./format";

interface EditItemDialogProps {
  open: boolean;
  item: InventoryItem;
  onClose: () => void;
}

const FIELD =
  "mt-1.5 w-full rounded-inner border border-line bg-paper px-3.5 text-[15px] text-ink transition-colors focus:border-accent";
const INPUT = `${FIELD} h-11`;
const TEXTAREA = `${FIELD} py-2.5 leading-relaxed`;
const STATUSES = Object.entries(STATUS_LABEL) as [InventoryItem["status"], string][];

// Edición a mano de los datos de un objeto; el estado y los precios siguen siendo los de la tasación.
export function EditItemDialog({ open, item, onClose }: EditItemDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (open && !dialog?.open) dialog?.showModal();
    if (!open && dialog?.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby={titleId}
      className="m-auto max-h-[92dvh] w-[min(94vw,36rem)] overflow-y-auto rounded-panel bg-paper p-6 text-ink backdrop:bg-ink/50 sm:p-7"
    >
      {/* El formulario se monta en cada apertura, así arranca siempre con los datos actuales del objeto. */}
      {open && <EditItemForm item={item} titleId={titleId} onClose={onClose} />}
    </dialog>
  );
}

function EditItemForm({ item, titleId, onClose }: { item: InventoryItem; titleId: string; onClose: () => void }) {
  const { updateItem } = useDashboard();
  const [name, setName] = useState(item.name);
  const id = useId();
  const categories = PRODUCT_CATEGORIES.includes(item.category)
    ? PRODUCT_CATEGORIES
    : [item.category, ...PRODUCT_CATEGORIES];

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const text = (field: string) => String(data.get(field) ?? "").trim();
    const updated: InventoryItem = {
      ...item,
      name: name.trim(),
      brand: text("brand"),
      model: text("model"),
      category: text("category"),
      status: text("status") as InventoryItem["status"],
      details: text("details") || undefined,
      seoTitle: text("seoTitle"),
      seoDescription: text("seoDescription"),
      lastUpdatedAt: new Date().toISOString(),
    };
    updateItem(updated, `${updated.name}: cambios guardados.`);
    onClose();
  }

  return (
    <form onSubmit={save}>
      <div className="flex items-start justify-between gap-4">
        <h2 id={titleId} className="text-lg font-semibold">Editar objeto</h2>
        <button
          type="button"
          aria-label="Cerrar"
          onClick={onClose}
          className="-mr-1 -mt-1 grid size-9 place-items-center rounded-full transition-colors hover:bg-fog"
        >
          <X className="size-5" aria-hidden />
        </button>
      </div>
      <p className="mt-2 rounded-inner bg-fog px-4 py-3 text-[13px] leading-relaxed text-ink-2">
        <span className="font-semibold text-ink">
          {item.conditionLabel} ({item.conditionScore}/100) · <span className="tabular-nums">{formatEur(item.priceMin)}</span>{" "}
          a <span className="tabular-nums">{formatEur(item.priceMax)}</span>, precio justo{" "}
          <span className="tabular-nums">{formatEur(item.priceAvg)}</span>
        </span>
        <br />
        El estado y los precios salen de la tasación y no se editan a mano.
      </p>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <Field id={`${id}-name`} label="Nombre" wide>
          <input
            id={`${id}-name`}
            name="name"
            required
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
            className={INPUT}
          />
        </Field>
        <Field id={`${id}-brand`} label="Marca">
          <input id={`${id}-brand`} name="brand" maxLength={60} defaultValue={item.brand} className={INPUT} />
        </Field>
        <Field id={`${id}-model`} label="Modelo">
          <input id={`${id}-model`} name="model" maxLength={80} defaultValue={item.model} className={INPUT} />
        </Field>
        <Field id={`${id}-category`} label="Categoría">
          <select id={`${id}-category`} name="category" defaultValue={item.category} className={INPUT}>
            {categories.map((category) => (
              <option key={category} value={category}>{category || "Sin categoría"}</option>
            ))}
          </select>
        </Field>
        <Field id={`${id}-status`} label="Situación">
          <select id={`${id}-status`} name="status" defaultValue={item.status} className={INPUT}>
            {STATUSES.map(([status, label]) => (
              <option key={status} value={status}>{label}</option>
            ))}
          </select>
        </Field>
        <Field id={`${id}-details`} label="Notas (opcional)" wide>
          <textarea
            id={`${id}-details`}
            name="details"
            rows={2}
            maxLength={500}
            defaultValue={item.details ?? ""}
            placeholder="Ej. incluye cargador y caja original"
            className={TEXTAREA}
          />
        </Field>
        <Field id={`${id}-seoTitle`} label="Título del anuncio" wide>
          <input id={`${id}-seoTitle`} name="seoTitle" maxLength={100} defaultValue={item.seoTitle} className={INPUT} />
        </Field>
        <Field id={`${id}-seoDescription`} label="Descripción del anuncio" wide>
          <textarea
            id={`${id}-seoDescription`}
            name="seoDescription"
            rows={5}
            maxLength={2000}
            defaultValue={item.seoDescription}
            className={TEXTAREA}
          />
        </Field>
      </div>

      {/* Fija abajo: en pantallas bajas el formulario hace scroll y los botones siguen a mano. */}
      <div className="sticky -bottom-6 -mx-6 -mb-6 mt-6 flex justify-end gap-2 border-t border-line bg-paper px-6 py-4 sm:-bottom-7 sm:-mx-7 sm:-mb-7 sm:px-7">
        <button
          type="button"
          onClick={onClose}
          className="h-11 rounded-full bg-fog px-5 text-[15px] font-semibold transition-colors hover:bg-fog-2"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={name.trim() === ""}
          className="h-11 rounded-full bg-accent px-5 text-[15px] font-semibold text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          Guardar cambios
        </button>
      </div>
    </form>
  );
}

function Field({ id, label, wide = false, children }: { id: string; label: string; wide?: boolean; children: ReactNode }) {
  return (
    <div className={wide ? "sm:col-span-2" : undefined}>
      <label htmlFor={id} className="text-[13px] font-medium text-ink-2">{label}</label>
      {children}
    </div>
  );
}
