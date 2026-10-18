# Security and privacy

- Passwords are bcrypt-hashed. JWT access tokens expire in minutes; refresh tokens last days.
- Role checks happen on the server. Citizens cannot assign themselves `OFFICER` or `ADMIN`.
- Internal notes, private attachments, and exact addresses are omitted from public incident payloads.
- File uploads are type- and size-limited (images, 8 MB). Object names are random.
- Rate limits apply globally and more tightly on login, signup, classify, and chat.
- Request bodies above 12 MB are rejected.
- Audit logs redact keys whose names look like secrets.
- AI prompts send title, short description, and locality — not passwords, emails, or phone numbers.

If a credential was shared outside env files, rotate it:

1. **Maps:** restrict or replace the browser key; update `VITE_GOOGLE_MAPS_API_KEY`.
2. **Firebase web config:** add HTTP referrer restrictions; rotate if needed.
3. **Bootstrap users:** change `SEED_BOOTSTRAP_PASSWORD` and reseed, or update password hashes in Firestore.
4. **`JWT_SECRET` / `INTERNAL_TASK_SECRET`:** new values in Secret Manager (production) or `backend/.env` (local); restart API; users re-login after JWT secret rotation.
