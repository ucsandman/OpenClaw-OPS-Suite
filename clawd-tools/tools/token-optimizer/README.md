# Token Optimizer - Max 5x Efficiency System

**Goal:** Keep Wes under his Anthropic Max 5x weekly limits.

## Max 5x Limits
- **5-hour sessions**: ~225 messages
- **Weekly limit**: Resets 7 days after session starts
- **Problem**: Long contexts burn 5x more tokens due to context baggage

## Optimization Strategies

### 1. Model Selection (CRITICAL!)
- ✅ **Default to Sonnet** (we're already on Sonnet 4-5)
- 🚫 **Avoid Opus** unless absolutely necessary (complex reasoning only)
- 💡 **Use Haiku** for simple tasks (status checks, quick lookups)

### 2. Browser Automation
- 🔥 **Browser snapshots = 20k-50k tokens each**
- ✅ Use targeted actions instead of snapshots when possible
- ✅ Reuse existing tabs (don't open new ones)
- ✅ Use `maxChars` limit on snapshots
- ❌ Avoid full-page snapshots unless necessary

### 3. Context Management
- 🔄 **Start fresh chats every 15-20 messages**
- 📝 Summarize and archive long sessions
- 🗑️ Clear unnecessary context before continuing
- 📊 Use compact formats (bullets > paragraphs)

### 4. Conversation Hygiene
- ✂️ Keep prompts concise
- 🎯 One task per message when possible
- 📦 Batch similar tasks together
- 🚫 Avoid verbose responses unless needed

### 5. Heartbeat Efficiency
- ⏱️ 4-hour heartbeats (current setting)
- 🤫 Return HEARTBEAT_OK when nothing to report
- 📋 Batch checks together (don't run separately)

## Token Costs Reference

| Operation | Tokens | Notes |
|-----------|--------|-------|
| Browser snapshot (LinkedIn) | 50k | 🔥 AVOID |
| Browser snapshot (generic) | 20k | Use sparingly |
| Targeted browser action | 100-500 | ✅ Preferred |
| Web search | 500-1k | Reasonable |
| Web fetch | 2k-10k | Depends on page |
| Email check (gog) | 500-1k | Efficient |
| Calendar operations | 200-500 | Very cheap |
| Simple exec command | 100-200 | Minimal |
| Heartbeat check | 200-500 | Acceptable |

## Warning Thresholds
- **High usage session** (>50k tokens): Consider summarizing
- **Browser snapshot**: Always check if necessary first
- **Long conversation** (>15 messages): Suggest fresh start

## Daily Budget Estimates
- **Conservative**: 20k tokens/day = 140k/week (safe)
- **Moderate**: 30k tokens/day = 210k/week (borderline)
- **Heavy**: 40k+ tokens/day = likely to hit weekly limit

## Recovery Actions
If hitting limits:
1. Switch to Haiku for non-critical tasks
2. Reduce heartbeat frequency to 6h or 8h
3. Disable proactive checks temporarily
4. Archive long conversations and start fresh
5. Wait for weekly reset
