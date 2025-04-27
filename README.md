# Web-SWMM 项目

## 1、项目介绍

Web-SWMM 项目旨在将 SWMM（Storm Water Management Model）的一部分功能搬到网页端，以便更直观地进行模型的操作和管理，为某些任务提供SWMM调用支持。  

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
4. **时间序列管理**：
   - 增删改查时间序列。
   - 获取时间序列的名称列表和详细信息。
5. **断面管理**：
   - 增删改查不规则断面。
   - 更新断面信息及其关联的渠道。
6. **计算模块**：
   - 获取和更新计算选项。
   - 运行 SWMM 模型并查询计算结果。

---

## 3、目录结构

```
web-swmm/
├── backend/                        # 后端代码
│   ├── apis/                       # API 路由模块
│   │   ├── calculate.py            # 计算模块
│   │   ├── conduit.py              # 渠道管理模块
│   │   ├── junction.py             # 节点管理模块
│   │   ├── outfall.py              # 出口管理模块
│   │   ├── timeseries.py           # 时间序列管理模块
│   │   └── transect.py             # 断面管理模块
│   ├── schemas/                    # 数据模型定义
│   │   ├── calculate.py
│   │   ├── conduit.py
│   │   ├── junction.py
│   │   ├── outfall.py
│   │   ├── result.py
│   │   ├── timeseries.py
│   │   └── transect.py
│   ├── swmm/                       # SWMM 计算文件存储目录
│   │   ├── swmm_test.ini
│   │   └── swmm_test.inp
│   ├── utils/                      # 工具模块
│   │   ├── coordinate_converter.py
│   │   └── swmm_constant.py
│   ├── app.py                      # 应用入口
│   ├── config.py                   # 配置文件
│   ├── poetry.lock                 # Poetry 锁文件
│   └── pyproject.toml              # Poetry 配置文件
├── frontend/                       # 前端代码
│   ├── src/                        # Vue 源代码
│   │   ├── apis/                   # 前端 axios 请求模块
│   │   │   ├── calculate.js
│   │   │   ├── conduit.js
│   │   │   ├── junction.js
│   │   │   ├── outfall.js
│   │   │   ├── timeseries.js
│   │   │   └── transect.js
│   │   ├── components/             # Vue 组件
│   │   │   ├── CalculateDialog.vue # SWMM计算模块弹窗
│   │   │   ├── CesiumContainer.vue # Cesium组件
│   │   │   ├── ConduitDialog.vue   # 渠道弹窗
│   │   │   ├── JunctionDialog.vue  # 节点弹窗
│   │   │   ├── LeftMenu.vue        # 左菜单
│   │   │   ├── OutfallDialog.vue   # 出口弹窗
│   │   │   ├── TimeSeriesDialog.vue # 时间序列弹窗
│   │   │   └── TransectDialog.vue  # 断面弹窗
│   │   ├── router/                 # 路由配置
│   │   │   └── index.js
│   │   ├── stores/                 # 状态管理
│   │   │   └── viewer.js
│   │   ├── utils/                  # 工具模块
│   │   │   ├── convert.js
│   │   │   ├── entity.js
│   │   │   ├── request.js
│   │   │   └── useCesium.js
│   │   ├── views/                  # 页面视图
│   │   │   └── HomeView.vue
├── docker-compose.yml              # Docker Compose 配置文件
├── Dockerfile                      # Docker 镜像构建文件
├── README.md                       # 项目说明文件
```
## 4、启动项目

### 4-1. 本地启动

#### **后端启动**
1. 确保已安装 Python 3.11 和 `Poetry`。
2. 安装依赖：
   ```bash
   poetry install
   ```
3. 激活虚拟环境：
   ```bash
   poetry shell
   ```
4. 启动 FastAPI 服务：
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

前端默认运行在 `http://localhost:5173`，后端运行在 `http://localhost:8080`。

---

### 4-2. 使用 Docker 部署

#### 步骤

1. **确保已安装 Docker 和 Docker Compose。**

2. **构建后端镜像：**

   ```bash
   docker build -t web-swmm .
   ```

   > 这里 `.` 是 Dockerfile 所在目录，`web-swmm` 是你给镜像取的名字。

3. **使用 Docker Compose 启动所有服务：**

    ```bash
       docker-compose up -d
    ```


4. **配置docker挂载文件**


   ```
   docker-volumes/
   ├── nginx/						 # 挂载 nginx 配置目录
   │   ├── html/                      # 前端静态文件目录
   │   │   ├── index.html             # 前端 build 之后的文件        
   │   │   └── ...             
   │   ├── nginx.conf                 # Nginx 配置文件
   ├── swmm/                          # 挂载 SWMM 文件目录
   │   ├── swmm_test.ini              # 挂载 SWMM 输入文件
   │   └── swmm_test.inp              # 挂载 SWMM 输入文件
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
         }
     }
   }
   ```