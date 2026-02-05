export const dynamic = 'force-dynamic';
export const revalidate = 0;

import { NextResponse } from 'next/server';
import { neon } from '@neondatabase/serverless';

// sql initialized inside handler for serverless compatibility

export async function GET() {
  try {
    const sql = neon(process.env.DATABASE_URL);
    // Get all goals
    const goals = await sql`SELECT * FROM goals ORDER BY created_at DESC`;

    // Get milestones for each goal
    const milestones = await sql`SELECT * FROM milestones ORDER BY created_at DESC`;

    // Attach milestones to goals
    const goalsWithMilestones = goals.map(g => ({
      ...g,
      milestones: milestones.filter(m => m.goal_id === g.id)
    }));

    // Calculate stats
    const active = goals.filter(g => g.status === 'active').length;
    const completed = goals.filter(g => g.status === 'completed').length;
    const avgProgress = goals.length > 0 
      ? Math.round(goals.reduce((sum, g) => sum + (g.progress || 0), 0) / goals.length)
      : 0;

    const stats = {
      totalGoals: goals.length,
      active,
      completed,
      avgProgress,
      totalMilestones: milestones.length,
      completedMilestones: milestones.filter(m => m.status === 'completed').length
    };

    return NextResponse.json({
      goals: goalsWithMilestones,
      stats,
      lastUpdated: new Date().toISOString()
    });
  } catch (error) {
    // SECURITY: Log detailed error server-side, return generic message to client
    console.error('Goals API error:', error);
    return NextResponse.json({ error: 'An error occurred while fetching goals data', goals: [], stats: {} }, { status: 500 });
  }
}

