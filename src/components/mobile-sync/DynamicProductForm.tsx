"use client";

import { useState } from "react";
import { Check, Loader2, Plus, RotateCcw, SlidersHorizontal, Sparkles } from "lucide-react";
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

const inputCls =
  "mt-1 w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 focus:border-zinc-900 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800/80 dark:text-zinc-100 dark:focus:border-zinc-300";

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
    setDynamicFields((prev) => buildDynamicFieldsForCategory(nextCategory, name, prev));
  }

  function updateDynamicField(key: string, nextValue: string) {
    setDynamicFields((prev) => prev.map((f) => (f.key === key ? { ...f, value: nextValue } : f)));
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
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-emerald-50 px-3.5 py-2.5 text-xs font-medium text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
        <span className="flex items-center gap-1.5">
          <Sparkles className="size-4 shrink-0" aria-hidden />
          Datos extraídos por {initialAnalysis.modelUsed ?? "Visión IA"} · Revisa y edita antes de continuar
        </span>
        {initialAnalysis.latencyMs && <span className="opacity-75">{(initialAnalysis.latencyMs / 1000).toFixed(1)}s</span>}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-xs font-medium text-zinc-600 sm:col-span-2 dark:text-zinc-300">
          Nombre del producto detectado
          <input required value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
        </label>

        <label className="text-xs font-medium text-zinc-600 sm:col-span-2 dark:text-zinc-300">
          Categoría (cambia los campos dinámicos según el tipo de objeto)
          <select value={category} onChange={(e) => handleCategoryChange(e.target.value)} className={inputCls}>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </label>

        <label className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
          Marca
          <input value={brand} onChange={(e) => setBrand(e.target.value)} className={inputCls} />
        </label>

        <label className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
          Modelo / Referencia
          <input value={model} onChange={(e) => setModel(e.target.value)} className={inputCls} />
        </label>
      </div>

      <fieldset className="rounded-2xl border border-zinc-200 bg-zinc-50/70 p-3.5 dark:border-zinc-800 dark:bg-zinc-800/40">
        <legend className="flex items-center gap-1.5 px-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-300">
          <SlidersHorizontal className="size-3.5" aria-hidden /> Campos específicos · {category}
        </legend>

        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {dynamicFields.map((field) => (
            <label key={field.key} className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
              {field.label}
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
            </label>
          ))}
        </div>

        <div className="mt-3 flex gap-2">
          <input
            value={newFieldLabel}
            onChange={(e) => setNewFieldLabel(e.target.value)}
            placeholder="Añadir otro campo (ej. N.º serie, ITV, Garantía)…"
            className="flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-900"
          />
          <button
            type="button"
            onClick={addCustomField}
            disabled={!newFieldLabel.trim()}
            className="flex items-center gap-1 rounded-xl border border-zinc-300 px-2.5 py-1.5 text-xs font-medium transition hover:bg-zinc-100 disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            <Plus className="size-3.5" aria-hidden /> Añadir
          </button>
        </div>
      </fieldset>

      <div className="rounded-2xl border border-zinc-200 p-3.5 dark:border-zinc-800">
        <div className="flex items-center justify-between text-xs font-semibold">
          <span>Estado / Salud del producto: {conditionScore}%</span>
          <span className="rounded-full bg-zinc-900 px-2.5 py-0.5 text-white dark:bg-white dark:text-zinc-900">{conditionLabel}</span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={conditionScore}
          onChange={(e) => setConditionScore(Number(e.target.value))}
          className="mt-2 w-full accent-zinc-900 dark:accent-white"
        />
        <label className="mt-2 block text-xs font-medium text-zinc-600 dark:text-zinc-300">
          Observaciones del estado físico
          <input value={conditionReasoning} onChange={(e) => setConditionReasoning(e.target.value)} className={inputCls} />
        </label>
      </div>

      <details className="rounded-2xl border border-zinc-200 px-3.5 py-2.5 text-xs dark:border-zinc-800">
        <summary className="cursor-pointer font-medium text-zinc-700 dark:text-zinc-300">
          Opciones avanzadas: Anuncio SEO y notas adicionales
        </summary>
        <div className="mt-3 flex flex-col gap-2.5">
          <label className="font-medium text-zinc-600 dark:text-zinc-300">
            Título SEO sugerido
            <input value={seoTitle} maxLength={65} onChange={(e) => setSeoTitle(e.target.value)} className={inputCls} />
          </label>
          <label className="font-medium text-zinc-600 dark:text-zinc-300">
            Descripción SEO
            <textarea rows={2} value={seoDescription} onChange={(e) => setSeoDescription(e.target.value)} className={inputCls} />
          </label>
          <label className="font-medium text-zinc-600 dark:text-zinc-300">
            Notas extra del vendedor
            <input value={extraNotes} onChange={(e) => setExtraNotes(e.target.value)} placeholder="Defectos no visibles, extras…" className={inputCls} />
          </label>
        </div>
      </details>

      <div className="flex gap-2.5 pt-1">
        <button
          type="button"
          onClick={onRetake}
          disabled={submitting}
          className="flex items-center justify-center gap-1.5 rounded-2xl border border-zinc-200 px-4 py-3 text-xs font-semibold transition hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          <RotateCcw className="size-4" aria-hidden /> Otra foto
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-zinc-900 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60 dark:bg-white dark:text-zinc-900"
        >
          {submitting ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Check className="size-4" aria-hidden />}
          {submitting ? "Tasando producto…" : "Confirmar datos y continuar"}
        </button>
      </div>
    </form>
  );
}
