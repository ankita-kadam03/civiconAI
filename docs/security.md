# Security and privacy

- Passwords are bcrypt-hashed. JWT access tokens expire in minutes; refresh tokens last days.
- Role checks happen on the server. Citizens cannot assign themselves `OFFICER` or `ADMIN`.
- Internal notes, private attachments and exact addresses are omitted from public incident payloads.
- File uploads are type- and size-limited (images, 8 MB). Object names are random.
- Rate limits apply globally and more tightly on login, signup, classify and chat.
- Request bodies above 12 MB are rejected.
- Audit logs redact keys whose names look like secrets.
- AI prompts send title, short description and locality — not passwords, emails or phone numbers.

If a credential was shared outside the env files, rotate it:

1. Maps: restrict the browser key, or create a new key and update `VITE_GOOGLE_MAPS_API_KEY`.
2. Firebase web keys: add HTTP referrer restrictions; rotate the app if needed.
3. Demo password: change `DEMO_USER_PASSWORD` and reseed, or update user hashes.
4. `INTERNAL_TASK_SECRET` / `JWT_SECRET`: generate new values and restart the API.
