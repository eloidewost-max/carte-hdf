import { createRemoteJWKSet, jwtVerify } from 'jose';

var ALLOWED_DOMAIN = 'vizzia.fr';

// Derive Clerk frontend API domain from the publishable key
function getClerkDomain(publishableKey) {
  var key = publishableKey.replace(/^pk_(test|live)_/, '');
  var decoded = atob(key);
  return decoded.replace(/\$$/, '');
}

export var config = {
  matcher: ['/((?!sign-in|favicon\\.ico|_vercel).*)'],
};

export default async function middleware(request) {
  var url = new URL(request.url);

  // Allow sign-in page through (with or without .html)
  if (url.pathname === '/sign-in' || url.pathname === '/sign-in.html') {
    return;
  }

  // Extract session token from Clerk cookie
  var cookieHeader = request.headers.get('cookie') || '';
  var match = cookieHeader.match(/__session=([^;]+)/);
  var token = match ? match[1] : null;

  if (!token) {
    return Response.redirect(new URL('/sign-in', request.url));
  }

  try {
    // Verify JWT against Clerk's JWKS (Edge-compatible via jose)
    var clerkDomain = getClerkDomain(process.env.CLERK_PUBLISHABLE_KEY);
    var JWKS = createRemoteJWKSet(new URL('https://' + clerkDomain + '/.well-known/jwks.json'));
    var result = await jwtVerify(token, JWKS);
    var payload = result.payload;

    // Check email from custom session claims (fast path, no API call)
    if (payload.email) {
      if (!payload.email.endsWith('@' + ALLOWED_DOMAIN)) {
        return accessDenied();
      }
      return; // authorized
    }

    // Fallback: fetch user from Clerk REST API to get email
    var userRes = await fetch('https://api.clerk.com/v1/users/' + payload.sub, {
      headers: { 'Authorization': 'Bearer ' + process.env.CLERK_SECRET_KEY }
    });

    if (!userRes.ok) {
      return Response.redirect(new URL('/sign-in', request.url));
    }

    var user = await userRes.json();
    var primaryEmail = (user.email_addresses || []).find(function(e) {
      return e.id === user.primary_email_address_id;
    });
    var email = primaryEmail ? primaryEmail.email_address : '';

    if (!email.endsWith('@' + ALLOWED_DOMAIN)) {
      return accessDenied();
    }

    return; // authorized
  } catch (err) {
    // Invalid or expired token
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
