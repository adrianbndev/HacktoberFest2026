#!/usr/bin/env bash
# Launch Xvfb + a headful browser with CDP on 9223 (loopback) and expose it
# through the CDP proxy on 9222. Never headless, never --enable-automation,
# and Chrome is started by us (not by the MCP server).
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
CHROME_PORT="${CHROME_PORT:-9223}"
PROXY_PORT="${PROXY_PORT:-9222}"

# A restart can leave stale X/profile locks from the previous launch.
rm -f "/tmp/.X${DISPLAY#:}-lock"
rm -f /chrome-profile/SingletonLock /chrome-profile/SingletonCookie /chrome-profile/SingletonSocket

Xvfb "${DISPLAY}" -screen 0 1440x900x24 -nolisten tcp &
XVFB_PID=$!

CHROME_BIN="${CHROME_BIN:-google-chrome-stable}"
if ! command -v "${CHROME_BIN}" >/dev/null 2>&1; then
    CHROME_BIN="chromium"
fi

# Wait until Xvfb accepts connections (bounded, no host display needed).
for _ in $(seq 1 50); do
    if xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
        break
    fi
    sleep 0.1
done

"${CHROME_BIN}" \
    --remote-debugging-port="${CHROME_PORT}" \
    --remote-debugging-address=127.0.0.1 \
    --remote-allow-origins='*' \
    --lang=es-ES \
    --accept-lang=es-ES,es \
    --user-data-dir=/chrome-profile \
    --no-first-run \
    --no-default-browser-check \
    --no-sandbox \
    --disable-dev-shm-usage \
    --start-maximized \
    about:blank &
CHROME_PID=$!

for _ in $(seq 1 100); do
    if curl -fsS "http://127.0.0.1:${CHROME_PORT}/json/version" >/dev/null 2>&1; then
        break
    fi
    sleep 0.2
done

python3 /usr/local/bin/cdp_proxy.py \
    --listen-port "${PROXY_PORT}" \
    --upstream-port "${CHROME_PORT}" &
PROXY_PID=$!

cleanup() {
    kill "${PROXY_PID}" "${CHROME_PID}" "${XVFB_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait -n "${PROXY_PID}" "${CHROME_PID}" "${XVFB_PID}"
