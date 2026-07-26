# giffgaff eSIM 获取工具

一个轻量级的 giffgaff eSIM 二维码获取工具，支持通过 giffgaff 账号登录后获取账号内已有的可下载 eSIM，也提供申请新的 eSIM 二维码入口。

> 本项目适合个人本地使用或自托管使用。请只操作你本人拥有或已获授权的 giffgaff 账号。

## 功能

- 账号密码登录 giffgaff
- 支持 giffgaff 登录二次验证
- 支持邮箱验证码和短信验证码
- 获取账号中已有的 `DOWNLOADABLE` eSIM
- 自动生成 eSIM 二维码
- 显示完整 LPA 字符串
- 显示账号信息、手机号、会员 ID、SIM 状态、eSIM 数量
- 支持申请新的 eSIM 二维码
- 支持退出登录并清理本地会话
- 登录状态保存在浏览器本地 24 小时
- 前后端分离，结构简单，方便二次开发

## 技术栈

前端：

- Vue 3
- Vite
- Pinia
- Tailwind CSS
- qrcode
- axios

后端：

- Python 3.11+
- FastAPI
- httpx
- Redis
- Pydantic
- uvicorn

会话：

- 后端使用 Redis 保存临时登录会话
- 前端使用 `localStorage` 保存 24 小时本地登录状态
- 前端不保存 giffgaff 密码和验证码

## 项目结构

```text
giffgaff-esim-qr/
├─ backend/          # FastAPI 后端
│  ├─ app/
│  ├─ pyproject.toml
│  └─ .env.example
├─ frontend/         # Vue 前端
│  ├─ src/
│  ├─ package.json
│  └─ .env.example
└─ README.md
```

## 启动方式

当前项目没有内置 Docker 编排，默认使用本地 Python 虚拟环境和 Node.js 启动。Redis 需要提前准备好。

### 1. 启动 Redis

如果本机已经安装 Redis，确保它运行在：

```text
redis://localhost:6379/0
```

如果你本机没有 Redis，也可以只用 Docker 启动 Redis：

```powershell
docker run -d --name giffgaff-redis -p 6379:6379 redis:7
```

### 2. 启动后端

```powershell
cd backend

python -m venv .venv
.\.venv\Scripts\activate

pip install -e ".[dev]"
copy .env.example .env

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端地址：

```text
http://127.0.0.1:8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

接口文档：

```text
http://127.0.0.1:8000/api/docs
```

### 3. 启动前端

另开一个终端：

```powershell
cd frontend

npm install
copy .env.example .env

npm run dev
```

前端地址：

```text
http://127.0.0.1:5174
```

如果端口被占用，Vite 可能会自动换到其他端口，请以终端输出为准。

## 环境变量

后端 `backend/.env`：

```env
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
PUBLIC_BASE_URL=http://localhost:5173

REDIS_URL=redis://localhost:6379/0
SESSION_TTL_SECONDS=86400

RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_REQUESTS=60

GIFFGAFF_ID_BASE=https://id.giffgaff.com
GIFFGAFF_PUBLIC_API_BASE=https://publicapi.giffgaff.com
GIFFGAFF_WEB_BASE=https://www.giffgaff.com

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174
```

前端 `frontend/.env`：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 使用流程

1. 打开前端页面。
2. 输入 giffgaff 账号和密码。
3. 如果 giffgaff 要求二次验证，选择邮箱或短信发送验证码。
4. 输入收到的验证码完成登录。
5. 登录后页面会显示账号信息。
6. 点击“获取已有 eSIM 二维码”获取已有可下载 eSIM。
7. 如果账号里有多个 eSIM，选择目标 eSIM 后再获取二维码。
8. 页面会显示二维码、SSN 和 LPA 字符串。
9. 如果需要重新下发 eSIM，可以点击“申请新的 eSIM 二维码”。
10. 点击“退出登录”会清理后端 Redis 会话和浏览器本地登录状态。

## 新 eSIM 申请服务窗口

获取已有 eSIM 二维码不受服务窗口限制，通常全天可用，也不会触发换卡。

服务窗口主要针对“申请新的 eSIM / 重新下发 eSIM / 涉及换发”的操作。页面显示的建议操作时间已换算为中国时间：

```text
中国建议操作时间：11:30 至次日 04:30
英国时间：04:30 至 21:30
```

申请新的 eSIM 或涉及换发的操作，建议尽量在这个窗口内进行。

## 主要接口

账号登录：

```text
POST /api/account/login
```

发送登录验证码：

```text
POST /api/account/login/challenge
```

提交登录验证码：

```text
POST /api/account/login/mfa
```

获取已有 eSIM：

```text
POST /api/esim/fetch
```

获取指定 eSIM 的 LPA：

```text
POST /api/esim/download-token
```

申请新的 eSIM：

```text
POST /api/esim/reserve-new
```

发送 eSIM 操作验证码：

```text
POST /api/mfa/send
```

校验 eSIM 操作验证码：

```text
POST /api/mfa/verify
```

## 安全说明

- 本项目不会在前端保存 giffgaff 密码。
- 登录过程中的密码只用于后端向 giffgaff 发起本次登录请求。
- 如遇登录验证码，后端会在 Redis 临时会话中保存必要状态。
- 登录成功后，前端只保存本项目的 `sessionId`、账号展示信息和页面状态。
- 如果项目部署到公网，建议务必加 HTTPS、访问控制、日志脱敏和更严格的限流。
- 不建议把本项目作为公开多人服务直接暴露使用。

## 注意事项

- giffgaff 可能会拦截服务端账号密码登录请求。
- 验证码由 giffgaff 发送到账号绑定邮箱或手机号，不是通过 eSIM 卡发送。
- 获取已有 eSIM 通常不会触发换卡，也不受新 eSIM 申请服务窗口限制。
- 申请新的 eSIM 可能会触发 giffgaff 新 eSIM 下发流程，请确认当前号码确实需要重新下发。
- eSIM 通常只能安装到一个设备；如果要换手机，通常需要重新下发或重新获取可安装的 eSIM。

## 开发命令

后端语法检查：

```powershell
cd backend
python -m compileall app
```

前端构建：

```powershell
cd frontend
npm run build
```

## 开源声明

本项目仅用于学习、研究和个人自用场景。使用者需要自行承担账号安全、运营商规则变更、接口变更和 eSIM 操作风险。
