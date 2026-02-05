import { NextResponse } from 'next/server';

/**
 * Authentication middleware for OpenClaw Dashboard
 *
 * SECURITY: Protects API routes with API key authentication
 * Set DASHBOARD_API_KEY environment variable in production
 */

// Routes that require authentication
const PROTECTED_ROUTES = [
  '/api/settings',
  '/api/tokens',
  '/api/relationships',
  '/api/goals',
  '/api/learning',
  '/api/workflows',
  '/api/inspiration',
  '/api/bounties',
  '/api/content',
  '/api/schedules',
  '/api/calendar',
  '/api/memory',
];

// Routes that are always public (health checks, setup)
const PUBLIC_ROUTES = [
  '/api/health',
  '/api/setup/status',
];

// Simple in-memory rate limiting (resets on deploy)
const rateLimitMap = new Map();
const RATE_LIMIT_WINDOW = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX = 100; // requests per window

function checkRateLimit(ip) {
  const now = Date.now();
  const record = rateLimitMap.get(ip);
  
  if (!record || now - record.timestamp > RATE_LIMIT_WINDOW) {
    rateLimitMap.set(ip, { timestamp: now, count: 1 });
    return true;
  }
  
  if (record.count >= RATE_LIMIT_MAX) {
    return false;
  }
  
  record.count++;
  return true;
}

export function middleware(request) {
  const { pathname } = request.nextUrl;
  
  // Skip non-API routes
  if (!pathname.startsWith('/api/')) {
    return NextResponse.next();
  }
  
  // Allow public routes without auth
  if (PUBLIC_ROUTES.some(route => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check if this is a protected API route
  const isProtectedRoute = PROTECTED_ROUTES.some(route => pathname.startsWith(route));

  // Get client IP for rate limiting
  const ip = request.headers.get('x-forwarded-for')?.split(',')[0] || 
             request.headers.get('x-real-ip') || 
             'unknown';

  // Apply rate limiting to all API routes
  if (!checkRateLimit(ip)) {
    console.warn(`[SECURITY] Rate limit exceeded for ${ip}: ${pathname}`);
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please slow down.' },
      { status: 429, headers: { 'Retry-After': '60' } }
    );
  }

  if (isProtectedRoute) {
    // Get API key from header or query param
    const apiKey = request.headers.get('x-api-key') ||
                   request.nextUrl.searchParams.get('api_key');

    // Get expected API key from environment
    const expectedKey = process.env.DASHBOARD_API_KEY;

    // If no API key is configured, allow access (but log warning)
    // For personal dashboards, this is acceptable. For production, set DASHBOARD_API_KEY
    if (!expectedKey) {
      console.log(`[INFO] DASHBOARD_API_KEY not set - allowing unauthenticated access to: ${pathname}`);
      return NextResponse.next();
    }

    // Validate API key
    if (apiKey !== expectedKey) {
      console.warn(`[SECURITY] Unauthorized API access attempt: ${pathname} from ${ip}`);
      return NextResponse.json(
        { error: 'Unauthorized - Invalid or missing API key' },
        { status: 401 }
      );
    }
  }

  // Add security headers
  const response = NextResponse.next();
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');

  return response;
}

export const config = {
  matcher: '/api/:path*',
};
