"""Local config editor UI served with the standard library."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ..config import get_config_path, init_default_settings, read_raw_config, write_raw_config


HTML_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>codex-console 配置台</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --surface: rgba(255, 255, 255, 0.86);
      --line: rgba(15, 23, 42, 0.08);
      --text: #0f172a;
      --muted: #52607a;
      --accent: #0f766e;
      --accent-strong: #115e59;
      --accent-soft: rgba(15, 118, 110, 0.12);
      --danger: #b42318;
      --shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
      --radius-xl: 28px;
      --radius-lg: 20px;
      --radius-md: 14px;
      --font-ui: "Segoe UI Variable", "Microsoft YaHei UI", "PingFang SC", sans-serif;
      --font-mono: "Cascadia Code", "Consolas", monospace;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      color: var(--text);
      font-family: var(--font-ui);
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.22), transparent 32%),
        radial-gradient(circle at top right, rgba(37, 99, 235, 0.18), transparent 28%),
        linear-gradient(180deg, #f8fbff 0%, #eef4fa 52%, #edf2f7 100%);
      min-height: 100vh;
    }
    .shell {
      width: min(1480px, calc(100vw - 32px));
      margin: 24px auto;
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      gap: 20px;
      align-items: start;
    }
    .sidebar, .panel {
      backdrop-filter: blur(20px);
      background: var(--surface);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }
    .sidebar {
      position: sticky;
      top: 18px;
      border-radius: var(--radius-xl);
      padding: 22px 18px;
    }
    .brand {
      padding: 6px 6px 18px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 18px;
    }
    .brand h1 {
      margin: 0;
      font-size: 28px;
      line-height: 1.05;
      letter-spacing: -0.03em;
    }
    .brand p {
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }
    .nav {
      display: grid;
      gap: 10px;
    }
    .nav a {
      text-decoration: none;
      color: var(--text);
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.64);
      border: 1px solid transparent;
      transition: 140ms ease;
      font-size: 14px;
    }
    .nav a:hover {
      transform: translateY(-1px);
      border-color: var(--line);
      background: #fff;
    }
    .panel {
      border-radius: 32px;
      overflow: hidden;
    }
    .hero {
      padding: 28px 30px 20px;
      border-bottom: 1px solid var(--line);
      background:
        radial-gradient(circle at top right, rgba(15, 118, 110, 0.14), transparent 34%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.82));
    }
    .hero-top {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-start;
      flex-wrap: wrap;
    }
    .hero h2 {
      margin: 0;
      font-size: clamp(30px, 4vw, 46px);
      line-height: 1;
      letter-spacing: -0.04em;
    }
    .hero p {
      margin: 10px 0 0;
      max-width: 780px;
      color: var(--muted);
      line-height: 1.7;
      font-size: 15px;
    }
    .meta {
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(15, 118, 110, 0.08);
      border: 1px solid rgba(15, 118, 110, 0.14);
      min-width: 280px;
    }
    .meta-title {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 6px;
    }
    .mono {
      font-family: var(--font-mono);
      font-size: 12px;
      line-height: 1.6;
      word-break: break-all;
    }
    .toolbar {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 22px;
    }
    button {
      appearance: none;
      border: none;
      border-radius: 999px;
      padding: 12px 18px;
      font: inherit;
      cursor: pointer;
      transition: 150ms ease;
    }
    button.primary {
      background: linear-gradient(135deg, var(--accent), #0b8f83);
      color: #fff;
      box-shadow: 0 16px 32px rgba(15, 118, 110, 0.22);
    }
    button.secondary {
      background: rgba(15, 23, 42, 0.06);
      color: var(--text);
      border: 1px solid var(--line);
    }
    button:hover { transform: translateY(-1px); }
    #status {
      margin-top: 14px;
      font-size: 14px;
      font-weight: 700;
    }
    .content {
      padding: 24px;
      display: grid;
      gap: 18px;
    }
    .section {
      border-radius: var(--radius-xl);
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid var(--line);
      padding: 22px;
    }
    .section-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 18px;
      flex-wrap: wrap;
    }
    .section h3 {
      margin: 0;
      font-size: 22px;
      letter-spacing: -0.03em;
    }
    .section p {
      margin: 6px 0 0;
      color: var(--muted);
      line-height: 1.65;
      font-size: 14px;
      max-width: 760px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 14px;
    }
    .field {
      grid-column: span 6;
      display: grid;
      gap: 7px;
    }
    .field.wide, .field.full { grid-column: 1 / -1; }
    .field.narrow { grid-column: span 4; }
    label {
      font-size: 13px;
      color: var(--muted);
      font-weight: 700;
    }
    .hint {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
      margin-top: -2px;
    }
    input, textarea, select {
      width: 100%;
      border-radius: var(--radius-md);
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.96);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
      transition: 120ms ease;
    }
    input:focus, textarea:focus, select:focus {
      outline: none;
      border-color: rgba(15, 118, 110, 0.5);
      box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.1);
    }
    textarea {
      min-height: 180px;
      resize: vertical;
      font-family: var(--font-mono);
      font-size: 12px;
      line-height: 1.65;
    }
    .pillbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 8px;
    }
    .pill {
      font-size: 12px;
      border-radius: 999px;
      padding: 7px 11px;
      background: var(--accent-soft);
      color: var(--accent-strong);
      border: 1px solid rgba(15, 118, 110, 0.12);
    }
    @media (max-width: 1080px) {
      .shell { grid-template-columns: 1fr; }
      .sidebar { position: static; }
    }
    @media (max-width: 720px) {
      .content, .hero { padding-left: 18px; padding-right: 18px; }
      .section { padding: 18px; }
      .field, .field.narrow { grid-column: 1 / -1; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <h1>配置台</h1>
        <p>把运行参数按领域拆开。先配默认值，再执行简短命令。</p>
      </div>
      <nav class="nav">
        <a href="#runtime">运行与日志</a>
        <a href="#workflow">工作流</a>
        <a href="#resources">默认资源</a>
        <a href="#proxy">代理</a>
        <a href="#mail">邮件</a>
        <a href="#cpa">CPA</a>
        <a href="#advanced">高级设置</a>
        <a href="#pools">资源池 JSON</a>
      </nav>
    </aside>

    <main class="panel">
      <section class="hero">
        <div class="hero-top">
          <div>
            <h2>codex-console</h2>
            <p>这是一份配置驱动的工作台。大多数场景只需要先在这里设好默认行为，然后通过 <span class="mono">python main.py run</span> 执行主流程。</p>
            <div class="pillbar">
              <span class="pill">配置优先</span>
              <span class="pill">兼容旧版字段</span>
              <span class="pill">支持本地 CPA 文件清理</span>
            </div>
          </div>
          <div class="meta">
            <div class="meta-title">当前配置文件</div>
            <div id="config-path" class="mono"></div>
          </div>
        </div>
        <div class="toolbar">
          <button class="primary" id="save">保存配置</button>
          <button class="secondary" id="reload">重新加载</button>
        </div>
        <div id="status"></div>
      </section>

      <div class="content">
        <section class="section" id="runtime">
          <div class="section-header">
            <div>
              <h3>运行与日志</h3>
              <p>决定数据库、日志和本地配置 UI 的监听地址。</p>
            </div>
          </div>
          <div class="grid">
            <div class="field wide">
              <label for="runtime.database_url">数据库地址</label>
              <input id="runtime.database_url" />
            </div>
            <div class="field narrow">
              <label for="runtime.log_level">日志级别</label>
              <input id="runtime.log_level" />
            </div>
            <div class="field narrow">
              <label for="runtime.log_retention_days">日志保留天数</label>
              <input id="runtime.log_retention_days" type="number" />
            </div>
            <div class="field wide">
              <label for="runtime.log_file">日志文件</label>
              <input id="runtime.log_file" />
            </div>
            <div class="field narrow">
              <label for="ui.host">配置台主机</label>
              <input id="ui.host" />
            </div>
            <div class="field narrow">
              <label for="ui.port">配置台端口</label>
              <input id="ui.port" type="number" />
            </div>
          </div>
        </section>

        <section class="section" id="workflow">
          <div class="section-header">
            <div>
              <h3>工作流</h3>
              <p>这里控制日常主流程的目标数量、校验策略和注册重试边界。</p>
            </div>
          </div>
          <div class="grid">
            <div class="field narrow">
              <label for="workflow.target_account_count">目标账号数</label>
              <input id="workflow.target_account_count" type="number" />
            </div>
            <div class="field narrow">
              <label for="workflow.max_registration_attempts">最大注册尝试数</label>
              <input id="workflow.max_registration_attempts" type="number" />
              <div class="hint">填 0 表示自动计算重试上限。</div>
            </div>
            <div class="field narrow">
              <label for="registration.default_count">单次注册默认数量</label>
              <input id="registration.default_count" type="number" />
            </div>
            <div class="field narrow">
              <label for="workflow.refresh_before_validate">验证前刷新 token</label>
              <select id="workflow.refresh_before_validate"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field narrow">
              <label for="workflow.auto_delete_invalid">自动清理失效账号</label>
              <select id="workflow.auto_delete_invalid"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field narrow">
              <label for="workflow.auto_sync_cpa">流程结束自动同步 CPA</label>
              <select id="workflow.auto_sync_cpa"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field narrow">
              <label for="registration.auto_upload_cpa">单次注册后立即上传 CPA</label>
              <select id="registration.auto_upload_cpa"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field narrow">
              <label for="registration.save_to_database">注册成功后写入数据库</label>
              <select id="registration.save_to_database"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field full">
              <label for="registration.service_config">注册时附加服务配置</label>
              <textarea id="registration.service_config"></textarea>
            </div>
          </div>
        </section>

        <section class="section" id="resources">
          <div class="section-header">
            <div>
              <h3>默认资源</h3>
              <p>给日常命令指定默认邮箱服务、代理和 CPA 目标。CLI 参数只在单次运行时覆盖这里。</p>
            </div>
          </div>
          <div class="grid">
            <div class="field narrow">
              <label for="resources.defaults.email_service_type">默认邮箱服务类型</label>
              <input id="resources.defaults.email_service_type" />
            </div>
            <div class="field narrow">
              <label for="resources.defaults.email_service_id">默认邮箱服务 ID</label>
              <input id="resources.defaults.email_service_id" type="number" />
            </div>
            <div class="field narrow">
              <label for="resources.defaults.proxy_id">默认代理 ID</label>
              <input id="resources.defaults.proxy_id" type="number" />
            </div>
            <div class="field narrow">
              <label for="resources.defaults.cpa_service_id">默认 CPA 服务 ID</label>
              <input id="resources.defaults.cpa_service_id" type="number" />
            </div>
          </div>
        </section>

        <section class="section" id="proxy">
          <div class="section-header">
            <div>
              <h3>代理</h3>
              <p>包含静态代理、动态代理获取和不同动作的代理策略。优先级关系以 CLI 参数为最高。</p>
            </div>
          </div>
          <div class="grid">
            <div class="field narrow">
              <label for="proxy.static.enabled">启用静态代理</label>
              <select id="proxy.static.enabled"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field narrow">
              <label for="proxy.static.type">代理类型</label>
              <input id="proxy.static.type" />
            </div>
            <div class="field narrow">
              <label for="proxy.static.port">代理端口</label>
              <input id="proxy.static.port" type="number" />
            </div>
            <div class="field wide">
              <label for="proxy.static.host">代理主机</label>
              <input id="proxy.static.host" />
            </div>
            <div class="field narrow">
              <label for="proxy.static.username">代理用户名</label>
              <input id="proxy.static.username" />
            </div>
            <div class="field narrow">
              <label for="proxy.static.password">代理密码</label>
              <input id="proxy.static.password" type="password" />
            </div>

            <div class="field narrow">
              <label for="proxy.policy.registration">注册走代理</label>
              <select id="proxy.policy.registration"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field narrow">
              <label for="proxy.policy.account_validate">账号校验走代理</label>
              <select id="proxy.policy.account_validate"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field narrow">
              <label for="proxy.policy.token_refresh">刷新 token 走代理</label>
              <select id="proxy.policy.token_refresh"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field narrow">
              <label for="proxy.policy.cpa_upload">CPA 上传走代理</label>
              <select id="proxy.policy.cpa_upload"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field narrow">
              <label for="proxy.policy.cpa_test">CPA 测试走代理</label>
              <select id="proxy.policy.cpa_test"><option value="true">是</option><option value="false">否</option></select>
            </div>

            <div class="field narrow">
              <label for="proxy.dynamic.enabled">启用动态代理</label>
              <select id="proxy.dynamic.enabled"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field wide">
              <label for="proxy.dynamic.api_url">动态代理接口地址</label>
              <input id="proxy.dynamic.api_url" />
            </div>
            <div class="field narrow">
              <label for="proxy.dynamic.api_key">动态代理接口密钥</label>
              <input id="proxy.dynamic.api_key" type="password" />
            </div>
            <div class="field narrow">
              <label for="proxy.dynamic.api_key_header">密钥请求头</label>
              <input id="proxy.dynamic.api_key_header" />
            </div>
            <div class="field narrow">
              <label for="proxy.dynamic.result_field">结果字段路径</label>
              <input id="proxy.dynamic.result_field" />
            </div>
          </div>
        </section>
        
        <section class="section" id="mail">
          <div class="section-header">
            <div>
              <h3>邮件</h3>
              <p>配置内置 tempmail、自定义域名邮箱、验证码轮询和 Outlook 专项参数。</p>
            </div>
          </div>
          <div class="grid">
            <div class="field wide">
              <label for="mail.tempmail.base_url">Tempmail 接口地址</label>
              <input id="mail.tempmail.base_url" />
            </div>
            <div class="field narrow">
              <label for="mail.tempmail.timeout">Tempmail 超时</label>
              <input id="mail.tempmail.timeout" type="number" />
            </div>
            <div class="field narrow">
              <label for="mail.tempmail.max_retries">Tempmail 重试次数</label>
              <input id="mail.tempmail.max_retries" type="number" />
            </div>
            <div class="field wide">
              <label for="mail.custom_domain.base_url">自定义域名邮箱接口</label>
              <input id="mail.custom_domain.base_url" />
            </div>
            <div class="field wide">
              <label for="mail.custom_domain.api_key">自定义域名邮箱密钥</label>
              <input id="mail.custom_domain.api_key" type="password" />
            </div>
            <div class="field narrow">
              <label for="mail.verification.code_timeout">验证码等待超时</label>
              <input id="mail.verification.code_timeout" type="number" />
            </div>
            <div class="field narrow">
              <label for="mail.verification.code_poll_interval">验证码轮询间隔</label>
              <input id="mail.verification.code_poll_interval" type="number" />
            </div>
            <div class="field full">
              <label for="mail.outlook.provider_priority">Outlook provider 优先级</label>
              <textarea id="mail.outlook.provider_priority"></textarea>
              <div class="hint">填写 JSON 数组，例如 <span class="mono">["imap_old","imap_new","graph_api"]</span>。</div>
            </div>
            <div class="field narrow">
              <label for="mail.outlook.health_failure_threshold">Outlook 故障阈值</label>
              <input id="mail.outlook.health_failure_threshold" type="number" />
            </div>
            <div class="field narrow">
              <label for="mail.outlook.health_disable_duration">Outlook 熔断时间</label>
              <input id="mail.outlook.health_disable_duration" type="number" />
            </div>
            <div class="field wide">
              <label for="mail.outlook.default_client_id">Outlook 默认 Client ID</label>
              <input id="mail.outlook.default_client_id" />
            </div>
          </div>
        </section>

        <section class="section" id="cpa">
          <div class="section-header">
            <div>
              <h3>CPA</h3>
              <p>配置远端 CPA 上传目标，以及本地 <span class="mono">json</span> 认证文件的清理策略。删除失效账号时，会尝试把对应本地文件移到垃圾箱目录。</p>
            </div>
          </div>
          <div class="grid">
            <div class="field narrow">
              <label for="cpa.enabled">启用 CPA 上传</label>
              <select id="cpa.enabled"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field wide">
              <label for="cpa.api_url">CPA API 地址</label>
              <input id="cpa.api_url" />
            </div>
            <div class="field wide">
              <label for="cpa.api_token">CPA API Token</label>
              <input id="cpa.api_token" type="password" />
            </div>
            <div class="field narrow">
              <label for="cpa.local_files.enabled">清理本地 CPA 文件</label>
              <select id="cpa.local_files.enabled"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field wide">
              <label for="cpa.local_files.path">本地 CPA 文件目录</label>
              <input id="cpa.local_files.path" />
              <div class="hint">支持填写目录，也支持直接填写某个 <span class="mono">.json</span> 文件路径，系统会自动取其父目录。</div>
            </div>
            <div class="field wide">
              <label for="cpa.local_files.trash_dir">垃圾箱目录</label>
              <input id="cpa.local_files.trash_dir" />
              <div class="hint">留空时默认使用本地 CPA 目录下的 <span class="mono">_trash</span>。</div>
            </div>
          </div>
        </section>

        <section class="section" id="advanced">
          <div class="section-header">
            <div>
              <h3>高级设置</h3>
              <p>这部分通常只在接入协议变化、调试或特殊部署时需要修改。</p>
            </div>
          </div>
          <div class="grid">
            <div class="field narrow">
              <label for="app.debug">调试模式</label>
              <select id="app.debug"><option value="true">是</option><option value="false">否</option></select>
            </div>
            <div class="field wide">
              <label for="openai.client_id">OpenAI Client ID</label>
              <input id="openai.client_id" />
            </div>
            <div class="field wide">
              <label for="openai.auth_url">OpenAI 授权地址</label>
              <input id="openai.auth_url" />
            </div>
            <div class="field wide">
              <label for="openai.token_url">OpenAI Token 地址</label>
              <input id="openai.token_url" />
            </div>
            <div class="field wide">
              <label for="openai.redirect_uri">OpenAI 回调地址</label>
              <input id="openai.redirect_uri" />
            </div>
            <div class="field wide">
              <label for="openai.scope">OpenAI Scope</label>
              <input id="openai.scope" />
            </div>
          </div>
        </section>

        <section class="section" id="pools">
          <div class="section-header">
            <div>
              <h3>资源池 JSON</h3>
              <p>可复用代理、邮箱服务和 CPA 服务统一放在这里。适合一次性维护，日常通过默认资源 ID 引用。</p>
            </div>
          </div>
          <div class="grid">
            <div class="field full">
              <label for="resources.proxies">代理池</label>
              <textarea id="resources.proxies"></textarea>
            </div>
            <div class="field full">
              <label for="resources.email_services">邮箱服务池</label>
              <textarea id="resources.email_services"></textarea>
            </div>
            <div class="field full">
              <label for="resources.cpa_services">CPA 服务池</label>
              <textarea id="resources.cpa_services"></textarea>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>

  <script>
    const fieldDefs = [
      { id: 'app.debug', type: 'boolean' },
      { id: 'runtime.database_url', type: 'string' },
      { id: 'runtime.log_level', type: 'string' },
      { id: 'runtime.log_file', type: 'string' },
      { id: 'runtime.log_retention_days', type: 'number' },
      { id: 'ui.host', type: 'string' },
      { id: 'ui.port', type: 'number' },
      { id: 'workflow.target_account_count', type: 'number' },
      { id: 'workflow.max_registration_attempts', type: 'number' },
      { id: 'workflow.refresh_before_validate', type: 'boolean' },
      { id: 'workflow.auto_delete_invalid', type: 'boolean' },
      { id: 'workflow.auto_sync_cpa', type: 'boolean' },
      { id: 'registration.default_count', type: 'number' },
      { id: 'registration.auto_upload_cpa', type: 'boolean' },
      { id: 'registration.save_to_database', type: 'boolean' },
      { id: 'registration.service_config', type: 'json-object' },
      { id: 'resources.defaults.email_service_type', type: 'string' },
      { id: 'resources.defaults.email_service_id', type: 'nullable-number' },
      { id: 'resources.defaults.proxy_id', type: 'nullable-number' },
      { id: 'resources.defaults.cpa_service_id', type: 'nullable-number' },
      { id: 'proxy.static.enabled', type: 'boolean' },
      { id: 'proxy.static.type', type: 'string' },
      { id: 'proxy.static.host', type: 'string' },
      { id: 'proxy.static.port', type: 'number' },
      { id: 'proxy.static.username', type: 'string' },
      { id: 'proxy.static.password', type: 'string' },
      { id: 'proxy.policy.registration', type: 'boolean' },
      { id: 'proxy.policy.account_validate', type: 'boolean' },
      { id: 'proxy.policy.token_refresh', type: 'boolean' },
      { id: 'proxy.policy.cpa_upload', type: 'boolean' },
      { id: 'proxy.policy.cpa_test', type: 'boolean' },
      { id: 'proxy.dynamic.enabled', type: 'boolean' },
      { id: 'proxy.dynamic.api_url', type: 'string' },
      { id: 'proxy.dynamic.api_key', type: 'string' },
      { id: 'proxy.dynamic.api_key_header', type: 'string' },
      { id: 'proxy.dynamic.result_field', type: 'string' },
      { id: 'mail.tempmail.base_url', type: 'string' },
      { id: 'mail.tempmail.timeout', type: 'number' },
      { id: 'mail.tempmail.max_retries', type: 'number' },
      { id: 'mail.custom_domain.base_url', type: 'string' },
      { id: 'mail.custom_domain.api_key', type: 'string' },
      { id: 'mail.verification.code_timeout', type: 'number' },
      { id: 'mail.verification.code_poll_interval', type: 'number' },
      { id: 'mail.outlook.provider_priority', type: 'json-array' },
      { id: 'mail.outlook.health_failure_threshold', type: 'number' },
      { id: 'mail.outlook.health_disable_duration', type: 'number' },
      { id: 'mail.outlook.default_client_id', type: 'string' },
      { id: 'cpa.enabled', type: 'boolean' },
      { id: 'cpa.api_url', type: 'string' },
      { id: 'cpa.api_token', type: 'string' },
      { id: 'cpa.local_files.enabled', type: 'boolean' },
      { id: 'cpa.local_files.path', type: 'string' },
      { id: 'cpa.local_files.trash_dir', type: 'string' },
      { id: 'openai.client_id', type: 'string' },
      { id: 'openai.auth_url', type: 'string' },
      { id: 'openai.token_url', type: 'string' },
      { id: 'openai.redirect_uri', type: 'string' },
      { id: 'openai.scope', type: 'string' }
    ];

    const jsonArrayFields = ['resources.proxies', 'resources.email_services', 'resources.cpa_services'];

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
      if (type === 'json-array') {
        return JSON.stringify(value || [], null, 2);
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
      if (type === 'json-array') {
        return JSON.parse(raw || '[]');
      }
      return raw;
    }

    function setStatus(message, isError) {
      const node = document.getElementById('status');
      node.textContent = message;
      node.style.color = isError ? 'var(--danger)' : 'var(--accent-strong)';
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
        document.getElementById(key).value = JSON.stringify(readPath(cfg, key) || [], null, 2);
      }
      setStatus('已加载当前配置。', false);
    }

    async function saveConfig() {
      try {
        const payload = {};
        for (const field of fieldDefs) {
          const node = document.getElementById(field.id);
          writePath(payload, field.id, parseValue(node.value, field.type));
        }
        for (const key of jsonArrayFields) {
          writePath(payload, key, JSON.parse(document.getElementById(key).value || '[]'));
        }

        const response = await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.error || '保存失败');
        }
        setStatus('配置已保存到 config.json。', false);
      } catch (error) {
        setStatus(error.message || '保存失败', true);
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
    print(f"配置界面已启动: http://{host}:{port}")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
