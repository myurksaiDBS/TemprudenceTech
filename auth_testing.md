# Auth testing
- Login: POST /api/auth/login {"email":"admin@temprudence.com","password":"Temprudence2026!"} -> {user, token} + httpOnly cookies
- Use `Authorization: Bearer <token>` or cookies for all /api calls
- GET /api/auth/me returns user (no password_hash)
- Brute force: 5 failed attempts per ip+email -> 429 for 15 minutes
- Users have uuid `id` field; bcrypt hash in password_hash ($2b$)
- Roles: admin (manage users, keys, delete computers) / technician (scan, view, export)
