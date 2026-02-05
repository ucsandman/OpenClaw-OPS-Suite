export const dynamic = 'force-dynamic';
export const revalidate = 0;

import { NextResponse } from 'next/server';
import { neon } from '@neondatabase/serverless';

// sql initialized inside handler for serverless compatibility

export async function GET() {
  try {
    const sql = neon(process.env.DATABASE_URL);
    // Get all content
    const content = await sql`SELECT * FROM content ORDER BY created_at DESC`;

    // Calculate stats by platform
    const byPlatform = {};
    content.forEach(c => {
      const platform = c.platform || 'other';
      if (!byPlatform[platform]) byPlatform[platform] = { count: 0, published: 0, draft: 0 };
      byPlatform[platform].count += 1;
      if (c.status === 'published') byPlatform[platform].published += 1;
      if (c.status === 'draft') byPlatform[platform].draft += 1;
    });

    const stats = {
      totalContent: content.length,
      published: content.filter(c => c.status === 'published').length,
      draft: content.filter(c => c.status === 'draft').length,
      byPlatform
    };

    return NextResponse.json({
      content,
      stats,
      lastUpdated: new Date().toISOString()
    });
  } catch (error) {
    // SECURITY: Log detailed error server-side, return generic message to client
    console.error('Content API error:', error);
    return NextResponse.json({ error: 'An error occurred while fetching content data', content: [], stats: {} }, { status: 500 });
  }
}

