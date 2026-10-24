---
name: mobile-sync-debugger
description: >-
  Use this skill when building, testing, or debugging the Mobile-to-PC camera synchronization flow
  (MOD-02), QR code LAN IP generation, client-side Canvas image compression, or SSE/short-polling
  session state transitions.
---

# 📱 Mobile-PC Sync & Camera Capture Skill (`MOD-02`)

This skill provides diagnostic tools and simulation procedures for the **Mobile Camera $\leftrightarrow$ Web PC** real-time flow (`Track B - Adri`).

## Key Guardrails Enforced

1. **Zero HTTPS Lockout on Mobile:** Always use `<input type="file" accept="image/*" capture="environment" />` as the primary trigger so mobile browsers on local LAN (`http://192.168.x.x:3000`) never fail with `navigator.mediaDevices is undefined`.
2. **Client-Side Canvas Compression:** Compress captured photos to max $800\text{ px}$ and JPEG quality $0.75$ ($< 200\text{ KB}$) before sending `PUT /api/capture-session/[sessionId]`.
3. **Instant PC Wakeup ($< 1.5\text{ s}$):** The PC modal polls or streams `/api/capture-session/[sessionId]` every $1.2\text{ s}$ and automatically triggers Vision AI (`MOD-03`) + MCP Stealth Valuation (`MOD-04`) the instant `status === 'photo_uploaded'`.

---

## Diagnostic & Simulation Steps

### Step 1: Detect Local LAN IP for QR Code Generation
Run the helper script to inspect active LAN IPv4 interfaces:
```bash
node .agent/skills/mobile-sync-debugger/scripts/detect-lan-and-simulate.mjs --info
```

### Step 2: Simulate a Mobile Camera Upload via CLI (End-to-End Test)
When the Next.js server is running on port 3000, you can simulate a mobile phone connecting to a session and uploading a compressed product photo without needing a physical phone:
```bash
node .agent/skills/mobile-sync-debugger/scripts/detect-lan-and-simulate.mjs --simulate <sessionId>
```
*(See [detect-lan-and-simulate.mjs](./scripts/detect-lan-and-simulate.mjs)).*
