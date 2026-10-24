// Logotipo de SmartLoot: una etiqueta de precio sobre el acento, junto al nombre.
export function Brand({ size = "md" }: { size?: "md" | "lg" }) {
  return (
    <span className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className={size === "lg" ? "size-10" : "size-8"} aria-hidden>
        <rect width="32" height="32" rx="9" fill="var(--accent)" />
        <path
          fill="#fff"
          fillRule="evenodd"
          d="M9 7.5h6.9c.6 0 1.1.2 1.5.6l7.5 7.5a2.1 2.1 0 0 1 0 3l-6 6a2.1 2.1 0 0 1-3 0l-7.5-7.5a2.1 2.1 0 0 1-.6-1.5V9A1.5 1.5 0 0 1 9 7.5Zm3.6 6.6a1.6 1.6 0 1 0 0-3.2 1.6 1.6 0 0 0 0 3.2Z"
        />
      </svg>
      <span className={`font-display font-semibold tracking-[-0.03em] ${size === "lg" ? "text-2xl" : "text-[21px]"}`}>
        SmartLoot
      </span>
    </span>
  );
}
