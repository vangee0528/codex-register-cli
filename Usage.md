# Usage

## Overview

The project now uses a unified file-based configuration model.

Primary entrypoint:

```bash
python main.py <command>
```

Primary configuration file:

```text
config.json
```

Optional path overrides in `.env`:

- `APP_CONFIG_PATH`
- `APP_DATABASE_URL`
- `DATABASE_URL`

## Configuration Model

Runtime configuration priority:

1. CLI arguments
2. `config.json`
3. legacy database resource tables as fallback
4. built-in defaults

That means normal users should configure the project through `config.json` or the config UI, not by writing into database settings tables.

## Config Commands

Show the active config file:

```bash
python main.py config show --output json
```

Show the active config path:

```bash
python main.py config path
```

Launch the local config editor UI:

```bash
python main.py config ui
```

Optional UI bind override:

```bash
python main.py config ui --host 127.0.0.1 --port 8765
```

## Config UI

Open the browser at:

```text
http://127.0.0.1:8765
```

The UI edits and saves `config.json` directly.

It currently covers:

- database path and logging
- static proxy settings
- Tempmail and custom-domain mail defaults
- CPA settings
- proxy pool JSON
- email service JSON
- CPA service JSON

## `config.json` Structure

Typical file skeleton:

```json
{
  "database_url": "data/database.db",
  "log_level": "INFO",
  "proxy_enabled": false,
  "proxy_type": "http",
  "proxy_host": "127.0.0.1",
  "proxy_port": 7890,
  "proxy_username": "",
  "proxy_password": "",
  "tempmail_base_url": "https://api.tempmail.lol/v2",
  "custom_domain_base_url": "",
  "custom_domain_api_key": "",
  "cpa_enabled": false,
  "cpa_api_url": "",
  "cpa_api_token": "",
  "proxies": [],
  "email_services": [],
  "cpa_services": []
}
```

## How To Configure Proxy

### Static global proxy

Edit these fields in `config.json`:

```json
{
  "proxy_enabled": true,
  "proxy_type": "http",
  "proxy_host": "127.0.0.1",
  "proxy_port": 7890,
  "proxy_username": "",
  "proxy_password": ""
}
```

This becomes the default proxy when no CLI proxy override is passed.

### Proxy pool

Use the `proxies` array for multiple proxies:

```json
{
  "proxies": [
    {
      "id": 1,
      "name": "default-http",
      "enabled": true,
      "is_default": true,
      "proxy_url": "http://127.0.0.1:7890"
    },
    {
      "id": 2,
      "name": "backup-socks",
      "enabled": true,
      "is_default": false,
      "type": "socks5",
      "host": "127.0.0.1",
      "port": 1080,
      "username": "",
      "password": ""
    }
  ]
}
```

Usage examples:

```bash
python main.py register --proxy http://127.0.0.1:7890
python main.py register --proxy-id 1
python main.py accounts ensure-target --target-count 20 --proxy-id 2
```

Resolution order:

1. `--proxy`
2. `--proxy-id`
3. static proxy from `config.json`
4. enabled default proxy from `proxies`
5. legacy database proxy fallback
6. no proxy

## How To Configure Email

There are two levels.

### Default built-in mail settings

For default Tempmail and custom-domain mail:

```json
{
  "tempmail_base_url": "https://api.tempmail.lol/v2",
  "tempmail_timeout": 30,
  "tempmail_max_retries": 3,
  "custom_domain_base_url": "https://mail.example.com/api",
  "custom_domain_api_key": "YOUR_KEY"
}
```

### Email service pool

Use `email_services` to define reusable mail backends:

```json
{
  "email_services": [
    {
      "id": 1,
      "name": "imap-main",
      "type": "imap_mail",
      "enabled": true,
      "priority": 0,
      "config": {
        "host": "imap.example.com",
        "email": "user@example.com",
        "password": "app-password"
      }
    },
    {
      "id": 2,
      "name": "duck-primary",
      "type": "duck_mail",
      "enabled": true,
      "priority": 1,
      "config": {
        "base_url": "https://duck.example.com",
        "default_domain": "mail.example.com"
      }
    }
  ]
}
```

Usage examples:

```bash
python main.py register --service-id 1
python main.py register --service-type duck_mail
python main.py accounts ensure-target --target-count 30 --service-id 2
```

Resolution order:

1. `--service-id`
2. `--service-type`
3. matching enabled service in `config.json.email_services`
4. legacy database email service fallback
5. built-in default config

## How To Configure CPA

### Single CPA target

```json
{
  "cpa_enabled": true,
  "cpa_api_url": "https://cpa.example.com/v0",
  "cpa_api_token": "YOUR_TOKEN"
}
```

### Multiple CPA targets

```json
{
  "cpa_services": [
    {
      "id": 1,
      "name": "primary",
      "api_url": "https://cpa.example.com/v0",
      "api_token": "YOUR_TOKEN",
      "enabled": true,
      "priority": 0
    }
  ]
}
```

Usage examples:

```bash
python main.py cpa test
python main.py cpa upload --all --cpa-service-id 1
python main.py register --auto-upload-cpa --cpa-api-url https://cpa.example.com/v0 --cpa-api-token YOUR_TOKEN
```

## Database Initialization

```bash
python main.py db init
```

With explicit database override:

```bash
python main.py db init --database-url sqlite:///./tmp/accounts.db
```

## Service Discovery

```bash
python main.py services list
python main.py services list --output json
python main.py services proxies --output json
```

These commands now show `config.json` resources first, with legacy database resources marked separately when present.

## Registration

### Syntax

```bash
python main.py register [options]
```

### Options

```text
--service-type {tempmail,outlook,moe_mail,temp_mail,duck_mail,freemail,imap_mail}
--service-id ID
--service-config JSON
--service-config-file PATH
--proxy URL
--proxy-id ID
--database-url URL
--output {text,json}
--no-save
--log-level LEVEL
--count N
--auto-upload-cpa
--cpa-api-url URL
--cpa-api-token TOKEN
--cpa-service-id ID
```

Examples:

```bash
python main.py register --output json
python main.py register --count 5 --output json
python main.py register --service-id 1 --proxy-id 2
python main.py register --service-config-file .\imap.json
```

## Account Management

### accounts list

```bash
python main.py accounts list
python main.py accounts list --status active --limit 50 --output json
```

### accounts validate

```bash
python main.py accounts validate --all --refresh-before-validate --output json
python main.py accounts validate --account-ids 1,2,3 --proxy http://127.0.0.1:7890
```

Behavior:

- valid accounts are marked `active`
- invalid accounts are marked `expired`

### accounts delete-invalid

```bash
python main.py accounts delete-invalid --all --status active --refresh-before-validate
```

Behavior:

- invalid accounts are marked `expired`
- invalid rows are deleted from the database

### accounts ensure-target

This is the one-shot workflow for maintaining a target number of valid accounts.

Process:

1. validate all stored accounts
2. compute current valid count `a`
3. take desired count `b`
4. compute `b-a`
5. delete invalid accounts
6. register until the gap is closed
7. if registration fails, continue retrying until the target is reached or `--max-attempts` is exhausted
8. sync all active accounts to CPA

Syntax:

```bash
python main.py accounts ensure-target --target-count B [options]
```

Options:

```text
--target-count N
--refresh-before-validate
--proxy URL
--proxy-id ID
--service-type {tempmail,outlook,moe_mail,temp_mail,duck_mail,freemail,imap_mail}
--service-id ID
--service-config JSON
--service-config-file PATH
--log-level LEVEL
--max-attempts N
--skip-cpa-sync
--cpa-api-url URL
--cpa-api-token TOKEN
--cpa-service-id ID
--database-url URL
--output {text,json}
```

Examples:

```bash
python main.py accounts ensure-target --target-count 20 --refresh-before-validate --output json
python main.py accounts ensure-target --target-count 50 --service-id 1 --proxy-id 2 --cpa-service-id 1 --output json
python main.py accounts ensure-target --target-count 100 --max-attempts 150 --output json
```

Batch wrapper:

```bat
ensure_target_accounts.bat 20
ensure_target_accounts.bat 50 --service-id 1 --proxy-id 2 --cpa-service-id 1
```

## CPA Operations

### cpa test

```bash
python main.py cpa test
python main.py cpa test --cpa-service-id 1 --output json
```

### cpa upload

```bash
python main.py cpa upload --all --status active --only-not-uploaded --output json
python main.py cpa upload --account-ids 1,2,3 --cpa-service-id 1
```

## Exit Codes

- `0`: requested command completed successfully
- `1`: the command ran but a validation, registration, or upload step failed
- `2`: CLI argument or runtime configuration error
