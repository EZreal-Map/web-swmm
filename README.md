# Web-SWMM 项目

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
   - 支持**流量（INFLOW）**和**雨量（RAINGAGE）**两种时间序列模式。
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
│   │   ├── calculate.py            # 计算模块
│   │   ├── conduit.py              # 渠道管理模块
│   │   ├── junction.py             # 节点管理模块
│   │   ├── outfall.py              # 出口管理模块
│   │   ├── subcatchment.py         # 子汇水区管理模块
│   │   ├── timeseries.py           # 时间序列管理模块
│   │   └── transect.py             # 断面管理模块
│   ├── schemas/                    
│   │   ├── calculate.py            # 计算模块数据模型
│   │   ├── conduit.py              # 渠道数据模型
│   │   ├── junction.py             # 节点数据模型
│   │   ├── outfall.py              # 出口数据模型
│   │   ├── result.py               # 响应结果数据模型
│   │   ├── subcatchment.py         # 子汇水区数据模型
│   │   ├── timeseries.py           # 时间序列数据模型
│   │   └── transect.py             # 断面数据模型
│   ├── swmm/                       # SWMM 计算文件存储目录
│   │   ├── swmm_test.ini           # 测试配置文件
│   │   └── swmm_test.inp           # 测试输入文件
│   ├── utils/                      # 工具模块
│   │   ├── coordinate_converter.py # 坐标系转换工具
│   │   ├── logger.py			   # logger 配置
│   │   ├── swmm_constant.py        # SWMM 常量配置
│   │   └── utils.py                # 通用工具函数
│   ├── .env                        # .env 环境变量（已隐藏）
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
│   │   │   ├── CalculateDialog.vue # SWMM计算模块弹窗
│   │   │   ├── CesiumContainer.vue # Cesium三维地图组件
│   │   │   ├── ConduitDialog.vue   # 渠道弹窗
│   │   │   ├── JunctionDialog.vue  # 节点弹窗
│   │   │   ├── LeftMenu.vue        # 左侧菜单组件
│   │   │   ├── OutfallDialog.vue   # 出口弹窗
│   │   │   ├── SubcatchmentDialog.vue # 子汇水区弹窗
│   │   │   ├── TimeSeriesDialog.vue # 时间序列弹窗
│   │   │   └── TransectDialog.vue  # 断面弹窗
│   │   ├── router/                 # 路由配置
│   │   │   └── index.js
│   │   ├── stores/                 # 状态管理
│   │   │   └── viewer.js
│   │   ├── utils/                  # 工具模块
│   │   │   ├── convert.js          # 数据转换工具
│   │   │   ├── entity.js           # 实体操作工具
│   │   │   ├── request.js          # HTTP请求工具
│   │   │   └── useCesium.js        # Cesium相关工具
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
├── Dockerfile
└── README.md
```

## 4、启动项目

### 4-1. 本地启动

#### **后端启动**

1. 参考`.env.example`，复制生成一个`.env`环境变量文件

2. 确保已安装 Python 3.11 和 `Poetry`。

3. 安装依赖：
   ```bash
   poetry install
   ```

4. 激活虚拟环境：
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

4. **配置 docker 挂载文件**

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
