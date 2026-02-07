#!/usr/bin/env node
/**
 * memory-diff - Compare memory files between sessions
 * 
 * Usage:
 *   node memory-diff.js                    # Compare yesterday to today
 *   node memory-diff.js 2026-02-01         # Compare specific date to today
 *   node memory-diff.js 2026-01-30 2026-02-01  # Compare two specific dates
 * 
 * Shows what changed in your memory between sessions.
 */

const fs = require('fs');
const path = require('path');

// Config - adjust to your workspace
const MEMORY_DIR = process.env.MEMORY_DIR || path.join(__dirname, '..', 'memory');

function getDateStr(daysAgo = 0) {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return d.toISOString().split('T')[0];
}

function readMemoryFile(dateStr) {
  const filePath = path.join(MEMORY_DIR, `${dateStr}.md`);
  if (fs.existsSync(filePath)) {
    return {
      exists: true,
      content: fs.readFileSync(filePath, 'utf-8'),
      path: filePath
    };
  }
  return { exists: false, content: '', path: filePath };
}

function getLines(content) {
  return content.split('\n').filter(line => line.trim());
}

function diffMemory(oldContent, newContent) {
  const oldLines = new Set(getLines(oldContent));
  const newLines = new Set(getLines(newContent));
  
  const added = [...newLines].filter(line => !oldLines.has(line));
  const removed = [...oldLines].filter(line => !newLines.has(line));
  
  return { added, removed };
}

function formatSection(title, lines, prefix) {
  if (lines.length === 0) return '';
  
  let output = `\n${title}\n${'─'.repeat(40)}\n`;
  lines.forEach(line => {
    // Truncate long lines for readability
    const display = line.length > 100 ? line.substring(0, 97) + '...' : line;
    output += `${prefix} ${display}\n`;
  });
  return output;
}

function main() {
  const args = process.argv.slice(2);
  
  let date1, date2;
  
  if (args.length === 0) {
    date1 = getDateStr(1); // yesterday
    date2 = getDateStr(0); // today
  } else if (args.length === 1) {
    date1 = args[0];
    date2 = getDateStr(0);
  } else {
    date1 = args[0];
    date2 = args[1];
  }
  
  console.log(`\n🧠 Memory Diff: ${date1} → ${date2}\n`);
  
  const old = readMemoryFile(date1);
  const new_ = readMemoryFile(date2);
  
  if (!old.exists && !new_.exists) {
    console.log(`❌ No memory files found for either date.`);
    console.log(`   Looked for: ${old.path}`);
    console.log(`   Looked for: ${new_.path}`);
    process.exit(1);
  }
  
  if (!old.exists) {
    console.log(`📝 No memory file for ${date1} (new session start?)`);
    console.log(`📄 ${date2} has ${getLines(new_.content).length} lines\n`);
    console.log(new_.content);
    process.exit(0);
  }
  
  if (!new_.exists) {
    console.log(`📝 No memory file for ${date2} yet`);
    console.log(`📄 ${date1} had ${getLines(old.content).length} lines`);
    process.exit(0);
  }
  
  const diff = diffMemory(old.content, new_.content);
  
  if (diff.added.length === 0 && diff.removed.length === 0) {
    console.log(`✨ No changes between ${date1} and ${date2}`);
    process.exit(0);
  }
  
  console.log(`📊 Summary:`);
  console.log(`   ${diff.added.length} lines added`);
  console.log(`   ${diff.removed.length} lines removed`);
  
  console.log(formatSection('➕ ADDED', diff.added, '+'));
  console.log(formatSection('➖ REMOVED', diff.removed, '-'));
}

main();
