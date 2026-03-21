# Swaya Live/Test Split (Current State)

Last updated: 2026-03-09

## 1) Domains and Purpose
- `www.swaya.me` = live/beta for real users
- `test.swaya.me` = test/dev validation environment

## 2) Frontend Roots
- Live root: `/www/wwwroot/www.swaya.me`
- Test root: `/home/vinay/Swaya.me/frontend/dist`

## 3) Backend Services (Isolated)
### Live backend
- Service: `swayame-backend.service`
- Unit file: `/etc/systemd/system/swayame-backend.service`
- Working directory: `/www/wwwroot/swaya-live/backend`
- Port: `8000`
- Env file: `/www/wwwroot/swaya-live/backend/.env`
- DB: `swayame`

### Test backend
- Service: `swayame-backend-test.service`
- Unit file: `/etc/systemd/system/swayame-backend-test.service`
- Working directory: `/home/vinay/Swaya.me/backend`
- Port: `8001`
- Env file: `/home/vinay/Swaya.me/backend/.env`
- DB: `swayame_test`

## 4) Database Split
- Live DB: `swayame`
- Test DB: `swayame_test`
- `swayame_test` was created and initialized by cloning from `swayame` snapshot.

## 5) Nginx Routing
### Live vhost
- Config: `/www/server/panel/vhost/nginx/www.swaya.me.conf`
- `root /www/wwwroot/www.swaya.me;`
- API proxy: `proxy_pass http://127.0.0.1:8000/api/;`

### Test vhost
- Config: `/www/server/panel/vhost/nginx/test.swaya.me.conf`
- `root /home/vinay/Swaya.me/frontend/dist;`
- API proxy: `proxy_pass http://127.0.0.1:8001/api/;`

## 6) SSL
- `www.swaya.me` SSL already active.
- `test.swaya.me` SSL deployed with:
  - `/www/server/panel/vhost/cert/test.swaya.me/fullchain.pem`
  - `/www/server/panel/vhost/cert/test.swaya.me/privkey.pem`
- `test.swaya.me` now listens on `443` and redirects HTTP to HTTPS.

## 7) aaPanel Metadata
- aaPanel site records were corrected to show different roots:
  - `www.swaya.me` -> `/www/wwwroot/www.swaya.me`
  - `test.swaya.me` -> `/home/vinay/Swaya.me/frontend/dist`

## 8) Deploy Workflow
### For test.swaya.me
1. Build frontend from dev repo:
   - `npm --prefix /home/vinay/Swaya.me/frontend run build`
2. Restart test backend:
   - `sudo systemctl restart swayame-backend-test.service`
3. Reload nginx:
   - `sudo /www/server/nginx/sbin/nginx -s reload`

### For www.swaya.me
1. Build/copy live frontend bundle into live root:
   - Source: `/home/vinay/Swaya.me/frontend/dist/`
   - Target: `/www/wwwroot/www.swaya.me/`
2. If backend changes are needed for live, sync to live backend code path:
   - `/www/wwwroot/swaya-live/backend`
3. Restart live backend:
   - `sudo systemctl restart swayame-backend.service`
4. Reload nginx:
   - `sudo /www/server/nginx/sbin/nginx -s reload`

## 9) Health Checks
- Live backend health:
  - `curl -sS -H 'Host: www.swaya.me' http://127.0.0.1:8000/health`
- Test backend health:
  - `curl -sS -H 'Host: test.swaya.me' http://127.0.0.1:8001/health`
- Live site over HTTPS:
  - `curl -kI --resolve www.swaya.me:443:127.0.0.1 https://www.swaya.me/`
- Test site over HTTPS:
  - `curl -kI --resolve test.swaya.me:443:127.0.0.1 https://test.swaya.me/`

## 10) Important Notes
- Live and test now use different backend processes and different DBs.
- Changes in `/home/vinay/Swaya.me/backend` affect **test** only.
- Live backend is served from `/www/wwwroot/swaya-live/backend` and must be updated intentionally.
