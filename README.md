# ShotSpot

ShotSpot stores public profiles and geotagged photographs in Supabase. The Flask
backend uses the Supabase service-role key only on the server; clients authenticate
with a Supabase access token and send it as `Authorization: Bearer <token>`.

## Supabase setup

1. Create a Supabase project and enable the authentication providers needed by the frontend.
2. Run [`migrations/001_initial_schema.sql`](./migrations/001_initial_schema.sql) in Supabase SQL Editor.
3. Create a public Storage bucket named `photos`, with a 10 MB limit and MIME types
   `image/jpeg`, `image/png`, and `image/webp`. The migration includes matching
   object policies.
4. Keep the service-role key private. It is only used by Flask and must never be
   sent to browser code.
5. After signup, create a row in `profiles` using the authenticated user's ID.
   Usernames must contain 3-30 letters, numbers, or underscores.

## Local setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`, then run:

```powershell
flask --app app run --debug
```

Do not commit `.env`. Run tests with `pytest`.

## API examples

List posts with pagination:

```text
GET /api/posts?page=1&per_page=20
```

Create a post:

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/posts `
  -H "Authorization: Bearer SUPABASE_ACCESS_TOKEN" `
  -F "image=@C:\photos\lake.jpg" `
  -F "caption=Morning light" `
  -F "place_name=Lake Balaton" `
  -F "latitude=46.8300" `
  -F "longitude=17.7340"
```

Other endpoints are `GET /api/posts/<post_id>`, `DELETE /api/posts/<post_id>`,
`GET /api/users/<user_id>`, and `GET /api/users/<user_id>/posts?page=1&per_page=20`.
Delete requires the post owner's token and returns `204` on success.

Successful creation returns `201` with the created post:

```json
{
  "id": "post-uuid",
  "user_id": "auth-user-uuid",
  "image_url": "auth-user-uuid/file-uuid.jpg",
  "caption": "Morning light",
  "place_name": "Lake Balaton",
  "latitude": 46.83,
  "longitude": 17.734,
  "instagram_url": null,
  "created_at": "2026-10-17T12:00:00+00:00"
}
```
