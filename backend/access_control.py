"""Local administrator access: file-backed key, signed sessions and CSRF checks."""
from runtime_paths import CONFIG_DIR
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import time
from fastapi import Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

KEY_PATH = Path(os.environ.get('FAMILY_ACCESS_KEY_PATH', str(CONFIG_DIR / 'dashboard-access.key')))
COOKIE = 'family_session'

def access_key():
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, 'w') as f: f.write(secrets.token_urlsafe(48))
    return KEY_PATH.read_text().strip()

def signature(value):
    return hmac.new(access_key().encode(), value.encode(), hashlib.sha256).hexdigest()

def valid_session(value):
    try:
        expires, nonce, digest = value.split('.')
        return int(expires) > time.time() and hmac.compare_digest(digest, signature(expires+'.'+nonce))
    except (ValueError, AttributeError): return False

def local_origin(request):
    # Reject DNS rebinding and browser requests from unrelated sites.
    return request.headers.get('origin') in {None, 'http://localhost:8000', 'http://127.0.0.1:8000'} and request.headers.get('sec-fetch-site') not in {'cross-site','same-site'}

def install_access(app):
    @app.middleware('http')
    async def guard(request: Request, call_next):
        path = request.url.path
        if request.headers.get('host','') not in {'localhost:8000','127.0.0.1:8000','testserver','family-agent-api:8000'}:
            return JSONResponse({'detail':'Unrecognized host'}, status_code=400)
        public = path in {'/health','/auth/login'} or path.startswith('/static/')
        bearer = request.headers.get('authorization','')
        token_ok = hmac.compare_digest(bearer, 'Bearer '+access_key())
        # Existing remote bridge credentials are limited to delivery routes.
        if not token_ok and (path in {'/messaging/inbox','/alerts/claim','/alerts/calendar/sync','/alerts/morning/sync'} or (path.startswith('/alerts/') and path.rsplit('/',1)[-1] in {'sent','failed','uncertain'})):
            from messaging_settings import load_settings
            cfg=load_settings()
            token_ok=cfg['provider']!='imessage' and bool(cfg.get('bridge_token')) and hmac.compare_digest(bearer,'Bearer '+cfg['bridge_token'])
        session_ok=valid_session(request.cookies.get(COOKIE,''))
        if not public and not token_ok and not session_ok:
            if path in {'/','/dashboard'}: return RedirectResponse('/auth/login')
            return JSONResponse({'detail':'Sign in to Family Agent first.'},status_code=401)
        if not token_ok and not local_origin(request):
            return JSONResponse({'detail':'Cross-site request rejected'},status_code=403)
        if not public and session_ok and not token_ok and request.method not in {'GET','HEAD','OPTIONS'} and request.headers.get('x-family-request')!='dashboard':
            return JSONResponse({'detail':'Missing browser request protection'},status_code=403)
        response=await call_next(request)
        if not path.startswith('/static/'): response.headers['Cache-Control']='no-store'
        response.headers['X-Frame-Options']='DENY'
        return response

    @app.get('/auth/login',response_class=HTMLResponse)
    def login_page():
        return '''<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Family Agent sign in</title><style>body{font:17px -apple-system,sans-serif;background:#f5f5f7;color:#1d1d1f;max-width:420px;margin:12vh auto;padding:24px}input,button{box-sizing:border-box;width:100%;padding:14px;margin:12px 0;border:1px solid #ccc;border-radius:10px;font:inherit}button{background:#0066cc;color:white}p{line-height:1.5}</style><h1>Welcome home.</h1><p>Open <strong>open-dashboard.command</strong> in your Family Agent folder to sign in privately on this Mac, or enter your local access key.</p><form><label>Access key<input type="password" autocomplete="current-password" required></label><button>Sign in</button></form><p id="status" role="status"></p><script>const form=document.querySelector('form');async function login(key){const r=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});if(r.ok)location.replace('/dashboard#concierge/tomorrow');else document.querySelector('#status').textContent='Sign-in failed. Check your local access key.';}form.onsubmit=e=>{e.preventDefault();login(form.querySelector('input').value)};const key=new URLSearchParams(location.hash.slice(1)).get('access');history.replaceState(null,'',location.pathname);if(key)login(key);</script></html>'''

    @app.post('/auth/login')
    async def login(request:Request):
        if not local_origin(request): return JSONResponse({'detail':'Invalid origin'},status_code=403)
        try: data=await request.json()
        except ValueError: return JSONResponse({'detail':'Invalid request'},status_code=400)
        if not isinstance(data,dict) or not isinstance(data.get('key'),str) or not hmac.compare_digest(data['key'],access_key()):
            return JSONResponse({'detail':'Invalid access key'},status_code=401)
        value=str(int(time.time()+86400*7))+'.'+secrets.token_hex(16)
        response=JSONResponse({'status':'signed_in'})
        response.set_cookie(COOKIE,value+'.'+signature(value),httponly=True,samesite='strict',max_age=86400*7,path='/')
        return response
