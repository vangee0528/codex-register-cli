# codex-console

一个以 CLI 为主、围绕 `config.json` 的账号工作流工具。

## 设计

项目现假设：

1. 日常行为由 `config.json` 定义
2. CLI 参数仅是临时覆盖
3. 主流程通常只用一个命令即可

主要入口：

```bash
python main.py run
```

## 核心命令

运行完整维护流程：

```bash
python main.py run
```

按配置默认值注册账号：

```bash
python main.py register
python main.py register --count 5
```

校验或清理已存账号：

```bash
python main.py accounts validate
python main.py accounts delete-invalid
```

将活跃账号同步到 CPA：

```bash
python main.py cpa upload
```

编辑配置：

```bash
python main.py config ui
python main.py config show --output json
python main.py config path
```

一键批量运行脚本：

```bat
ensure_target_accounts.bat
ensure_target_accounts.bat --target-count 20 --sync-cpa
```

## 主流程

`python main.py run` 执行配置流程：

1. 校验数据库中的当前账号
2. 当 `workflow.auto_delete_invalid=true` 时清理无效账号
3. 统计当前有效账号数 `a`
4. 从 `workflow.target_account_count` 读取目标数 `b`
5. 注册 `b-a` 个新账号，直至补齐或达到重试上限
6. 当 `workflow.auto_sync_cpa=true` 时，将活跃账号上传至 CPA

## 配置

主配置文件：

```text
config.json
```

常用部分：

- `defaults`：默认邮箱服务 / 代理 / CPA 目标选择
- `registration`：默认注册数量和是否自动上传 CPA
- `workflow`：目标账号数量、校验清理、CPA 同步、重试上限
- `proxy_policy`：决定哪些行为走代理
- `proxy_dynamic`：可选动态代理 API
- `proxies`、`email_services`、`cpa_services`：可复用资源池

打开本地配置编辑器：

```bash
python main.py config ui
```

默认地址：

```text
http://127.0.0.1:8765
```

## `.env`

`.env` 依然有用，但仅用于运行时路径覆盖。

支持的环境变量：

- `APP_CONFIG_PATH`
- `APP_DATABASE_URL`
- `DATABASE_URL`

示例模板：[` .env.example `](./.env.example)

## 保留文件

- `main.py`
- `config.json`
- `src/`
- `data/`
- `logs/`
- `Usage.md`
- `README.md`
- `ensure_target_accounts.bat`
- `requirements.txt`
- `pyproject.toml`

## 文档

完整用法：[`Usage.md`](Usage.md)
