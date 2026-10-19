# Security and privacy

- Passwords are bcrypt-hashed. JWT access tokens expire in minutes; refresh tokens last days.
- Role checks happen on the server. Citizens cannot assign themselves `OFFICER` or `ADMIN`.
- Every issue and its location are public. Signed-out visitors see the issue, location, and promote count; signed-in users also see status, brief summary, assigned officer name, municipality, non-private attachments, and conversations.
- AI summaries/classifications, image inference, contact phone numbers, and private attachments are restricted to the reporter and authorized officials (department officers and administrators). The attachment privacy option hides an image from other users, but not from its reporter or authorized officials.
- File uploads are type- and size-limited (images, 8 MB). Object names are random.
- Rate limits apply globally and more tightly on login, signup, classify, and chat.
- Requests are limited to 12 MB except report-image multipart submissions and image classification, which allow up to 34 MB to accommodate four images of up to 8 MB each.
- Audit logs redact keys whose names look like secrets.
- Gemini receives the report title, description, locality, and attached images for classification and image inference — not passwords, emails, or phone numbers. Marking an image private restricts image retrieval by other users; it does not exclude it from Gemini analysis.

If a credential was shared outside env files, rotate it:

1. **Maps:** restrict or replace the browser key; update `VITE_GOOGLE_MAPS_API_KEY`.
2. **Firebase web config:** add HTTP referrer restrictions; rotate if needed.
3. **Bootstrap users:** change `SEED_BOOTSTRAP_PASSWORD` and reseed, or update password hashes in Firestore.
4. **`JWT_SECRET` / `INTERNAL_TASK_SECRET`:** new values in Secret Manager (production) or `backend/.env` (local); restart API; users re-login after JWT secret rotation.
