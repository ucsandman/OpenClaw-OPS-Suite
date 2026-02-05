export const dynamic = 'force-dynamic';
export const revalidate = 0;

import { NextResponse } from 'next/server';
import { neon } from '@neondatabase/serverless';

// sql initialized inside handler for serverless compatibility

export async function GET() {
  try {
    const sql = neon(process.env.DATABASE_URL);
    // Get upcoming calendar events from Neon
    // Note: DB stores EST times as naive timestamps, so we adjust for timezone
    // by subtracting 6 hours from NOW() to ensure we don't filter out future EST events
    const events = await sql`
      SELECT id, summary, start_time, end_time, location, description 
      FROM calendar_events 
      WHERE start_time >= NOW() - INTERVAL '6 hours'
      ORDER BY start_time 
      LIMIT 10
    `;
    
    // Add EST timezone offset to naive timestamps for proper client parsing
    const eventsWithTz = (events || []).map(event => ({
      ...event,
      // Timestamps from DB are in EST - append offset so JS parses correctly
      start_time: appendESTOffset(event.start_time),
      end_time: appendESTOffset(event.end_time),
    }));
    
    return NextResponse.json({
      events: eventsWithTz,
      lastUpdated: new Date().toISOString(),
      count: eventsWithTz.length
    });
  } catch (error) {
    console.error('Calendar API error:', error);
    return NextResponse.json({
      events: [],
      error: 'An error occurred while fetching calendar data',
      lastUpdated: new Date().toISOString()
    }, { status: 500 });
  }
}

function appendESTOffset(timestamp) {
  if (!timestamp) return null;
  
  // Handle Date objects - they come from DB as UTC but represent EST times
  // So we need to extract the UTC values and treat them as EST
  if (timestamp instanceof Date) {
    const year = timestamp.getUTCFullYear();
    const month = String(timestamp.getUTCMonth() + 1).padStart(2, '0');
    const day = String(timestamp.getUTCDate()).padStart(2, '0');
    const hours = String(timestamp.getUTCHours()).padStart(2, '0');
    const minutes = String(timestamp.getUTCMinutes()).padStart(2, '0');
    const seconds = String(timestamp.getUTCSeconds()).padStart(2, '0');
    // Return ISO string with EST offset (the UTC values ARE the EST values)
    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}-05:00`;
  }
  
  // Handle strings
  const str = String(timestamp);
  
  // If already has proper timezone offset at the end, return as-is
  if (str.match(/-\d{2}:\d{2}$/) || str.match(/\+\d{2}:\d{2}$/)) {
    return str;
  }
  
  // If has Z (UTC), it's wrong - the data is actually EST
  if (str.includes('Z')) {
    return str.replace('Z', '-05:00');
  }
  
  // If has GMT+0000 etc, convert to proper ISO format with EST offset
  if (str.includes('GMT')) {
    const date = new Date(str);
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    const seconds = String(date.getUTCSeconds()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}-05:00`;
  }
  
  // Naive datetime string - append EST offset
  return str + '-05:00';
}


