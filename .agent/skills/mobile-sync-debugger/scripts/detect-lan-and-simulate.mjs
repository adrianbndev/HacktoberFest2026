#!/usr/bin/env node
/**
 * Mobile-PC Sync Diagnostic & CLI Simulation Tool
 * 1. --info: Detects LAN IPv4 addresses for QR code reachability on hackathon Wi-Fi.
 * 2. --simulate <sessionId> [baseUrl]: Simulates a mobile phone connecting and uploading a compressed JPEG.
 */
import os from 'node:os';

function getLanAddresses() {
  const nets = os.networkInterfaces();
  const results = [];
  for (const name of Object.keys(nets)) {
    for (const net of nets[name] || []) {
      if (net.family === 'IPv4' && !net.internal) {
        results.push({ interface: name, address: net.address });
      }
    }
  }
  return results;
}

// Tiny valid 1x1 JPEG data URL for headless E2E session testing
const SAMPLE_PRODUCT_DATA_URL =
  'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=';

async function simulateMobileCapture(sessionId, baseUrl = 'http://localhost:3000') {
  const endpoint = `${baseUrl}/api/capture-session/${encodeURIComponent(sessionId)}`;
  console.log(`📱 [1/2] Simulating mobile connection to ${endpoint}...`);

  const connectRes = await fetch(endpoint, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: 'mobile_connected' }),
  });
  if (!connectRes.ok) {
    throw new Error(`Failed mobile_connected: HTTP ${connectRes.status}`);
  }
  console.log('  ✅ PC notified: status = mobile_connected');

  await new Promise((r) => setTimeout(r, 600));

  console.log(`📸 [2/2] Uploading compressed camera photo to ${endpoint}...`);
  const uploadRes = await fetch(endpoint, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      status: 'photo_uploaded',
      photoDataUrl: SAMPLE_PRODUCT_DATA_URL,
    }),
  });
  if (!uploadRes.ok) {
    throw new Error(`Failed photo_uploaded: HTTP ${uploadRes.status}`);
  }
  console.log('  ✅ Photo uploaded! PC should now automatically start Vision AI + MCP Stealth.');
}

const args = process.argv.slice(2);
if (args.includes('--simulate')) {
  const idx = args.indexOf('--simulate');
  const sessionId = args[idx + 1] || 'demo-session-01';
  const baseUrl = args[idx + 2] || 'http://localhost:3000';
  simulateMobileCapture(sessionId, baseUrl).catch((err) => {
    console.error('❌ Simulation error:', err.message);
    process.exit(1);
  });
} else {
  console.log('📡 Detected Local LAN IPv4 Interfaces for Mobile QR Sync:');
  const ips = getLanAddresses();
  if (ips.length === 0) {
    console.log('  ⚠️ No external LAN IPv4 found. Use localhost or `npx cloudflared tunnel --url http://localhost:3000`');
  } else {
    for (const item of ips) {
      console.log(`  ✅ ${item.interface}: http://${item.address}:3000`);
    }
  }
}
