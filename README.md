# WNBase Hosting prototype

WNBase hosts member sites at `sites.wnbase.com/username/sitename/`. People join at `sites.wnbase.com` with Clerk, reserve a URL, upload a ZIP, and choose whether to list it publicly. The dashboard shows listed sites and published announcements. Staff can post announcements from the main site and manage moderation through Django Admin.

## Run on Windows PowerShell

```powershell
python -m pip install -r requirements.txt
$env:WNBASE_DEMO = "1"
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

For macOS or Linux, use `export WNBASE_DEMO=1` in place of the PowerShell environment command.

Open http://localhost:8000. Sign in from the header.

| Account | Username | Local demo password |
| --- | --- | --- |
| Member | `demo` | `wnbase-demo-local` |
| Admin | `admin` | `wnbase-admin-local` |

The sample site is at http://127.0.0.1:8000/demo/build-notes/. Open the control panel on `localhost` and published pages on `127.0.0.1` to exercise the same host separation used in deployment. Upload `examples/sample-site.zip` to test publishing to a new URL. Local demo credentials are only available after enabling demo mode and running the seed command.

## Publish a site

Put `index.html` at the top level of the ZIP and use relative paths such as `./style.css`. Each account can host three sites. ZIPs support standard web assets, audio, video, fonts, PDFs, and 3D models. CNAME and common repository tooling are skipped. ZIP contents are public after publishing. Uploaded CommonJS is served as a file and WNBase does not provide a Node runtime. Deployments support up to 500 files and 25 MiB of extracted content by default, and retain the three latest releases. An unlisted site is still accessible by its URL.

Pages run with an opaque browser origin. Browser JavaScript can post to an external API when that API supports the request, including CORS for the sandboxed origin when required. External form embeds depend on the provider's frame policy and whether the form works inside the sandbox. WNBase supplies static files and does not collect form submissions or run user backends.

## Deployment configuration

One Render web service can route both hostnames to this app. Add `sites.wnbase.com` as a custom domain in Render and point the Cloudflare `sites` CNAME to the service’s Render hostname. Configure a separate Clerk application for WNBase sign-in and set:

- `APP_ORIGIN` (optional) overrides the dashboard URL. Leave it unset to use `PUBLISH_ORIGIN`.
- `CONTENT_ORIGIN` (optional) serves uploaded files. Leave it unset on Render to use the service’s `RENDER_EXTERNAL_URL`. Keep that hostname enabled and distinct from the dashboard host.
- `PUBLISH_ORIGIN=https://sites.wnbase.com`
- `CLERK_ISSUER` to the Clerk Frontend API origin, including `https://`
- `CLERK_PUBLISHABLE_KEY` to that application's publishable key
- `DJANGO_SECRET_KEY` to a newly generated secret
- `DATABASE_URL` to a persistent Postgres connection string, using TLS against the hosted database
- Leave `WNBASE_DEMO` unset.
- Optional: `WNBASE_SITE_LIMIT_MIB` (default 25) and `WNBASE_SITE_FILE_LIMIT` (default 500). Adjust both to fit the database storage budget.

In Clerk, require usernames and customize the **session token** with this JSON claim:

```json
{"wnbase_username":"{{user.username}}"}
```

A new member's verified Clerk username becomes their published URL namespace. Their Clerk user ID stays linked to the account. A later Clerk rename keeps existing URLs stable.

Use the included `render.yaml` for a free Render web service. Supply the Clerk values and an external persistent Postgres connection string when prompted. Add the publishing domain to that service in Render.

Published files are stored in Postgres along with their deployment records. Use the database provider's persistent capacity to size a beta. The current limits are per account and there is no public registration quota. Keep registration limited to a beta cohort through Clerk until you have a global storage budget.

Build command:

```sh
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

Start command:

```sh
python manage.py migrate && gunicorn config.wsgi --bind "0.0.0.0:${PORT:-8000}"
```

After an admin signs in with Clerk, grant their account permissions using `python manage.py grant_clerk_staff user_...` with their Clerk user ID. They can then open **Announcements** and **Admin** in the site header. For full Django administration, use `python manage.py createsuperuser` and sign in directly at `/admin/`.

Live Clerk sign-in and domain routing need your Clerk app and DNS. The local demo can be run without either.
