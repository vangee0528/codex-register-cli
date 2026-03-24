# codex-register-cli

原项目地址：[codex-console](https://github.com/dou-jiang/codex-console)

本项目是一个以命令行为中心的账号工作流工具，通过统一的 CLI 完成账号注册、账号校验、目标数量补齐、代理选择、邮箱服务接入和 CPA 同步。

当前仓库已经不是“零散脚本集合”的形态，而是一个明确的配置驱动型 CLI 应用：默认行为写在配置里，命令行参数只做临时覆盖，日常使用通常通过少量固定命令完成。

## 项目定位

这个项目的核心目标是把一整套账号处理流程收拢到一个统一入口中，避免手工切换脚本和临时改代码。它主要解决这几件事：

- 根据配置选择邮箱服务和代理
- 执行账号注册流程，并把结果保存到数据库
- 校验已有账号状态，必要时刷新 token
- 清理失效账号，并将账号池补齐到目标数量
- 按配置把有效账号同步到 CPA 服务
- 用本地 Web UI 编辑 `config.json`

## 核心思路

项目的设计思路可以概括为三层：

1. 配置驱动  
   `config.json` 是主配置源，决定默认邮箱服务、代理、工作流目标数量、CPA 目标和代理策略。

2. CLI 编排  
   `src/cli/` 负责命令解析和工作流编排，把“注册”“校验”“清理”“同步”组合成稳定命令。

3. 能力模块化  
   `src/core/`、`src/services/`、`src/database/` 分别负责注册引擎、邮箱服务实现和数据持久化，方便替换资源和扩展流程。

默认工作流 `python main.py run` 的实际逻辑是：

1. 读取配置并初始化运行环境
2. 校验数据库中的现有账号
3. 按配置决定是否删除失效账号
4. 统计当前有效账号数量
5. 如果低于目标值，则继续注册新账号直到补齐或达到重试上限
6. 如果开启了 CPA 自动同步，则上传有效账号

## 功能概览

- 统一 CLI 入口，支持 `run / register / accounts / cpa / config / services / db`
- 支持多种邮箱服务实现
- 支持静态代理、配置池代理、数据库代理、动态代理 API
- 使用 SQLAlchemy 持久化账号、邮箱服务、代理和 CPA 配置
- 支持 SQLite，也兼容 PostgreSQL 连接串
- 提供本地配置编辑器，直接修改 `config.json`

当前代码里已经注册的邮箱服务类型包括：

- `tempmail`
- `outlook`
- `moe_mail`
- `temp_mail`
- `duck_mail`
- `freemail`
- `imap_mail`

## 快速开始

### 运行要求

- Python `>= 3.10`

### 安装依赖

```bash
pip install -r requirements.txt
```

或者：

```bash
pip install -e .
```

### 初始化

项目运行时会自动创建 `data/`、`logs/`、默认数据库和默认配置。首次使用也可以显式执行：

```bash
python main.py db init
```

### 最常用的命令

执行完整工作流：

```bash
python main.py run
```

注册一个或多个账号：

```bash
python main.py register
python main.py register --count 5
```

查看已保存账号：

```bash
python main.py accounts list
```

校验账号：

```bash
python main.py accounts validate
```

删除失效账号：

```bash
python main.py accounts delete-invalid
```

上传账号到 CPA：

```bash
python main.py cpa upload
```

查看当前配置：

```bash
python main.py config show --output json
python main.py config path
```

启动本地配置 UI：

```bash
python main.py config ui
```

默认地址：

```text
http://127.0.0.1:8765
```

## 配置说明

### 配置优先级

项目采用“配置为主，参数覆盖”的方式：

1. `config.json` 作为主配置源
2. CLI 参数作为单次运行覆盖
3. `.env` 仅用于运行时路径类覆盖

### 主配置文件

```text
config.json
```

较重要的配置块：

- `defaults`：默认邮箱服务、代理、CPA 目标选择
- `registration`：单次注册默认数量、是否自动上传、服务附加配置
- `workflow`：目标账号数量、校验策略、清理策略、CPA 自动同步、最大尝试次数
- `proxy_policy`：不同动作是否走代理
- `proxy_dynamic`：动态代理 API 配置
- `proxies`：配置文件中的代理池
- `email_services`：配置文件中的邮箱服务池
- `cpa_services`：配置文件中的 CPA 服务池

### `.env`

`.env` 不是主配置入口，主要用于覆盖配置文件路径和数据库地址。

支持的环境变量：

- `APP_CONFIG_PATH`
- `APP_DATABASE_URL`
- `DATABASE_URL`

示例见 [`.env.example`](./.env.example)。

## 项目结构

```text
.
├─ main.py                  # 根入口，转发到 src.main
├─ config.json              # 主配置文件
├─ Usage.md                 # 更完整的使用说明
├─ src/
│  ├─ cli/                  # argparse 命令定义与工作流编排
│  ├─ core/                 # 注册引擎、HTTP、OpenAI OAuth、上传逻辑
│  ├─ services/             # 邮箱服务实现
│  ├─ database/             # ORM、会话、CRUD、初始化
│  └─ config/               # 配置模型与常量
├─ data/                    # 运行期数据库目录
└─ logs/                    # 日志目录
```

## 关键命令说明

### `run`

按 `config.json` 中的工作流默认值执行完整流程，适合作为日常主入口。

```bash
python main.py run
python main.py run --target-count 20 --sync-cpa
```

### `register`

只做注册，不负责账号池补齐逻辑。

```bash
python main.py register
python main.py register --count 3
```

### `accounts`

用于账号库存管理。

```bash
python main.py accounts list
python main.py accounts validate
python main.py accounts delete-invalid
python main.py accounts ensure-target
```

### `cpa`

用于测试 CPA 连通性和上传账号。

```bash
python main.py cpa test
python main.py cpa upload --all --only-not-uploaded
```

### `services`

查看当前可用邮箱服务和代理来源，便于排查配置是否生效。

```bash
python main.py services list
python main.py services proxies
```

## 运行机制补充

- CLI 启动时会自动加载项目根目录下的 `.env`
- 运行时会确保 `data/` 和 `logs/` 目录存在
- 数据库会在启动阶段自动初始化
- 账号注册成功后可写入数据库，并记录邮箱服务、代理来源、token 等信息
- `run` 命令本质上复用了账号校验和单次注册逻辑，而不是单独复制一套流程

## 注意事项

- `config.json` 是默认行为的中心，建议优先改配置，不要把日常参数长期堆在命令行里
- 代理、邮箱服务和 CPA 服务既可以来自 `config.json`，也可能来自旧数据库记录，排查时建议先看 `services` 命令输出
- 账号数据、token、会话信息会落库，部署和使用时需要自行做好访问控制和密钥管理
- 本项目包含对外部服务的请求流程，实际使用前应确认目标环境、账号策略和相关合规要求

## 文档

- 完整使用说明见 [`Usage.md`](./Usage.md)
- 项目入口是 [`main.py`](./main.py)
- 包级入口是 [`src/main.py`](./src/main.py)
