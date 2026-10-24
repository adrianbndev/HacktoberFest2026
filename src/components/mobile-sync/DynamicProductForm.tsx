"use client";

import { useState } from "react";
import { Check, Loader2, Plus, RotateCcw, ScanSearch, SlidersHorizontal, X } from "lucide-react";
import { ConditionChip } from "@/components/inventory/HealthScoreBadge";
import {
  PRODUCT_CATEGORIES,
  buildDynamicFieldsForCategory,
  mapScoreToConditionLabel,
} from "@/lib/vision/category-fields";
import type { VisionAnalysisResult, VisionDynamicField } from "@/types/sdd";

export interface DynamicProductFormProps {
  initialAnalysis: VisionAnalysisResult;
  submitting: boolean;
  onConfirm: (adjusted: VisionAnalysisResult, extraNotes: string) => void;
  onRetake: () => void;
}

const FIELD = "mt-1.5 w-full rounded-inner border border-line bg-paper px-3.5 text-[15px] text-ink transition-colors focus:border-accent";
const inputCls = `${FIELD} h-11`;
const textareaCls = `${FIELD} py-2.5 leading-relaxed`;
const labelCls = "text-[13px] font-medium text-ink-2";

export function DynamicProductForm({ initialAnalysis, submitting, onConfirm, onRetake }: DynamicProductFormProps) {
  const [name, setName] = useState(initialAnalysis.name);
  const [category, setCategory] = useState(initialAnalysis.category);
  const [brand, setBrand] = useState(initialAnalysis.brand);
  const [model, setModel] = useState(initialAnalysis.model);
  const [conditionScore, setConditionScore] = useState(initialAnalysis.conditionScore);
  const [conditionReasoning, setConditionReasoning] = useState(initialAnalysis.conditionReasoning);
  const [seoTitle, setSeoTitle] = useState(initialAnalysis.seoTitle);
  const [seoDescription, setSeoDescription] = useState(initialAnalysis.seoDescription);
  const [dynamicFields, setDynamicFields] = useState<VisionDynamicField[]>(() =>
    initialAnalysis.dynamicFields && initialAnalysis.dynamicFields.length > 0
      ? initialAnalysis.dynamicFields
      : buildDynamicFieldsForCategory(initialAnalysis.category, initialAnalysis.name),
  );
  const [extraNotes, setExtraNotes] = useState("");
  const [newFieldLabel, setNewFieldLabel] = useState("");

  const conditionLabel = mapScoreToConditionLabel(conditionScore);
  const categories = PRODUCT_CATEGORIES.includes(category) ? PRODUCT_CATEGORIES : [category, ...PRODUCT_CATEGORIES];

  function handleCategoryChange(nextCategory: string) {
    setCategory(nextCategory);
    setDynamicFields((prev) => buildDynamicFieldsForCategory(nextCategory, "", prev));
  }

  function updateDynamicField(key: string, nextValue: string) {
    setDynamicFields((prev) => prev.map((f) => (f.key === key ? { ...f, value: nextValue } : f)));
  }

  function removeDynamicField(key: string) {
    setDynamicFields((prev) => prev.filter((f) => f.key !== key));
  }

  function addCustomField() {
    const clean = newFieldLabel.trim();
    if (!clean) return;
    setDynamicFields((prev) => [
      ...prev,
      { key: `custom_${Date.now().toString(36)}`, label: clean, value: "", fieldType: "text", placeholder: `Valor de ${clean.toLowerCase()}…` },
    ]);
    setNewFieldLabel("");
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    onConfirm(
      {
        ...initialAnalysis,
        name: name.trim() || initialAnalysis.name,
        category: category.trim() || initialAnalysis.category,
        brand: brand.trim() || "Genérica",
        model: model.trim() || "Estándar",
        conditionScore,
        conditionLabel,
        conditionReasoning: conditionReasoning.trim() || initialAnalysis.conditionReasoning,
        seoTitle: seoTitle.trim() || initialAnalysis.seoTitle,
        seoDescription: seoDescription.trim() || initialAnalysis.seoDescription,
        dynamicFields,
      },
      extraNotes,
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-inner bg-fog px-4 py-3 text-sm text-ink-2">
        <span className="flex items-center gap-2">
          <ScanSearch className="size-4.5 shrink-0 text-accent" aria-hidden />
          Datos reconocidos por {initialAnalysis.modelUsed ?? "la IA"}. Revísalos antes de tasar.
        </span>
        {initialAnalysis.latencyMs && (
          <span className="tabular-nums">{(initialAnalysis.latencyMs / 1000).toFixed(1)} s</span>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-12">
        <label className={`${labelCls} sm:col-span-2 lg:col-span-5`}>
          Nombre del objeto
          <input required value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
        </label>

        <label className={`${labelCls} sm:col-span-2 lg:col-span-3`}>
          Categoría
          <select value={category} onChange={(e) => handleCategoryChange(e.target.value)} className={inputCls}>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </label>

        <label className={`${labelCls} lg:col-span-2`}>
          Marca<input value={brand} onChange={(e) => setBrand(e.target.value)} className={inputCls} />
        </label>
        <label className={`${labelCls} lg:col-span-2`}>
          Modelo<input value={model} onChange={(e) => setModel(e.target.value)} className={inputCls} />
        </label>
      </div>

      <fieldset className="rounded-panel bg-fog p-4">
        <legend className="float-left mb-3 flex w-full items-center gap-2 text-[15px] font-semibold">
          <SlidersHorizontal className="size-4" aria-hidden /> Datos de {category}
        </legend>

        <div className="clear-both grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {dynamicFields.map((field) => (
            <div key={field.key} className={labelCls}>
              <div className="flex items-center justify-between gap-1">
                <span>{field.label}</span>
                {dynamicFields.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeDynamicField(field.key)}
                    aria-label={`Quitar ${field.label}`}
                    title="Quitar este campo"
                    className="grid size-6 place-items-center rounded-full transition-colors hover:bg-fog-2 hover:text-ink"
                  >
                    <X className="size-3.5" aria-hidden />
                  </button>
                )}
              </div>
              {field.fieldType === "select" && field.options && field.options.length > 0 ? (
                <select value={field.value} onChange={(e) => updateDynamicField(field.key, e.target.value)} className={inputCls}>
                  {field.options.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : (
                <input
                  type={field.fieldType === "number" ? "number" : "text"}
                  value={field.value}
                  placeholder={field.placeholder ?? ""}
                  onChange={(e) => updateDynamicField(field.key, e.target.value)}
                  className={inputCls}
                />
              )}
            </div>
          ))}
        </div>

        <div className="mt-3 flex gap-2">
          <input
            value={newFieldLabel}
            onChange={(e) => setNewFieldLabel(e.target.value)}
            placeholder="Añadir otro dato (n.º de serie, garantía…)"
            aria-label="Nombre del dato que quieres añadir"
            className="h-10 min-w-0 flex-1 rounded-inner border border-line bg-paper px-3 text-sm transition-colors focus:border-accent"
          />
          <button
            type="button"
            onClick={addCustomField}
            disabled={!newFieldLabel.trim()}
            className="flex h-10 items-center gap-1 rounded-full bg-paper px-4 text-sm font-semibold ring-1 ring-line transition-colors hover:bg-fog-2 disabled:opacity-40"
          >
            <Plus className="size-4" aria-hidden /> Añadir
          </button>
        </div>
      </fieldset>

      <div className="grid items-start gap-4 lg:grid-cols-2">
      <div className="rounded-panel bg-fog p-4">
        <div className="flex items-center justify-between gap-3 text-[15px] font-semibold">
          <span className="tabular-nums">Estado: {conditionScore}/100</span>
          <ConditionChip label={conditionLabel} />
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={conditionScore}
          onChange={(e) => setConditionScore(Number(e.target.value))}
          aria-label="Estado del objeto, de 0 a 100"
          className="mt-3 w-full accent-accent"
        />
        <label className={`mt-2 block ${labelCls}`}>
          Qué se ve en la foto
          <input value={conditionReasoning} onChange={(e) => setConditionReasoning(e.target.value)} className={inputCls} />
        </label>
      </div>

      <details open className="rounded-panel bg-fog px-4 py-3">
        <summary className="text-[15px] font-semibold">Anuncio y notas (opcional)</summary>
        <div className="mt-3 flex flex-col gap-3">
          <label className={labelCls}>
            Título del anuncio
            <input value={seoTitle} maxLength={65} onChange={(e) => setSeoTitle(e.target.value)} className={inputCls} />
          </label>
          <label className={labelCls}>
            Descripción del anuncio
            <textarea
              rows={5}
              value={seoDescription}
              onChange={(e) => setSeoDescription(e.target.value)}
              className={`${textareaCls} min-h-32 resize-y`}
            />
          </label>
          <label className={labelCls}>
            Tus notas
            <input value={extraNotes} onChange={(e) => setExtraNotes(e.target.value)} placeholder="Defectos que no se ven, extras…" className={inputCls} />
          </label>
        </div>
      </details>
      </div>

      <div className="flex justify-end gap-2.5 pt-1">
        <button
          type="button"
          onClick={onRetake}
          disabled={submitting}
          className="flex h-12 items-center justify-center gap-1.5 rounded-full bg-fog px-5 text-[15px] font-semibold transition-colors hover:bg-fog-2 disabled:opacity-50"
        >
          <RotateCcw className="size-4" aria-hidden /> Otra foto
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-accent sm:flex-none sm:px-8 text-[15px] font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-60"
        >
          {submitting ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Check className="size-4" aria-hidden />}
          {submitting ? "Tasando…" : "Confirmar y tasar"}
        </button>
      </div>
    </form>
  );
}
