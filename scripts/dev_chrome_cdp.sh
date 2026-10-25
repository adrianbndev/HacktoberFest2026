#!/usr/bin/env bash
# Chrome local con CDP para el motor de mercado (MOD-04) cuando no hay Docker.
#
# En Docker el navegador vive en el servicio `market-browser` (market-browser:9222).
# En el Mac de la demo se usa el Chrome instalado, con un perfil aparte para no
# tocar el navegador personal. El backend debe apuntar a él con CDP_URL.
set -euo pipefail

PORT="${CDP_PORT:-9222}"
PROFILE="${CHROME_PROFILE_DIR:-$HOME/.cache/lifeos-chrome}"
CHROME_BIN="${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

if curl -fsS "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
  echo "Ya hay un Chrome con CDP en :${PORT}"
  exit 0
fi

if [ ! -x "${CHROME_BIN}" ]; then
  echo "No encuentro Chrome en '${CHROME_BIN}'. Define CHROME_BIN." >&2
  exit 1
fi

mkdir -p "${PROFILE}"
echo "Arrancando Chrome (CDP :${PORT}, perfil ${PROFILE})…"
nohup "${CHROME_BIN}" \
  --remote-debugging-port="${PORT}" \
  --user-data-dir="${PROFILE}" \
  --no-first-run \
  --no-default-browser-check \
  --disable-features=Translate,MediaRouter \
  about:blank >"${PROFILE}.log" 2>&1 </dev/null &
disown

for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
    echo "Listo: exporta CDP_URL=http://127.0.0.1:${PORT} y reinicia el backend."
    exit 0
  fi
  sleep 0.25
done

echo "Chrome no respondió en :${PORT}. Revisa ${PROFILE}.log" >&2
exit 1
