# 使用说明

## 思路

本项目现已转为配置优先：

1. 把日常默认值放在 `config.json` 中
2. 仅在临时场景使用 CLI 参数作为覆盖
3. 优先使用最简命令完成任务

对大多数用户，日常命令是：

```bash
python main.py run
```

## 快速开始

### 1. 准备运行时文件

```bash
python main.py db init
```

### 2. 编辑配置

选择下面之一：

```bash
python main.py config ui
```

或直接编辑 `config.json`。

### 3. 运行主流程

```bash
python main.py run
```

## 主流程

`python main.py run` 使用 `config.json` 执行以下操作：

1. 校验当前数据库账号
2. 可选：在验证之前刷新令牌
3. 当配置允许时删除无效账号
4. 统计可用有效账号数 
5. 读取目标账号数 
6. 注册账号使得有效账号数达到目标
7. 如果某些注册失败，继续重试直到达成目标或耗尽配置尝试上限
8. 可选：将活跃账号上传到 CPA

## 命令集

### 运行完整流程

```bash
python main.py run                    # 执行完整流程，使用 config.json 中的默认值
python main.py run --target-count 20  # 执行完整流程，临时覆盖目标账号数为 20
python main.py run --sync-cpa         # 执行完整流程，临时覆盖注册后自动上传 CPA 为 True
python main.py run --no-sync-cpa      # 执行完整流程，临时覆盖注册后自动上传 CPA 为 False
python main.py run --output json      # 执行完整流程，输出 JSON 格式结果
```

可见参数：

- `--target-count`：临时覆盖 `workflow.target_account_count`
- `--refresh-before-validate` / `--no-refresh-before-validate`：临时覆盖 `workflow.refresh_before_validate`
- `--sync-cpa` / `--no-sync-cpa`：临时覆盖 `workflow.auto_sync_cpa`
- `--output {text,json}`

### 仅注册

```bash     
python main.py register                    # 注册账号，使用 config.json 中的默认值
python main.py register --count 5          # 注册账号，临时覆盖注册账号数为 5
python main.py register --upload-cpa       # 注册账号，临时覆盖注册后自动上传 CPA 为 True
python main.py register --no-upload-cpa    # 注册账号，临时覆盖注册后自动上传 CPA 为 False
```

可见参数：

- `--count`：临时覆盖 `registration.default_count`
- `--upload-cpa` / `--no-upload-cpa`：临时覆盖 `registration.auto_upload_cpa`
- `--output {text,json}`

### 验证或清理账号

```bash
python main.py accounts validate                        # 验证账号有效性，使用 config.json 中的默认值
python main.py accounts delete-invalid                  # 删除无效账号，使用 config.json 中的默认值
python main.py accounts validate --account-ids 1,2,3    # 验证指定账号 ID 的有效性
python main.py accounts delete-invalid --status active  # 删除状态为 active 的账号（谨慎使用）
```

行为说明：

- 未指定账号 ID 时命令自动对全部匹配账号生效。
- 令牌刷新与验证代理由 `proxy.policy` 控制。
- 当执行 `delete-invalid` 且 `cpa.local_files.enabled=true` 时，会尝试把本地 CPA 目录里的对应 `email.json` 移动到垃圾箱目录。

### CPA

```bash
python main.py cpa test                         # 测试 CPA 连接，使用 config.json 中的默认值
python main.py cpa upload                       # 上传活跃账号到 CPA，使用 config.json 中的默认值
python main.py cpa upload --only-not-uploaded   # 仅上传未曾上传过的活跃账号
python main.py cpa sync-local                   # 从本地 CPA json 文件同步账号到数据库
python main.py cpa sync-local --path C:\\Users\\.cli-proxy-api
```

行为说明：

- 未指定账号 ID 时 `cpa upload` 默认对活跃账号执行。
- CPA 代理使用由 `proxy.policy.cpa_upload` 与 `proxy.policy.cpa_test` 控制。
- `cpa sync-local` 会读取 `cpa.local_files.path` 或 `--path` 指定目录下的 `*.json` 文件，并按邮箱创建或更新数据库账号记录。

### 配置

```bash
python main.py config path                # 输出配置文件路径
python main.py config show --output json  # 输出当前配置，临时覆盖输出格式为 JSON（注意敏感信息泄露风险）
python main.py config ui                  # 启动交互式配置 UI，修改后自动保存到 config.json
```

## `config.json` 结构

推荐配置骨架：

```json
{
  "app": {
    "name": "Codex CLI registration system",
    "version": "2.2.0",
    "debug": false
  },
  "runtime": {
    "database_url": "sqlite:///data/database.db",
    "log_level": "INFO",
    "log_file": "logs/app.log",
    "log_retention_days": 30
  },
  "ui": {
    "host": "127.0.0.1",
    "port": 8765
  },
  "resources": {
    "defaults": {
      "email_service_type": "tempmail",
      "email_service_id": null,
      "proxy_id": null,
      "cpa_service_id": null
    },
    "proxies": [],
    "email_services": [],
    "cpa_services": []
  },
  "registration": {
    "default_count": 1,
    "auto_upload_cpa": false,
    "save_to_database": true,
    "service_config": {}
  },
  "workflow": {
    "target_account_count": 10,
    "refresh_before_validate": true,
    "auto_delete_invalid": true,
    "auto_sync_cpa": false,
    "max_registration_attempts": 0
  },
  "proxy": {
    "static": {
      "enabled": false,
      "type": "http",
      "host": "127.0.0.1",
      "port": 7890,
      "username": "",
      "password": ""
    },
    "policy": {
      "registration": true,
      "account_validate": true,
      "token_refresh": true,
      "cpa_upload": false,
      "cpa_test": false
    },
    "dynamic": {
      "enabled": false,
      "api_url": "",
      "api_key": "",
      "api_key_header": "X-API-Key",
      "result_field": ""
    }
  },
  "mail": {
    "tempmail": {
      "base_url": "https://api.tempmail.lol/v2",
      "timeout": 30,
      "max_retries": 3
    },
    "custom_domain": {
      "base_url": "",
      "api_key": ""
    },
    "verification": {
      "code_timeout": 120,
      "code_poll_interval": 3
    },
    "outlook": {
      "provider_priority": [
        "imap_old",
        "imap_new",
        "graph_api"
      ],
      "health_failure_threshold": 5,
      "health_disable_duration": 60,
      "default_client_id": "24d9a0ed-8787-4584-883c-2fd79308940a"
    }
  },
  "cpa": {
    "enabled": false,
    "api_url": "",
    "api_token": "",
    "local_files": {
      "enabled": false,
      "path": "~/.cli-proxy-api",
      "trash_dir": ""
    }
  }
}
```

## 配置工作机制

优先级：

1. 临时 CLI 覆盖
2. `config.json`
3. 旧数据库资源表回退
4. 内置默认值

因此建议日常流程：

1. 配置一次
2. 重复执行简短命令

## 代理配置

### 静态代理

```json
{
  "proxy": {
    "static": {
      "enabled": true,
      "type": "http",
      "host": "127.0.0.1",
      "port": 7890,
      "username": "",
      "password": ""
    }
  }
}
```

### 代理池

```json
{
  "resources": {
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
}
```

### 动态代理

```json
{
  "proxy": {
    "dynamic": {
      "enabled": true,
      "api_url": "https://proxy.example.com/get",
      "api_key": "YOUR_KEY",
      "api_key_header": "X-API-Key",
      "result_field": "data.proxy"
    }
  }
}
```

### 决定哪些行为使用代理

```json
{
  "proxy": {
    "policy": {
      "registration": true,
      "account_validate": true,
      "token_refresh": true,
      "cpa_upload": false,
      "cpa_test": false
    }
  }
}
```

含义：

- `registration`：注册流程与邮箱服务请求使用代理解析
- `account_validate`：账号有效性验证使用代理解析
- `token_refresh`：刷新前验证使用代理解析
- `cpa_upload`：CPA 上传使用代理解析
- `cpa_test`：CPA 测试使用代理解析

### 选择默认代理资源

```json
{
  "resources": {
    "defaults": {
      "proxy_id": 1
    }
  }
}
```

当行为可代理时，解析顺序：

1. CLI 临时 `--proxy`
2. CLI 临时 `--proxy-id`
3. `resources.defaults.proxy_id`
4. `proxy.dynamic`
5. 静态代理配置
6. `resources.proxies` 中启用代理
7. 旧数据库代理回退
8. 直连

## 邮件配置

### 内置 temp mail 默认

```json
{
  "mail": {
    "tempmail": {
      "base_url": "https://api.tempmail.lol/v2",
      "timeout": 30,
      "max_retries": 3
    }
  }
}
```

### 默认邮箱服务选择

```json
{
  "resources": {
    "defaults": {
      "email_service_type": "tempmail",
      "email_service_id": null
    }
  }
}
```

当你希望绑定到可复用服务记录时，使用 `email_service_id`。
当你希望基于类型默认时，使用 `email_service_type`。

### 可复用邮箱服务

```json
{
  "resources": {
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
}
```

### 注册专用内联默认

```json
{
  "registration": {
    "service_config": {
      "domain": "mail.example.com"
    }
  }
}
```

此值在运行前合并到解析后的邮件服务配置中。

## CPA 配置

### 单个默认 CPA 目标

```json
{
  "cpa": {
    "enabled": true,
    "api_url": "https://cpa.example.com/v0",
    "api_token": "YOUR_TOKEN"
  }
}
```

### 多个 CPA 目标

```json
{
  "resources": {
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
}
```

### 选择默认 CPA 目标

```json
{
  "resources": {
    "defaults": {
      "cpa_service_id": 1
    }
  }
}
```

### 决定何时自动执行 CPA

```json
{
  "registration": {
    "auto_upload_cpa": false
  },
  "workflow": {
    "auto_sync_cpa": true
  }
}
```

含义：

- `registration.auto_upload_cpa`：每次 `register` 后立即上传
- `workflow.auto_sync_cpa`：`run` 结束时上传所有活跃账号

### 清理本地 CPA 认证文件

```json
{
  "cpa": {
    "local_files": {
      "enabled": true,
      "path": "C:\\Users\\wqchen\\.cli-proxy-api",
      "trash_dir": "C:\\Users\\wqchen\\.cli-proxy-api\\_trash"
    }
  }
}
```

说明：

- `path` 支持填写目录，也支持直接填写某个 `email.json` 文件路径，系统会自动取其父目录。
- 当执行 `accounts delete-invalid` 或 `run` 里的自动清理逻辑时，会尝试把失效账号对应的本地 `json` 文件移入垃圾箱目录。
- 垃圾箱目录留空时，默认使用 `path/_trash`。
- 当执行 `python main.py cpa sync-local` 时，会从同一目录读取本地 `json` 文件，将其中的账号同步进数据库。

## 工作流默认设置

推荐日常配置：

```json
{
  "workflow": {
    "target_account_count": 20,
    "refresh_before_validate": true,
    "auto_delete_invalid": true,
    "auto_sync_cpa": true,
    "max_registration_attempts": 60
  },
  "registration": {
    "default_count": 1,
    "auto_upload_cpa": false
  }
}
```

说明：

- `max_registration_attempts=0` 表示使用内置自动重试上限。
- `auto_delete_invalid=true` 让 `run` 真正清理数据库而不是仅标记无效。

## 临时覆盖

CLI 仍支持特殊场景的临时覆盖参数，非日常用法。

常见高级覆盖：

- `--proxy`
- `--proxy-id`
- `--service-id`
- `--service-type`
- `--service-config`
- `--service-config-file`
- `--cpa-service-id`
- `--cpa-api-url`
- `--cpa-api-token`
- `--database-url`
- `--log-level`

示例：

```bash
python main.py run --target-count 50 --proxy http://127.0.0.1:7890
python main.py register --count 3 --service-id 2
python main.py cpa upload --account-ids 1,2,3 --cpa-service-id 1
```

## 一键批处理文件

`ensure_target_accounts.bat` 现在直接转发到配置驱动流程：

```bat
ensure_target_accounts.bat
ensure_target_accounts.bat --target-count 20
ensure_target_accounts.bat --target-count 20 --sync-cpa
```

等效命令：

```bash
python main.py run [temporary overrides]
```

## 可选 `.env`

`.env` 仍有价值，仅用于路径级运行时覆盖。

支持字段：

- `APP_CONFIG_PATH`
- `APP_DATABASE_URL`
- `DATABASE_URL`

示例：

```dotenv
APP_CONFIG_PATH=H:\\CliProxy\\codex-console\\source_code\\config.json
APP_DATABASE_URL=sqlite:///H:/CliProxy/codex-console/source_code/data/database.db
```

## 退出码

- `0`：命令成功完成
- `1`：命令运行完成，但验证/注册/上传未完全成功
- `2`：CLI 参数或运行时配置错误
