#!/usr/bin/env node
/**
 * SDD Gatekeeper & Clean Code Verification Harness
 * Works out-of-the-box with Node.js (zero external npm dependencies required).
 * Compatible with Antigravity CLI, Claude Code, and OpenCode.
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();

const REQUIRED_SDD_FILES = [
  'AGENTS.md',
  'CLAUDE.md',
  '.agent/roadmap.md',
  '.agent/architecture.md',
  '.agent/mcp/stealth-market-mcp.md',
  '.agent/rules/hackathon-guardrails.md',
  '.agent/rules/clean-code-solid.md',
  '.agent/rules/testing-and-quality-gates.md',
  '.agent/decisions/001-tech-stack-and-options-matrix.md',
  '.agent/modules/INDEX-control-tower.md',
  '.agent/modules/MOD-00-foundation-store-types.md',
  '.agent/modules/MOD-01-auth-and-inventory-ui.md',
  '.agent/modules/MOD-02-mobile-pc-sync.md',
  '.agent/modules/MOD-03-vision-health-seo.md',
  '.agent/modules/MOD-04-mcp-stealth-valuation.md',
  '.agent/modules/MOD-05-price-tracker-and-alerts.md',
  '.agent/modules/MOD-06-lifeos-weather-plans-calendar.md',
  '.agent/modules/MOD-07-github-hacktoberfest-ai.md',
  '.agent/tracks/team-tracks-contract.md',
];

const MAX_LINES_PER_FILE = 250;

function logHeader(title) {
  console.log(`\n========================================================`);
  console.log(`🛡️  ${title}`);
  console.log(`========================================================`);
}

function checkSddFiles() {
  logHeader('1. SDD Documentation & Spec Integrity');
  let missing = 0;
  for (const relPath of REQUIRED_SDD_FILES) {
    const fullPath = path.join(ROOT, relPath);
    if (fs.existsSync(fullPath)) {
      console.log(`  ✅ ${relPath}`);
    } else {
      console.error(`  ❌ MISSING: ${relPath}`);
      missing++;
    }
  }
  return missing === 0;
}

function parseRoadmapProgress() {
  logHeader('2. SDD Level Gatekeeping & Roadmap Progress');
  const roadmapPath = path.join(ROOT, '.agent/roadmap.md');
  if (!fs.existsSync(roadmapPath)) return {};

  const content = fs.readFileSync(roadmapPath, 'utf8');
  const sections = content.split(/^## /m).slice(1);
  const levelStats = {};

  for (const section of sections) {
    const firstLine = section.split('\n')[0].trim();
    const doneMatches = section.match(/^- \[x\]/gm) || [];
    const todoMatches = section.match(/^- \[ \]/gm) || [];
    const total = doneMatches.length + todoMatches.length;
    const pct = total > 0 ? Math.round((doneMatches.length / total) * 100) : 100;
    levelStats[firstLine] = { done: doneMatches.length, total, pct };
    const statusIcon = pct === 100 ? '🟢 COMPLETE' : pct > 0 ? '🚧 IN PROGRESS' : '⏳ PENDING';
    console.log(`  ${statusIcon} | ${firstLine} -> ${doneMatches.length}/${total} (${pct}%)`);
  }
  return levelStats;
}

function walkFiles(dir, extFilter = ['.ts', '.tsx']) {
  if (!fs.existsSync(dir)) return [];
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && !['node_modules', '.next', '.git'].includes(entry.name)) {
      results.push(...walkFiles(full, extFilter));
    } else if (entry.isFile() && extFilter.includes(path.extname(entry.name))) {
      results.push(full);
    }
  }
  return results;
}

function checkCleanCodeAndSolid() {
  logHeader('3. Clean Code, SOLID & Architecture Audit (src/ & backend/)');
  const srcDir = path.join(ROOT, 'src');
  const backendDir = path.join(ROOT, 'backend');
  if (!fs.existsSync(srcDir) && !fs.existsSync(backendDir)) {
    console.log('  ℹ️  src/ and backend/ directories not created yet (Pre-initialization phase).');
    return true;
  }

  const tsFiles = walkFiles(srcDir, ['.ts', '.tsx']);
  const pyFiles = walkFiles(backendDir, ['.py']);
  const files = [...tsFiles, ...pyFiles];
  let violations = 0;

  for (const file of files) {
    const rel = path.relative(ROOT, file);
    const content = fs.readFileSync(file, 'utf8');
    const lines = content.split('\n').length;

    if (lines > MAX_LINES_PER_FILE) {
      console.error(`  ❌ SRP Violation (File too large: ${lines} > ${MAX_LINES_PER_FILE} lines): ${rel}`);
      violations++;
    }

    if (file.endsWith('.ts') || file.endsWith('.tsx')) {
      const explicitAnyRegex = /:\s*any\b|<any>|as\s+any\b/g;
      const anyMatches = content.match(explicitAnyRegex);
      if (anyMatches) {
        console.error(`  ❌ TypeScript Strict Violation (${anyMatches.length}x explicit 'any'): ${rel}`);
        violations++;
      }
    }
  }

  if (violations === 0) {
    console.log(`  ✅ Audited ${tsFiles.length} TS/TSX files and ${pyFiles.length} Python files: 0 SRP or strict typing violations.`);
  }
  return violations === 0;
}

const sddOk = checkSddFiles();
parseRoadmapProgress();
const codeOk = checkCleanCodeAndSolid();

console.log('\n========================================================');
if (sddOk && codeOk) {
  console.log('✅ SDD HARNESS VERIFICATION PASSED');
  process.exit(0);
} else {
  console.error('❌ SDD HARNESS FOUND ISSUES — Review output above.');
  process.exit(1);
}
