#!/usr/bin/env node
/**
 * session-to-memory - Extract significant moments from a conversation
 * 
 * Usage:
 *   node session-to-memory.js <transcript-file>    # Parse a transcript file
 *   node session-to-memory.js --stdin              # Read from stdin
 *   echo "conversation" | node session-to-memory.js --stdin
 * 
 * Outputs structured memory notes in markdown format.
 */

const fs = require('fs');
const path = require('path');

// Patterns that indicate significance
const PATTERNS = {
  decisions: [
    /\b(decided|decision|going to|will do|let's do|agreed|confirmed)\b/i,
    /\b(won't|not going to|rejected|declined)\b/i
  ],
  insights: [
    /\b(realized|learned|understood|insight|discovered|figured out)\b/i,
    /\b(the key is|important thing|main takeaway|lesson)\b/i,
    /\b(turns out|apparently|interesting(ly)?)\b/i
  ],
  emotions: [
    /\b(love|loved|amazing|awesome|excited|happy|proud)\b/i,
    /\b(frustrated|annoyed|worried|concerned|sad)\b/i,
    /\b(made me (smile|laugh|think|feel))\b/i,
    /\b(meaningful|significant|special)\b/i
  ],
  remember: [
    /\b(remember|don't forget|note to self|keep in mind)\b/i,
    /\b(important:|note:|reminder:)\b/i,
    /\b(for (future|later|next time))\b/i
  ],
  facts: [
    /\b(is called|named|located at|lives in|works at)\b/i,
    /\b(password|api key|credential|secret)\b/i,
    /\b(https?:\/\/\S+)\b/i,  // URLs
    /\b(\d{4}-\d{2}-\d{2})\b/,  // Dates
    /\b(phone|email|address):\s*\S+/i
  ],
  actions: [
    /\b(todo|to-do|action item|next step|follow up)\b/i,
    /\b(need to|should|must|have to)\b/i,
    /\b(schedule|book|set up|create|build|ship)\b/i
  ],
  milestones: [
    /\b(first time|finally|achieved|completed|shipped|launched)\b/i,
    /\b(milestone|breakthrough|success|win)\b/i,
    /\b(\d+)\s*(upvotes|followers|likes|views|impressions)\b/i
  ]
};

function extractSignificantLines(text) {
  const lines = text.split('\n');
  const significant = {
    decisions: [],
    insights: [],
    emotions: [],
    remember: [],
    facts: [],
    actions: [],
    milestones: []
  };
  
  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.length < 10) return;
    
    for (const [category, patterns] of Object.entries(PATTERNS)) {
      for (const pattern of patterns) {
        if (pattern.test(trimmed)) {
          // Get some context (previous line if available)
          const context = idx > 0 ? lines[idx - 1].trim() : '';
          significant[category].push({
            line: trimmed,
            context: context.length > 10 ? context : null
          });
          break;
        }
      }
    }
  });
  
  return significant;
}

function dedupeAndLimit(items, limit = 5) {
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const key = item.line.substring(0, 50);
    if (!seen.has(key)) {
      seen.add(key);
      result.push(item);
      if (result.length >= limit) break;
    }
  }
  return result;
}

function formatMemoryNote(significant, date = null) {
  const dateStr = date || new Date().toISOString().split('T')[0];
  let output = `# ${dateStr}\n\n`;
  
  // Milestones first
  if (significant.milestones.length > 0) {
    output += `## Milestones\n`;
    dedupeAndLimit(significant.milestones, 5).forEach(m => {
      output += `- ${cleanLine(m.line)}\n`;
    });
    output += '\n';
  }
  
  // Key decisions
  if (significant.decisions.length > 0) {
    output += `## Decisions Made\n`;
    dedupeAndLimit(significant.decisions, 5).forEach(d => {
      output += `- ${cleanLine(d.line)}\n`;
    });
    output += '\n';
  }
  
  // Insights
  if (significant.insights.length > 0) {
    output += `## Insights & Learnings\n`;
    dedupeAndLimit(significant.insights, 5).forEach(i => {
      output += `- ${cleanLine(i.line)}\n`;
    });
    output += '\n';
  }
  
  // Emotional beats
  if (significant.emotions.length > 0) {
    output += `## Meaningful Moments\n`;
    dedupeAndLimit(significant.emotions, 3).forEach(e => {
      output += `- ${cleanLine(e.line)}\n`;
    });
    output += '\n';
  }
  
  // Action items
  if (significant.actions.length > 0) {
    output += `## Action Items\n`;
    dedupeAndLimit(significant.actions, 5).forEach(a => {
      output += `- [ ] ${cleanLine(a.line)}\n`;
    });
    output += '\n';
  }
  
  // Facts to remember
  if (significant.facts.length > 0) {
    output += `## Facts & References\n`;
    dedupeAndLimit(significant.facts, 5).forEach(f => {
      output += `- ${cleanLine(f.line)}\n`;
    });
    output += '\n';
  }
  
  // Things explicitly marked to remember
  if (significant.remember.length > 0) {
    output += `## To Remember\n`;
    dedupeAndLimit(significant.remember, 5).forEach(r => {
      output += `- ${cleanLine(r.line)}\n`;
    });
    output += '\n';
  }
  
  return output;
}

function cleanLine(line) {
  // Remove timestamps, message prefixes, clean up
  return line
    .replace(/^\[.*?\]\s*/g, '')  // Remove [timestamp] prefixes
    .replace(/^(User|Assistant|Human|AI):\s*/i, '')  // Remove role prefixes
    .replace(/^\*+|\*+$/g, '')  // Remove surrounding asterisks
    .substring(0, 200);  // Limit length
}

function analyzeTranscript(text) {
  console.log('\n📝 Analyzing transcript...\n');
  
  const significant = extractSignificantLines(text);
  
  // Stats
  const total = Object.values(significant).reduce((sum, arr) => sum + arr.length, 0);
  console.log(`Found ${total} significant moments:\n`);
  for (const [cat, items] of Object.entries(significant)) {
    if (items.length > 0) {
      console.log(`  ${cat}: ${items.length}`);
    }
  }
  
  console.log('\n' + '─'.repeat(50) + '\n');
  
  const memoryNote = formatMemoryNote(significant);
  console.log(memoryNote);
  
  return memoryNote;
}

// CLI
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(`
session-to-memory - Extract significant moments from conversations

Usage:
  node session-to-memory.js <file>      Parse a transcript file
  node session-to-memory.js --stdin     Read from stdin
  
Options:
  --output <file>   Write output to file instead of stdout
  --date <date>     Use specific date in header (YYYY-MM-DD)
  `);
  process.exit(0);
}

if (args.includes('--stdin')) {
  let data = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => data += chunk);
  process.stdin.on('end', () => analyzeTranscript(data));
} else if (args[0] && fs.existsSync(args[0])) {
  const text = fs.readFileSync(args[0], 'utf-8');
  analyzeTranscript(text);
} else {
  console.log('Usage: node session-to-memory.js <transcript-file> or --stdin');
  console.log('       Run with --help for more options');
}
