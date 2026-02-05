export const dynamic = 'force-dynamic';
export const revalidate = 0;

import { NextResponse } from 'next/server';
import { neon } from '@neondatabase/serverless';

// sql initialized inside handler for serverless compatibility

export async function GET() {
  try {
    const sql = neon(process.env.DATABASE_URL);
    // Get all contacts
    const rawContacts = await sql`SELECT * FROM contacts ORDER BY last_contact DESC NULLS LAST`;

    // Get recent interactions with contact names
    const rawInteractions = await sql`
      SELECT i.*, c.name as contact_name 
      FROM interactions i 
      LEFT JOIN contacts c ON i.contact_id = c.id 
      ORDER BY i.date DESC LIMIT 50
    `;

    // Transform contacts to expected format (snake_case -> camelCase)
    const contacts = rawContacts.map(c => ({
      id: c.id,
      name: c.name,
      platform: c.platform || 'unknown',
      temperature: (c.temperature || 'warm').toUpperCase(),
      context: c.notes || c.opportunity_type || '',
      lastContact: c.last_contact,
      interactions: c.interaction_count || 0,
      followUpDate: c.next_followup
    }));

    // Transform interactions
    const interactions = rawInteractions.map(i => ({
      id: i.id,
      contactName: i.contact_name || 'Unknown',
      direction: i.direction || 'outbound',
      summary: i.summary || i.notes || '',
      type: i.type || 'message',
      platform: i.platform || 'unknown',
      date: i.date
    }));

    // Calculate stats
    const hot = contacts.filter(c => c.temperature === 'HOT').length;
    const warm = contacts.filter(c => c.temperature === 'WARM').length;
    const cold = contacts.filter(c => c.temperature === 'COLD').length;
    
    // Due follow-ups (including today and overdue)
    const today = new Date().toISOString().split('T')[0];
    const followUpsDue = contacts.filter(c => c.followUpDate && c.followUpDate <= today).length;

    const stats = {
      total: contacts.length,
      hot,
      warm,
      cold,
      followUpsDue
    };

    return NextResponse.json({
      contacts,
      interactions,
      stats,
      lastUpdated: new Date().toISOString()
    });
  } catch (error) {
    // SECURITY: Log detailed error server-side, return generic message to client
    console.error('Relationships API error:', error);
    return NextResponse.json({ error: 'An error occurred while fetching relationship data', contacts: [], interactions: [], stats: {} }, { status: 500 });
  }
}

