"use client";

import { useEffect, useState } from "react";

const ROLL_MS = 900;
const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - 2 ** (-10 * t));
const prefersReducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Cuando el valor cambia, la cifra rueda del valor anterior al nuevo (como un saldo que recibe dinero).
export function useRollingNumber(target?: number) {
  const [previousTarget, setPreviousTarget] = useState(target);
  const [rollFrom, setRollFrom] = useState<number>();
  const [progress, setProgress] = useState(0);

  if (target !== previousTarget) {
    setPreviousTarget(target);
    const canRoll = previousTarget !== undefined && target !== undefined && !prefersReducedMotion();
    setRollFrom(canRoll ? previousTarget : undefined);
    setProgress(0);
  }

  useEffect(() => {
    if (rollFrom === undefined) return;
    let start: number | undefined;
    let frame = requestAnimationFrame(function tick(now) {
      start ??= now;
      const t = Math.min(1, (now - start) / ROLL_MS);
      setProgress(t);
      if (t < 1) frame = requestAnimationFrame(tick);
      else setRollFrom(undefined);
    });
    return () => cancelAnimationFrame(frame);
  }, [rollFrom, target]);

  if (rollFrom === undefined || target === undefined) return target;
  return Math.round(rollFrom + (target - rollFrom) * easeOutExpo(progress));
}
