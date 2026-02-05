export const dynamic = 'force-dynamic';
export const revalidate = 0;

import { NextResponse } from 'next/server';
import { neon } from '@neondatabase/serverless';

// sql initialized inside handler for serverless compatibility

export async function GET() {
  try {
    const sql = neon(process.env.DATABASE_URL);
    // Get all workflows
    const workflows = await sql`SELECT * FROM workflows ORDER BY last_run DESC NULLS LAST`;

    // Get recent executions
    const executions = await sql`SELECT * FROM executions ORDER BY started_at DESC LIMIT 20`;

    // Get scheduled jobs
    const scheduledJobs = await sql`SELECT * FROM scheduled_jobs ORDER BY next_run ASC NULLS LAST`;

    // Calculate stats
    const enabled = workflows.filter(w => w.enabled === 1).length;
    const totalRuns = workflows.reduce((sum, w) => sum + (w.run_count || 0), 0);
    const recentSuccess = executions.filter(e => e.status === 'success').length;
    const recentFailed = executions.filter(e => e.status === 'failed').length;

    const stats = {
      totalWorkflows: workflows.length,
      enabled,
      totalRuns,
      recentExecutions: executions.length,
      recentSuccess,
      recentFailed,
      scheduledJobs: scheduledJobs.length
    };

    return NextResponse.json({
      workflows,
      executions,
      scheduledJobs,
      stats,
      lastUpdated: new Date().toISOString()
    });
  } catch (error) {
    // SECURITY: Log detailed error server-side, return generic message to client
    console.error('Workflows API error:', error);
    return NextResponse.json({ error: 'An error occurred while fetching workflow data', workflows: [], executions: [], scheduledJobs: [], stats: {} }, { status: 500 });
  }
}

