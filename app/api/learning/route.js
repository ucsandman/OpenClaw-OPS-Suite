export const dynamic = 'force-dynamic';
export const revalidate = 0;

import { NextResponse } from 'next/server';
import { neon } from '@neondatabase/serverless';

// sql initialized inside handler for serverless compatibility

export async function GET() {
  try {
    const sql = neon(process.env.DATABASE_URL);
    // Get all decisions with their outcomes joined
    const decisions = await sql`
      SELECT d.*, 
             COALESCE(o.result, 'pending') as outcome,
             o.id as outcome_id
      FROM decisions d
      LEFT JOIN outcomes o ON o.decision_id = d.id
      ORDER BY d.timestamp DESC LIMIT 20
    `;

    // Get all lessons
    const lessons = await sql`SELECT * FROM lessons ORDER BY confidence DESC`;

    // Calculate stats
    const successCount = decisions.filter(d => d.outcome === 'success').length;
    const totalWithOutcome = decisions.filter(d => d.outcome && d.outcome !== 'pending').length;
    const successRate = totalWithOutcome > 0 ? Math.round((successCount / totalWithOutcome) * 100) : 0;

    const stats = {
      totalDecisions: decisions.length,
      totalLessons: lessons.length,
      successRate,
      patterns: lessons.filter(l => l.confidence >= 80).length
    };

    return NextResponse.json({
      decisions,
      lessons,
      stats,
      lastUpdated: new Date().toISOString()
    });
  } catch (error) {
    // SECURITY: Log detailed error server-side, return generic message to client
    console.error('Learning API error:', error);
    return NextResponse.json({ error: 'An error occurred while fetching learning data', decisions: [], lessons: [], stats: {} }, { status: 500 });
  }
}

