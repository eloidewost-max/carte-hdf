import { createRemoteJWKSet, jwtVerify } from 'jose';

const ALLOWED_DOMAIN = 'vizzia.fr';

// Derive Clerk frontend API domain from the publishable key (runs once at cold start)
function getClerkDomain(publishableKey) {
  const key = publishableKey.replace(/^pk_(test|live)_/, '');
  return atob(key).replace(/\$$/, '');
}

// Hoisted to module scope so JWKS cache persists across requests
const clerkDomain = getClerkDomain(process.env.CLERK_PUBLISHABLE_KEY);
const JWKS = createRemoteJWKSet(new URL('https://' + clerkDomain + '/.well-known/jwks.json'));

// Email cache: avoids re-fetching from Clerk API on every request (capped at 500 entries)
const emailCache = new Map();
const EMAIL_CACHE_MAX = 500;

export const config = {
  matcher: ['/((?!sign-in|favicon\\.ico|_vercel).*)'],
};

export default async function middleware(request) {
  const url = new URL(request.url);

  if (url.pathname === '/sign-in.html') {
    return;
  }

  // Extract session token from Clerk cookie
  const cookieHeader = request.headers.get('cookie') || '';
  const sessionCookie = cookieHeader.split('; ').find(function(c) { return c.startsWith('__session='); });
  const token = sessionCookie ? sessionCookie.slice('__session='.length) : null;

  if (!token) {
    return Response.redirect(new URL('/sign-in', request.url));
  }

  try {
    const result = await jwtVerify(token, JWKS);
    const payload = result.payload;

    // Fast path: email in custom session claims (no API call)
    if (payload.email) {
      if (!payload.email.endsWith('@' + ALLOWED_DOMAIN)) {
        return accessDenied();
      }
      return;
    }

    // Check cache before calling Clerk API
    if (emailCache.has(payload.sub)) {
      const cached = emailCache.get(payload.sub);
      if (!cached.endsWith('@' + ALLOWED_DOMAIN)) {
        return accessDenied();
      }
      return;
    }

    // Fallback: fetch user from Clerk REST API
    const userRes = await fetch('https://api.clerk.com/v1/users/' + payload.sub, {
      headers: { 'Authorization': 'Bearer ' + process.env.CLERK_SECRET_KEY }
    });

    if (!userRes.ok) {
      return Response.redirect(new URL('/sign-in', request.url));
    }

    const user = await userRes.json();
    const primaryEmail = (user.email_addresses || []).find(function(e) {
      return e.id === user.primary_email_address_id;
    });
    const email = primaryEmail ? primaryEmail.email_address : '';

    if (emailCache.size >= EMAIL_CACHE_MAX) emailCache.clear();
    emailCache.set(payload.sub, email);

    if (!email.endsWith('@' + ALLOWED_DOMAIN)) {
      return accessDenied();
    }

    return;
  } catch (err) {
    return Response.redirect(new URL('/sign-in', request.url));
  }
}

function accessDenied() {
  return new Response(
    '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Accès refusé</title>' +
    '<style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;' +
    'background:#0a0b10;color:#e2e4e9;display:flex;justify-content:center;align-items:center;' +
    'height:100vh;margin:0}div{text-align:center}h1{font-size:24px;margin-bottom:12px}' +
    'p{color:#8b8f98;margin-bottom:24px}a{color:#4ecdc4;text-decoration:none}a:hover{text-decoration:underline}</style>' +
    '</head><body><div><h1>Accès refusé</h1>' +
    '<p>Seules les adresses <strong>@vizzia.fr</strong> sont autorisées.</p>' +
    '<a href="/sign-in">Se reconnecter avec une autre adresse</a></div></body></html>',
    { status: 403, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}
