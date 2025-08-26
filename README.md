# [🌏 Web-SWMM 项目](https://www.bilibili.com/video/BV1p7eFz6EBj/)

## 1、项目介绍

Web-SWMM 项目旨在将 SWMM（Storm Water Management Model）的一部分功能搬到网页端，以便更直观地进行模型的操作和管理，为某些任务提供 SWMM 调用支持。

前端使用 **Vue** 和 **Cesium** 实现交互式界面和三维可视化，后端使用 **FastAPI** 和 **swmm-api** 提供高效的 API 服务和 SWMM 文件的操作能力。

---

## 2、实现功能

该项目实现了以下 SWMM 功能：

1. **节点管理**：

   - 增删改查节点。
   - 更新节点的坐标、入流信息及关联的时间序列。

2. **渠道管理**：

   - 增删改查渠道（管道）。
   - 更新渠道的断面信息及起点、终点节点。

3. **出口管理**：

   - 增删改查出口节点。
   - 更新出口的坐标和出流类型。

4. **子汇水区管理**：

   - **产流模型参数管理**：增删改查子汇水区，设置名称、雨量计、出水口、面积、不透水率、宽度和坡度参数。
   - **汇流模型参数管理**：管理不透水和透水子区的曼宁粗糙系数、凹陷储存量、径流流向和流向百分比。
   - **下渗模型参数管理**：管理霍顿下渗模型参数，包括最大入渗速率、最小入渗速率、衰减常数、干燥时间和最大入渗体积。
   - **边界数据管理**：编辑和保存子汇水区的多边形边界，支持 WGS84 和 UTM 坐标系之间的自动转换。
   - **数据一致性维护**：在子汇水区重命名时，自动更新关联的汇流、下渗和多边形数据的名称引用。

5. **时间序列管理**：

   - 增删改查时间序列。
   - 支持流量（INFLOW）和雨量（RAINGAGE）两种时间序列模式。
   - 获取时间序列的名称列表和详细信息。
   - 时间序列数据的导入和导出（JSONB 格式存储）。

6. **断面管理**：

   - 增删改查不规则断面。
   - 更新断面信息及其关联的渠道。

7. **计算模块**：
   - 获取和更新计算选项。
   - 运行 SWMM 模型并查询计算结果。
   - 解析计算错误日志，协助问题定位。

---

## 3、目录结构

```bash
web-swmm/
├── backend/                        # 后端代码
│   ├── apis/
│   │   ├── agent/                  # 智能体相关接口
│   │   │   └── chat.py             # 智能体对话接口
│   │   ├── calculate.py            # 计算模块
│   │   ├── conduit.py              # 渠道管理模块
│   │   ├── junction.py             # 节点管理模块
│   │   ├── outfall.py              # 出口管理模块
│   │   ├── subcatchment.py         # 子汇水区管理模块
│   │   ├── timeseries.py           # 时间序列管理模块
│   │   └── transect.py             # 断面管理模块
│   ├── schemas/
│   ├── tools/                      # 后端工具函数
│   │   ├── calculate.py            # 计算相关工具
│   │   ├── conduit.py              # 渠道相关工具
│   │   ├── junction.py             # 节点相关工具
│   │   ├── outfall.py              # 出口相关工具
│   │   ├── subcatchment.py         # 子汇水区相关工具
│   │   └── webgis.py               # GIS 相关工具
│   │   ├── calculate.py            # 计算模块数据模型
│   │   ├── conduit.py              # 渠道数据模型
│   │   ├── junction.py             # 节点数据模型
│   │   ├── outfall.py              # 出口数据模型
│   │   ├── result.py               # 响应结果数据模型
│   │   ├── subcatchment.py         # 子汇水区数据模型
│   │   ├── timeseries.py           # 时间序列数据模型
│   │   └── transect.py             # 断面数据模型
│   ├── swmm/                       # SWMM 计算文件存储目录
│   │   ├── swmm.inp                # 测试输入文件(已.gitignore)
│   │   └── swmm.inp.example        # 测试输入文件(示例)
│   ├── utils/                      # 工具模块
│   │   ├── coordinate_converter.py # 坐标系转换工具
│   │   ├── logger.py			   # logger 配置
│   │   ├── swmm_constant.py        # SWMM 常量配置
│   │   └── utils.py                # 通用工具函数
│   │   ├── websocket_manager.py    # websocket 管理工具
│   │   └── agent/                  # 智能体底层工具
│   │       ├── async_store_manager.py   # 异步存储管理
│   │       ├── graph_manager.py         # 智能体图管理
│   │       ├── llm_manager.py           # 大模型管理
│   │       ├── serial_tool_node.py      # 串行工具节点
│   │       └──  websocket_manager.py     # 智能体 websocket 管理
│   ├── .env                        # .env 环境变量(已.gitignore)
│   ├── .env.example                # .env 环境变量示例
│   ├── app.py                      # 应用入口
│   ├── config.py                   # 配置文件
│   ├── poetry.lock
│   └── pyproject.toml
├── frontend/                       # 前端代码
│   ├── public/
│   │   └── favicon.ico
│   ├── src/
│   │   ├── apis/                   # 前端 axios 请求模块
│   │   │   ├── calculate.js        # 计算模块API
│   │   │   ├── conduit.js          # 渠道API
│   │   │   ├── junction.js         # 节点API
│   │   │   ├── outfall.js          # 出口API
│   │   │   ├── subcatchment.js     # 子汇水区API
│   │   │   ├── timeseries.js       # 时间序列API
│   │   │   └── transect.js         # 断面API
│   │   ├── components/
│   │   │   ├── agent/                  # 智能体相关组件
│   │   │   │   ├── AgentChatDialog.vue # 智能体对话主窗口
│   │   │   │   ├── ChatInput.vue       # 智能体输入框
│   │   │   │   ├── ConfirmBoxUI.vue    # 智能体确认弹窗
│   │   │   │   ├── EchartsUI.vue       # 智能体图表组件
│   │   │   │   ├── MessageItem.vue     # 智能体消息项
│   │   │   │   └── MessageList.vue     # 智能体消息列表
│   │   │   ├── CalculateDialog.vue     # SWMM计算模块弹窗
│   │   │   ├── CesiumContainer.vue     # Cesium三维地图组件
│   │   │   ├── ConduitDialog.vue       # 渠道弹窗
│   │   │   ├── JunctionDialog.vue      # 节点弹窗
│   │   │   ├── LeftMenu.vue            # 左侧菜单组件
│   │   │   ├── OutfallDialog.vue       # 出口弹窗
│   │   │   ├── SubcatchmentDialog.vue  # 子汇水区弹窗
│   │   │   ├── TimeSeriesDialog.vue    # 时间序列弹窗
│   │   │   └── TransectDialog.vue      # 断面弹窗
│   │   ├── router/                 # 路由配置
│   │   │   └── index.js
│   │   ├── stores/                 # 状态管理
│   │   │   └── viewer.js
│   │   ├── utils/                  # 工具模块
│   │   │   ├── constant.js         # 常量定义
│   │   │   ├── convert.js          # 数据转换工具
│   │   │   ├── entity.js           # 实体操作工具
│   │   │   ├── request.js          # HTTP请求工具
│   │   │   ├── useCesium.js        # Cesium相关工具
│   │   │   └── wsURL.js            # websocket 地址工具
│   │   ├── tools/                  # 前端工具函数
│   │   │   ├── webgis.js           # GIS 相关工具
│   │   │   └── webui.js            # UI 相关工具
│   │   ├── views/
│   │   │   └── HomeView.vue
│   │   ├── App.vue
│   │   └── main.js
│   ├── .editorconfig
│   ├── .prettierrc.json
│   ├── eslint.config.js
│   ├── index.html
│   ├── jsconfig.json
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── vite.config.js
├── docker-volumes/                 # Docker挂载目录
│   ├── nginx/                      # Nginx配置目录
│   │   ├── html/                   # 前端静态文件目录
│   │   └── nginx.conf              # Nginx配置文件
│   └── swmm/                       # SWMM文件挂载目录
│       ├── Minjiang_with_conduit.ini
│       ├── Minjiang_with_conduit.inp
│       ├── swmm_test.ini
│       └── swmm_test.inp
├── docker-compose.yml
├── pg-docker-compose.yml           # 独立PostgreSQL服务的Compose文件
├── Dockerfile
└── README.md
```

## 4、启动项目

### 4-1. 本地启动

#### **后端启动**

1. 参考`.env.example`，复制生成一个`.env`环境变量文件

2. 参考`/backend/swmm/swmm.inp.example`,复制生成一个测试`swmm.inp`文件

3. 使用 docker 配置`PostgreSQL`数据库

   ```bash
   docker-compose -f pg-docker-compose.yml -p pg up
   ```

4. 确保已安装 Python 3.11 和 `Poetry`。

5. 安装依赖：

   ```bash
   poetry install
   ```

6. 激活虚拟环境：

   ```bash
   poetry shell
   ```

7. 启动 FastAPI 服务：
   ```bash
   python app.py
   ```

#### **前端启动**

1. 确保已安装 Node.js 和 pnpm。
2. 安装依赖：
   ```bash
   pnpm install
   ```
3. 启动开发服务器：
   ```bash
   pnpm dev
   ```

前端默认运行在 `http://localhost:5000`，后端运行在 `http://localhost:8080`。

---

### 4-2. 使用 Docker 部署

#### 步骤

1. **修改 backend `.env`**

   ```bash
   # 数据库配置（指向docker容器的postgres)
   DB_HOST=postgres
   DB_PORT=5432
   # 日志配置
   LOG_LEVEL=INFO
   ```

2. **修改 frontend `./frontend/utils/request.js`**

   ```js
   const baseURL = "/api"; // 反向代理（部署时使用）
   ```

3. **使用 Docker Compose 启动所有服务：**

   ```bash
      docker-compose up -d
   ```

4. **配置 docker 挂载文件**

   ```bash
   docker-volumes/
   ├── nginx/						 # 挂载 nginx 配置目录
   │   ├── html/                      # 前端静态文件目录
   │   │   ├── index.html             # 前端 build 之后的文件
   │   │   └── ...
   │   ├── nginx.conf                 # Nginx 配置文件
   ├── swmm/                          # 挂载 SWMM 文件目录
   │   └── swmm.inp                   # 挂载 SWMM 输入文件
   ```

   > nginx.conf

   ```nginx
   #user  root;
   worker_processes  1;
   events {
     worker_connections  1024;
   }
   http {
     include       mime.types;
     default_type  application/octet-stream;
     client_max_body_size 100M;  # 允许最多 100MB 的文件上传
     sendfile        on;
     keepalive_timeout  65;
     server {
         listen       80;
         server_name  localhost;
         location / {
             root   /usr/share/nginx/html;
             try_files $uri $uri/ /index.html last; # 解决刷新404问题
             index  index.html index.htm;
         }
         error_page   500 502 503 504  /50x.html;
         location = /50x.html {
             root   html;
         }

         # 配置后端接口反向代理
         location /api/ {
             proxy_pass http://fastapi:8080/;
             proxy_http_version 1.1;
             proxy_set_header Upgrade $http_upgrade;
             proxy_set_header Connection "upgrade";
             proxy_set_header Host $host;
         }
     }
   }
   ```
