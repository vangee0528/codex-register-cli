"""Local config editor UI served with the standard library."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ..config import get_config_path, init_default_settings, read_raw_config, write_raw_config


HTML_PAGE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>codex-console config</title>
  <style>
    :root { --bg:#f4efe5; --card:#fffaf0; --ink:#1f2a2e; --accent:#b85c38; --line:#d9cdbd; }
    body { margin:0; font-family:Georgia,serif; background:linear-gradient(135deg,#f4efe5,#e9dcc7); color:var(--ink); }
    .wrap { max-width:1100px; margin:0 auto; padding:24px; }
    h1 { margin:0 0 8px; font-size:34px; }
    p { margin:0 0 18px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:18px; box-shadow:0 12px 30px rgba(31,42,46,.08); }
    .card h2 { margin:0 0 14px; font-size:20px; }
    label { display:block; margin:10px 0 6px; font-size:14px; font-weight:700; }
    input, textarea, select { width:100%; box-sizing:border-box; border:1px solid var(--line); border-radius:12px; padding:10px 12px; font:inherit; background:#fff; }
    textarea { min-height:180px; resize:vertical; font-family:Consolas,monospace; font-size:13px; }
    .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
    .actions { display:flex; gap:12px; margin-top:18px; }
    button { border:0; border-radius:999px; padding:12px 18px; font:inherit; cursor:pointer; background:var(--accent); color:#fff; }
    button.secondary { background:#415a60; }
    #status { margin-top:14px; font-weight:700; }
    .mono { font-family:Consolas,monospace; font-size:13px; }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>Config Editor</h1>
    <p>Edit <span id=\"config-path\" class=\"mono\"></span> and save directly to <code>config.json</code>.</p>
    <div class=\"grid\">
      <section class=\"card\">
        <h2>General</h2>
        <label>database_url</label><input id=\"database_url\" />
        <label>log_level</label><input id=\"log_level\" />
        <label>log_file</label><input id=\"log_file\" />
        <label>registration_timeout</label><input id=\"registration_timeout\" type=\"number\" />
        <label>registration_max_retries</label><input id=\"registration_max_retries\" type=\"number\" />
      </section>
      <section class=\"card\">
        <h2>Static Proxy</h2>
        <label>proxy_enabled</label><select id=\"proxy_enabled\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <div class=\"row\">
          <div><label>proxy_type</label><input id=\"proxy_type\" /></div>
          <div><label>proxy_port</label><input id=\"proxy_port\" type=\"number\" /></div>
        </div>
        <label>proxy_host</label><input id=\"proxy_host\" />
        <label>proxy_username</label><input id=\"proxy_username\" />
        <label>proxy_password</label><input id=\"proxy_password\" type=\"password\" />
      </section>
      <section class=\"card\">
        <h2>Mail Defaults</h2>
        <label>tempmail_base_url</label><input id=\"tempmail_base_url\" />
        <div class=\"row\">
          <div><label>tempmail_timeout</label><input id=\"tempmail_timeout\" type=\"number\" /></div>
          <div><label>tempmail_max_retries</label><input id=\"tempmail_max_retries\" type=\"number\" /></div>
        </div>
        <label>custom_domain_base_url</label><input id=\"custom_domain_base_url\" />
        <label>custom_domain_api_key</label><input id=\"custom_domain_api_key\" type=\"password\" />
      </section>
      <section class=\"card\">
        <h2>CPA</h2>
        <label>cpa_enabled</label><select id=\"cpa_enabled\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <label>cpa_api_url</label><input id=\"cpa_api_url\" />
        <label>cpa_api_token</label><input id=\"cpa_api_token\" type=\"password\" />
      </section>
      <section class=\"card\">
        <h2>Proxy Pool</h2>
        <label>proxies</label>
        <textarea id=\"proxies\"></textarea>
      </section>
      <section class=\"card\">
        <h2>Email Services</h2>
        <label>email_services</label>
        <textarea id=\"email_services\"></textarea>
      </section>
      <section class=\"card\">
        <h2>CPA Services</h2>
        <label>cpa_services</label>
        <textarea id=\"cpa_services\"></textarea>
      </section>
    </div>
    <div class=\"actions\">
      <button id=\"save\">Save config.json</button>
      <button class=\"secondary\" id=\"reload\">Reload</button>
    </div>
    <div id=\"status\"></div>
  </div>
<script>
const fields = [
  'database_url','log_level','log_file','registration_timeout','registration_max_retries',
  'proxy_enabled','proxy_type','proxy_host','proxy_port','proxy_username','proxy_password',
  'tempmail_base_url','tempmail_timeout','tempmail_max_retries','custom_domain_base_url','custom_domain_api_key',
  'cpa_enabled','cpa_api_url','cpa_api_token'
];
const jsonFields = ['proxies','email_services','cpa_services'];

async function loadConfig() {
  const response = await fetch('/api/config');
  const payload = await response.json();
  document.getElementById('config-path').textContent = payload.path;
  const cfg = payload.config;
  for (const key of fields) {
    const node = document.getElementById(key);
    const value = cfg[key];
    node.value = value === undefined || value === null ? '' : String(value);
  }
  for (const key of jsonFields) {
    document.getElementById(key).value = JSON.stringify(cfg[key] || [], null, 2);
  }
  setStatus('Loaded config.json', false);
}

function setStatus(message, isError) {
  const node = document.getElementById('status');
  node.textContent = message;
  node.style.color = isError ? '#9f1d1d' : '#1f6a3f';
}

async function saveConfig() {
  try {
    const payload = {};
    for (const key of fields) {
      const node = document.getElementById(key);
      let value = node.value;
      if (key.endsWith('_enabled')) {
        value = value === 'true';
      } else if (['registration_timeout','registration_max_retries','proxy_port','tempmail_timeout','tempmail_max_retries'].includes(key)) {
        value = value === '' ? 0 : Number(value);
      }
      payload[key] = value;
    }
    for (const key of jsonFields) {
      payload[key] = JSON.parse(document.getElementById(key).value || '[]');
    }
    const response = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || 'save failed');
    }
    setStatus('Saved config.json', false);
  } catch (error) {
    setStatus(error.message, true);
  }
}

document.getElementById('save').addEventListener('click', saveConfig);
document.getElementById('reload').addEventListener('click', loadConfig);
loadConfig();
</script>
</body>
</html>"""


def run_config_ui(host: str, port: int) -> None:
    init_default_settings()

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/":
                body = HTML_PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/api/config":
                self._send_json({
                    "path": str(get_config_path()),
                    "config": read_raw_config(),
                })
                return

            self._send_json({"error": "not found"}, status_code=404)

        def do_POST(self) -> None:
            if self.path != "/api/config":
                self._send_json({"error": "not found"}, status_code=404)
                return

            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode("utf-8"))
                write_raw_config(payload)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status_code=400)
                return

            self._send_json({"ok": True, "path": str(get_config_path())})

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Config UI running at http://{host}:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
