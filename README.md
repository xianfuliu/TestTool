# TestTool Web Refactor

当前仓库保留原有 `PyQt5` 代码作为兼容业务层，同时新增一套按模块拆分的 `Django + Vue3 + MySQL` Web 平台骨架。

## 目录规划

### 后端

- `backend/test_platform`
  Django 主工程，负责全局配置、路由和运行入口。
- `backend/apps/common`
  公共层，只放 JSON 响应、CORS、中间桥接和旧代码适配能力。
- `backend/apps/authentication`
  登录、注册、会话、验证码。
- `backend/apps/test_data`
  身份证、营业执照等测试数据生成能力。
- `backend/apps/api_tool`
  产品配置与接口执行能力。
- `backend/apps/interface_auto`
  业务组、项目、接口模板、用例、调度、报告、全局工具、变量、环境。
- `backend/apps/tool_cards`
  工具卡片文件夹与卡片数据。
- `backend/apps/data_query`
  配置驱动的 SQL 查询能力。
- `backend/apps/api_management`
  旧 FastAPI 服务启停与路由目录管理。

### 前端

- `frontend/src/app`
  应用入口、路由、全局样式。
- `frontend/src/shared`
  共享布局、组件、API 客户端。
- `frontend/src/modules/auth`
  登录注册页面。
- `frontend/src/modules/test-data`
  测试数据页面。
- `frontend/src/modules/api-tool`
  接口工具页面。
- `frontend/src/modules/interface-auto`
  接口自动化总览页面。
- `frontend/src/modules/tool-cards`
  工具卡片页面。
- `frontend/src/modules/data-query`
  数据查询页面。
- `frontend/src/modules/api-management`
  API 管理页面。

## 迁移策略

1. Django 负责模块化路由、接口封装和 Web 运行时。
2. 旧 `src/core/services` 与 `src/utils` 中已稳定的业务逻辑继续复用，避免重写导致逻辑漂移。
3. Vue3 前端严格按模块目录组织，不在共享层混入业务代码。

## 启动方式

### 后端

```bash
pip install -r requirements.txt
python backend/manage.py runserver 0.0.0.0:8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认前端会请求 `http://127.0.0.1:8000`。
