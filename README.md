# codex-console

CLI-first account workflow with a file-based configuration model.

## What Changed

- Runtime configuration is now managed by `config.json`
- A lightweight local settings UI is available through `python main.py config ui`
- The database is used for account data, not as the primary settings store
- Payment-related code and dependencies were removed

## Retained Project Trunk

- `src/`: source code
- `config.json`: primary runtime configuration file
- `data/`: runtime database files
- `logs/`: runtime logs
- `main.py`: single entrypoint
- `requirements.txt`: runtime dependencies
- `.env.example`: optional path override example
- `README.md` and `Usage.md`: documentation
- `ensure_target_accounts.bat`: one-click target-account workflow

## Entry Point

```bash
python main.py --help
```

## Configuration

Show the active config:

```bash
python main.py config show --output json
```

Print the config path:

```bash
python main.py config path
```

Launch the local config editor UI:

```bash
python main.py config ui
```

Default UI address:

```text
http://127.0.0.1:8765
```

## Common Workflows

Initialize database:

```bash
python main.py db init
```

Run one registration:

```bash
python main.py register --output json
```

Validate stored accounts:

```bash
python main.py accounts validate --all --refresh-before-validate --output json
```

Ensure the database contains a target number of valid accounts and sync CPA:

```bash
python main.py accounts ensure-target --target-count 20 --refresh-before-validate --output json
```

One-click batch wrapper:

```bat
ensure_target_accounts.bat 20
```

## How Configuration Works

Priority order:

1. CLI arguments
2. `config.json`
3. Legacy database resource tables, only as fallback
4. Built-in defaults

Typical examples:

- Static proxy: edit `proxy_enabled`, `proxy_host`, `proxy_port`, `proxy_username`, `proxy_password`
- Proxy pool: edit `proxies`
- Email services: edit `email_services`
- CPA target: edit `cpa_enabled`, `cpa_api_url`, `cpa_api_token`, or `cpa_services`

## Optional `.env`

`.env` is still useful for path overrides only.

Supported keys:

- `APP_CONFIG_PATH`
- `APP_DATABASE_URL`
- `DATABASE_URL`

## Documentation

- [Usage.md](Usage.md)

## Disclaimer

This repository is for learning, research, and engineering discussion.
Use it in compliance with the relevant platform rules and laws.
