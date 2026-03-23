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
    :root { --bg:#f1efe8; --card:#fffdf8; --ink:#1f2933; --accent:#9e3d22; --line:#ddd3c3; --muted:#66727f; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Georgia,serif; background:radial-gradient(circle at top,#f9f4ea,#ebe1cf 55%,#e1d4bf); color:var(--ink); }
    .wrap { max-width:1280px; margin:0 auto; padding:24px; }
    h1 { margin:0 0 8px; font-size:34px; }
    p { margin:0 0 18px; color:var(--muted); }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:18px; box-shadow:0 14px 34px rgba(31,41,51,.08); }
    .card h2 { margin:0 0 12px; font-size:20px; }
    label { display:block; margin:10px 0 6px; font-size:14px; font-weight:700; }
    input, textarea, select { width:100%; border:1px solid var(--line); border-radius:12px; padding:10px 12px; font:inherit; background:#fff; }
    textarea { min-height:180px; resize:vertical; font-family:Consolas,monospace; font-size:13px; }
    .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
    .actions { display:flex; gap:12px; margin-top:18px; flex-wrap:wrap; }
    button { border:0; border-radius:999px; padding:12px 18px; font:inherit; cursor:pointer; background:var(--accent); color:#fff; }
    button.secondary { background:#415a60; }
    #status { margin-top:14px; font-weight:700; }
    .mono { font-family:Consolas,monospace; font-size:13px; }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>Config Editor</h1>
    <p>Edit <span id=\"config-path\" class=\"mono\"></span>. Daily usage should mostly rely on these defaults.</p>
    <div class=\"grid\">
      <section class=\"card\">
        <h2>General</h2>
        <label>database_url</label><input id=\"database_url\" />
        <div class=\"row\">
          <div><label>log_level</label><input id=\"log_level\" /></div>
          <div><label>log_file</label><input id=\"log_file\" /></div>
        </div>
        <label>config_ui_host</label><input id=\"config_ui_host\" />
        <label>config_ui_port</label><input id=\"config_ui_port\" type=\"number\" />
      </section>
      <section class=\"card\">
        <h2>Workflow Defaults</h2>
        <div class=\"row\">
          <div><label>workflow.target_account_count</label><input id=\"workflow.target_account_count\" type=\"number\" /></div>
          <div><label>workflow.max_registration_attempts</label><input id=\"workflow.max_registration_attempts\" type=\"number\" /></div>
        </div>
        <label>workflow.refresh_before_validate</label><select id=\"workflow.refresh_before_validate\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <label>workflow.auto_delete_invalid</label><select id=\"workflow.auto_delete_invalid\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <label>workflow.auto_sync_cpa</label><select id=\"workflow.auto_sync_cpa\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
      </section>
      <section class=\"card\">
        <h2>Default Resources</h2>
        <div class=\"row\">
          <div><label>defaults.email_service_type</label><input id=\"defaults.email_service_type\" /></div>
          <div><label>registration.default_count</label><input id=\"registration.default_count\" type=\"number\" /></div>
        </div>
        <div class=\"row\">
          <div><label>defaults.email_service_id</label><input id=\"defaults.email_service_id\" type=\"number\" /></div>
          <div><label>defaults.proxy_id</label><input id=\"defaults.proxy_id\" type=\"number\" /></div>
        </div>
        <div class=\"row\">
          <div><label>defaults.cpa_service_id</label><input id=\"defaults.cpa_service_id\" type=\"number\" /></div>
          <div><label>registration.auto_upload_cpa</label><select id=\"registration.auto_upload_cpa\"><option value=\"true\">true</option><option value=\"false\">false</option></select></div>
        </div>
        <label>registration.save_to_database</label><select id=\"registration.save_to_database\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <label>registration.service_config</label><textarea id=\"registration.service_config\"></textarea>
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
        <h2>Proxy Policy</h2>
        <label>proxy_policy.registration</label><select id=\"proxy_policy.registration\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <label>proxy_policy.account_validate</label><select id=\"proxy_policy.account_validate\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <label>proxy_policy.token_refresh</label><select id=\"proxy_policy.token_refresh\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <label>proxy_policy.cpa_upload</label><select id=\"proxy_policy.cpa_upload\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <label>proxy_policy.cpa_test</label><select id=\"proxy_policy.cpa_test\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
      </section>
      <section class=\"card\">
        <h2>Dynamic Proxy</h2>
        <label>proxy_dynamic.enabled</label><select id=\"proxy_dynamic.enabled\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
        <label>proxy_dynamic.api_url</label><input id=\"proxy_dynamic.api_url\" />
        <label>proxy_dynamic.api_key</label><input id=\"proxy_dynamic.api_key\" type=\"password\" />
        <label>proxy_dynamic.api_key_header</label><input id=\"proxy_dynamic.api_key_header\" />
        <label>proxy_dynamic.result_field</label><input id=\"proxy_dynamic.result_field\" />
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
const fieldDefs = [
  { id: 'database_url', type: 'string' },
  { id: 'log_level', type: 'string' },
  { id: 'log_file', type: 'string' },
  { id: 'config_ui_host', type: 'string' },
  { id: 'config_ui_port', type: 'number' },
  { id: 'workflow.target_account_count', type: 'number' },
  { id: 'workflow.max_registration_attempts', type: 'number' },
  { id: 'workflow.refresh_before_validate', type: 'boolean' },
  { id: 'workflow.auto_delete_invalid', type: 'boolean' },
  { id: 'workflow.auto_sync_cpa', type: 'boolean' },
  { id: 'defaults.email_service_type', type: 'string' },
  { id: 'defaults.email_service_id', type: 'nullable-number' },
  { id: 'defaults.proxy_id', type: 'nullable-number' },
  { id: 'defaults.cpa_service_id', type: 'nullable-number' },
  { id: 'registration.default_count', type: 'number' },
  { id: 'registration.auto_upload_cpa', type: 'boolean' },
  { id: 'registration.save_to_database', type: 'boolean' },
  { id: 'registration.service_config', type: 'json-object' },
  { id: 'proxy_enabled', type: 'boolean' },
  { id: 'proxy_type', type: 'string' },
  { id: 'proxy_host', type: 'string' },
  { id: 'proxy_port', type: 'number' },
  { id: 'proxy_username', type: 'string' },
  { id: 'proxy_password', type: 'string' },
  { id: 'proxy_policy.registration', type: 'boolean' },
  { id: 'proxy_policy.account_validate', type: 'boolean' },
  { id: 'proxy_policy.token_refresh', type: 'boolean' },
  { id: 'proxy_policy.cpa_upload', type: 'boolean' },
  { id: 'proxy_policy.cpa_test', type: 'boolean' },
  { id: 'proxy_dynamic.enabled', type: 'boolean' },
  { id: 'proxy_dynamic.api_url', type: 'string' },
  { id: 'proxy_dynamic.api_key', type: 'string' },
  { id: 'proxy_dynamic.api_key_header', type: 'string' },
  { id: 'proxy_dynamic.result_field', type: 'string' },
  { id: 'tempmail_base_url', type: 'string' },
  { id: 'tempmail_timeout', type: 'number' },
  { id: 'tempmail_max_retries', type: 'number' },
  { id: 'custom_domain_base_url', type: 'string' },
  { id: 'custom_domain_api_key', type: 'string' },
  { id: 'cpa_enabled', type: 'boolean' },
  { id: 'cpa_api_url', type: 'string' },
  { id: 'cpa_api_token', type: 'string' }
];
const jsonArrayFields = ['proxies', 'email_services', 'cpa_services'];

function readPath(obj, path) {
  return path.split('.').reduce((current, key) => current == null ? undefined : current[key], obj);
}

function writePath(obj, path, value) {
  const parts = path.split('.');
  let current = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const key = parts[i];
    if (typeof current[key] !== 'object' || current[key] === null || Array.isArray(current[key])) {
      current[key] = {};
    }
    current = current[key];
  }
  current[parts[parts.length - 1]] = value;
}

function formatValue(value, type) {
  if (type === 'json-object') {
    return JSON.stringify(value || {}, null, 2);
  }
  if (value === undefined || value === null) {
    return '';
  }
  return String(value);
}

function parseValue(raw, type) {
  if (type === 'boolean') {
    return raw === 'true';
  }
  if (type === 'number') {
    return raw === '' ? 0 : Number(raw);
  }
  if (type === 'nullable-number') {
    return raw === '' ? null : Number(raw);
  }
  if (type === 'json-object') {
    return JSON.parse(raw || '{}');
  }
  return raw;
}

async function loadConfig() {
  const response = await fetch('/api/config');
  const payload = await response.json();
  document.getElementById('config-path').textContent = payload.path;
  const cfg = payload.config;

  for (const field of fieldDefs) {
    const node = document.getElementById(field.id);
    node.value = formatValue(readPath(cfg, field.id), field.type);
  }
  for (const key of jsonArrayFields) {
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
    for (const field of fieldDefs) {
      const node = document.getElementById(field.id);
      writePath(payload, field.id, parseValue(node.value, field.type));
    }
    for (const key of jsonArrayFields) {
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
