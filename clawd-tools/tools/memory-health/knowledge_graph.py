#!/usr/bin/env python3
"""
Knowledge Graph Extractor
Extracts entities, topics, and relationships from memory files.
"""

import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

DB_PATH = Path(__file__).parent / "data" / "memory_health.db"
MEMORY_DIR = Path(__file__).parent.parent.parent / "memory"
MEMORY_MD = Path(__file__).parent.parent.parent / "MEMORY.md"

def init_db():
    """Initialize knowledge graph tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            mention_count INTEGER DEFAULT 1,
            first_seen TEXT,
            last_seen TEXT,
            context TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            mention_count INTEGER DEFAULT 1,
            related_entities TEXT,
            keywords TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity1 TEXT NOT NULL,
            entity2 TEXT NOT NULL,
            relationship_type TEXT,
            strength INTEGER DEFAULT 1,
            context TEXT
        )
    ''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_topics_name ON topics(name)')
    
    conn.commit()
    conn.close()

def extract_entities(text, source_file):
    """Extract named entities from text."""
    entities = []
    
    # People patterns (names with @, capitalized names)
    people = re.findall(r'@(\w+)', text)
    for person in people:
        entities.append({'name': person, 'type': 'person', 'source': source_file})
    
    # Also find capitalized names that look like people
    name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
    potential_names = re.findall(name_pattern, text)
    # Filter out common words
    skip_words = {'The', 'This', 'That', 'These', 'When', 'What', 'Where', 'How', 'Why',
                  'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
                  'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                  'September', 'October', 'November', 'December', 'Today', 'Tomorrow', 'Yesterday'}
    for name in potential_names:
        if name not in skip_words and len(name) > 2:
            entities.append({'name': name, 'type': 'person', 'source': source_file})
    
    # Tools/Projects (capitalized or specific patterns)
    tool_patterns = [
        r'\b(Clawdbot|MoltFire|Moltbook|Telegram|Discord|GitHub|Vercel|Neon|Notion)\b',
        r'\b([A-Z][a-zA-Z]+(?:Bot|API|CLI|DB|Tool))\b',
    ]
    for pattern in tool_patterns:
        tools = re.findall(pattern, text)
        for tool in tools:
            entities.append({'name': tool, 'type': 'tool', 'source': source_file})
    
    # URLs/Services
    urls = re.findall(r'https?://([a-zA-Z0-9.-]+)', text)
    for url in urls:
        entities.append({'name': url, 'type': 'service', 'source': source_file})
    
    # File paths
    paths = re.findall(r'[`"]([a-zA-Z0-9_/-]+\.[a-z]+)[`"]', text)
    for path in paths:
        entities.append({'name': path, 'type': 'file', 'source': source_file})
    
    return entities

def extract_topics(text):
    """Extract topic keywords from text."""
    # Common AI/tech topics
    topic_patterns = {
        'ai': r'\b(AI|artificial intelligence|machine learning|ML|LLM|GPT|Claude)\b',
        'automation': r'\b(automat|workflow|cron|schedule|heartbeat)\b',
        'security': r'\b(security|auth|password|token|secret|credential)\b',
        'memory': r'\b(memory|context|recall|remember|forget)\b',
        'dashboard': r'\b(dashboard|chart|graph|visualiz|display)\b',
        'communication': r'\b(email|message|chat|telegram|discord|slack)\b',
        'development': r'\b(code|develop|build|deploy|git|commit)\b',
        'data': r'\b(data|database|SQL|postgres|sqlite|neon)\b',
        'income': r'\b(income|money|earn|revenue|client|customer|bounty)\b',
        'personal': r'\b(Wes|personal|preference|like|prefer|hate)\b',
    }
    
    topics = []
    text_lower = text.lower()
    
    for topic, pattern in topic_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            topics.append(topic)
    
    return topics

def extract_relationships(text, entities):
    """Find relationships between entities mentioned together."""
    relationships = []
    
    # Group entities by sentence/paragraph
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        para_entities = []
        for e in entities:
            if e['name'].lower() in para.lower():
                para_entities.append(e['name'])
        
        # Create relationships between entities in same paragraph
        for i, e1 in enumerate(para_entities):
            for e2 in para_entities[i+1:]:
                if e1 != e2:
                    relationships.append({
                        'entity1': e1,
                        'entity2': e2,
                        'context': para[:100]
                    })
    
    return relationships

def build_graph():
    """Build the knowledge graph from all memory files."""
    init_db()
    
    all_entities = []
    all_topics = []
    all_relationships = []
    
    # Process MEMORY.md
    if MEMORY_MD.exists():
        content = MEMORY_MD.read_text(encoding='utf-8', errors='ignore')
        entities = extract_entities(content, 'MEMORY.md')
        topics = extract_topics(content)
        relationships = extract_relationships(content, entities)
        
        all_entities.extend(entities)
        all_topics.extend(topics)
        all_relationships.extend(relationships)
    
    # Process daily files
    if MEMORY_DIR.exists():
        for f in sorted(MEMORY_DIR.glob('*.md')):
            if f.name.startswith('20'):
                content = f.read_text(encoding='utf-8', errors='ignore')
                entities = extract_entities(content, f.name)
                topics = extract_topics(content)
                relationships = extract_relationships(content, entities)
                
                all_entities.extend(entities)
                all_topics.extend(topics)
                all_relationships.extend(relationships)
    
    # Aggregate and store
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Clear old data
    c.execute('DELETE FROM entities')
    c.execute('DELETE FROM topics')
    c.execute('DELETE FROM relationships')
    
    # Store entities
    entity_counts = Counter((e['name'], e['type']) for e in all_entities)
    for (name, etype), count in entity_counts.most_common():
        sources = [e['source'] for e in all_entities if e['name'] == name]
        c.execute('''
            INSERT INTO entities (name, type, mention_count, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, etype, count, min(sources), max(sources)))
    
    # Store topics
    topic_counts = Counter(all_topics)
    for topic, count in topic_counts.most_common():
        c.execute('''
            INSERT OR REPLACE INTO topics (name, mention_count)
            VALUES (?, ?)
        ''', (topic, count))
    
    # Store relationships
    rel_counts = Counter((r['entity1'], r['entity2']) for r in all_relationships)
    for (e1, e2), strength in rel_counts.most_common(50):  # Top 50 relationships
        c.execute('''
            INSERT INTO relationships (entity1, entity2, strength)
            VALUES (?, ?, ?)
        ''', (e1, e2, strength))
    
    conn.commit()
    conn.close()
    
    return {
        'entities': len(entity_counts),
        'topics': len(topic_counts),
        'relationships': len(rel_counts)
    }

def get_graph_data():
    """Get knowledge graph data for visualization."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get top entities
    c.execute('SELECT name, type, mention_count FROM entities ORDER BY mention_count DESC LIMIT 30')
    entities = [{'name': r[0], 'type': r[1], 'mentions': r[2]} for r in c.fetchall()]
    
    # Get topics
    c.execute('SELECT name, mention_count FROM topics ORDER BY mention_count DESC')
    topics = [{'name': r[0], 'mentions': r[1]} for r in c.fetchall()]
    
    # Get relationships
    c.execute('SELECT entity1, entity2, strength FROM relationships ORDER BY strength DESC LIMIT 50')
    relationships = [{'source': r[0], 'target': r[1], 'strength': r[2]} for r in c.fetchall()]
    
    conn.close()
    
    return {
        'entities': entities,
        'topics': topics,
        'relationships': relationships
    }

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: knowledge_graph.py <command>")
        print("Commands:")
        print("  build    - Build knowledge graph from memory files")
        print("  entities - List top entities")
        print("  topics   - List topics")
        print("  json     - Output graph data as JSON")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'build':
        result = build_graph()
        print(f"Knowledge graph built:")
        print(f"  Entities: {result['entities']}")
        print(f"  Topics: {result['topics']}")
        print(f"  Relationships: {result['relationships']}")
    
    elif cmd == 'entities':
        init_db()
        data = get_graph_data()
        print("Top Entities:")
        for e in data['entities'][:20]:
            print(f"  [{e['type']}] {e['name']}: {e['mentions']} mentions")
    
    elif cmd == 'topics':
        init_db()
        data = get_graph_data()
        print("Topics:")
        for t in data['topics']:
            print(f"  {t['name']}: {t['mentions']} mentions")
    
    elif cmd == 'json':
        init_db()
        data = get_graph_data()
        print(json.dumps(data))
    
    else:
        print(f"Unknown command: {cmd}")

if __name__ == '__main__':
    main()
