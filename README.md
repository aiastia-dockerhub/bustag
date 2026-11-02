# Bustag - 基于机器学习的车牌自动推荐系统

<img src="./bustag/app/static/images/logo.png" width="300">

> Fork 自 [gxtrobot/bustag](https://github.com/gxtrobot/bustag)，进行了大量重构和功能增强。

Bustag 是一个自动车牌推荐系统。定时通过 [javbus-api](https://github.com/ovnrain/javbus-api) 爬取最新影片信息，用户对影片进行打标后训练 LightGBM 模型，模型可自动预测并推荐喜欢的影片，过滤大量不喜欢的内容。

## 与原版的主要区别

| 特性 | 原版 | 本 Fork |
|------|------|---------|
| 前端 | Bottle 模板 + jQuery | **Nuxt 3 (Vue 3) + Bootstrap 5** |
| 爬虫 | aspider 直爬 JavBus | **javbus-api 接口** |
| 模型 | KNN | **LightGBM 梯度提升树** |
| 特征 | 简单标签编码 | **分类编码 + 数值特征 + 交叉验证 + AUC 评估** |
| 影片类型 | 仅普通 | **有码 + 无码** |
| 部署 | 单容器 | **Docker Compose（含 javbus-api）** |
| 数据库 | SQLite | **SQLite / MySQL** |
| 图片 | 直接引用外链 | **图片代理 + 磁盘缓存** |
| 账号 | 无 | **密码登录（`BUSTAG_PASSWORD`），多设备共享服务端状态** |
| 云下载 | 仅 Aria2 浏览器直连 | **Aria2 + 115 云下载（服务端授权保活，多设备共享）** |

## 系统截图

- 推荐页面（模型自动预测喜欢的影片）
  ![](./docs/recommend.png)

- 打标页面（手动标记喜欢/不喜欢）
  ![](./docs/tagit.png)

- 本地文件页面
  ![](./docs/local.png)

- 番号上传页面
  ![](./docs/local_upload.png)

- 模型页面（训练、评估、重新推荐）
  ![](./docs/model.png)

- 数据导入页面
  ![](./docs/data.png)

## 快速开始

### Docker Compose 部署（推荐）

1. 创建项目目录和配置文件：

```bash
mkdir bustag && cd bustag
mkdir data
```

2. 在 `data/` 下创建 `config.ini`（[参考配置](./data/config.ini)），最简配置：

```ini
[download]
api_base_url = http://javbus-api:3000
count = 10
interval = 10800
movie_type = normal,uncensored
```

3. 创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  javbus-api:
    image: ovnrain/javbus-api
    container_name: javbus-api
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - TZ=Asia/Shanghai

  bustag:
    image: aiastia/bustag:vue
    container_name: bustag
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      - TZ=Asia/Shanghai
      - JAVBUS_API_URL=http://javbus-api:3000
    volumes:
      - ./data:/app/data
    depends_on:
      - javbus-api
```

4. 启动：

```bash
docker compose up -d
```

5. 访问 `http://localhost:8080`

### 从源码运行

需要 Python 3.11+ 和 Node.js 20+。

```bash
# 后端
pip install -r requirements.txt
python -c "from bustag.app.api import start_app; start_app()"

# 前端开发
cd frontend
npm install
npm run dev
```

## 使用流程

按以下顺序操作：

1. **打标** → 到「打标」页面，对影片标记喜欢/不喜欢，建议累积 300+ 条
2. **训练** → 到「模型」页面点击训练，生成 LightGBM 模型
3. **推荐** → 之后每次爬取新影片，系统自动调用模型预测并推荐
4. **确认** → 在「推荐」页面确认推荐结果，确认后转为打标数据
5. **循环** → 积累更多打标数据，重新训练，效果越来越好

## 账号系统（多设备访问）

设置环境变量 `BUSTAG_PASSWORD` 后，所有 `/api` 接口需密码登录访问：

```bash
# 本地运行
export BUSTAG_PASSWORD=your-password
python -c "from bustag.app.api import start_app; start_app()"

# Docker Compose（docker-compose.yml 中取消注释对应行）
# - BUSTAG_PASSWORD=your-password
```

- 不设置该变量时认证关闭（与原有无登录用法完全兼容）
- 会话 cookie 30 天有效，导航栏「🚪 登出」可主动登出（服务端即时失效）
- 连续 5 次密码错误将锁定该 IP 5 分钟
- **115 授权、AppID 等配置全部保存在服务端**，任何设备浏览器登录密码即可使用，无需每台设备重复扫码

## 115 云下载（推送磁力）

将影片的最大磁力链接直接推送到 115 网盘的离线下载（云下载），由 115 服务器完成下载和转存。

### 接入步骤

1. 登录 [115 开放平台](https://open.115.com/)（需先完成开发者入驻），在「应用管理」创建应用，拿到 **AppID**
2. bustag 导航栏点「☁️ 115」→ 填入 AppID（可选：填写保存目录 ID）→ 保存
3. 点「📱 扫码授权」，用 **115 客户端 App** 扫码确认
4. 之后在推荐/打标/搜索页面点「☁️ 115」按钮即可推送磁力

### 授权保活机制

| 事项 | 说明 |
|------|------|
| access_token 有效期 | 2 小时；临期自动刷新，另有定时任务每 30 分钟保活，长期不掉线 |
| refresh_token 有效期 | **1 年（刷新不延长）**，到期需重新扫码，设置弹框会显示到期日 |
| 授权失效 | 服务端标记并停止自动重试，UI 提示重新扫码 |
| 凭证存储 | 服务端 `data/115_token.json`（权限 0600、原子写、已加入 .gitignore），永不回传前端 |
| 刷新安全 | refresh_token 轮换原子保存；遵守官方 60 秒刷新限流；终态错误码立即停止重试 |

推送失败常见原因：`91006` 空间不足、`1000012` 云下载配额用完、`1000011` 单次超 115 个链接。

## 配置说明

配置文件 `data/config.ini`：

```ini
[database]
# 数据库类型：sqlite 或 mysql
type = sqlite
# MySQL 配置（type=mysql 时生效）
# host = localhost
# port = 3306
# name = bustag
# user = root
# password =

[download]
# javbus-api 服务地址
api_base_url = http://localhost:3000
# 认证 Token（可选）
auth_token =
# JavBus 网站地址（用于生成影片链接）
javbus_url = https://www.javbus.com
# 每次下载的页数（每页约 30 个影片）
count = 10
# 磁力链接筛选：exist=只返回有磁力的, all=全部
magnet = exist
# 影片类型：normal=有码, uncensored=无码, 逗号分隔可多选
movie_type = normal,uncensored
# 自动下载间隔（秒），10800=3小时
interval = 10800
# API 请求间隔（秒）
api_interval = 0.5
# 图片磁盘缓存
img_cache_enabled = true
```

## REST API 接口

所有接口返回 JSON，供前端调用。

### 影片相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/index` | GET | 推荐列表（模型预测结果），参数：`like`, `page`, `type` |
| `/api/tagit` | GET | 打标列表（未评分影片），参数：`like`, `page`, `type` |
| `/api/tag/<fanhao>` | POST | 打标操作，body：`{"rate_value": 1}` |
| `/api/correct/<fanhao>` | POST | 推荐反馈（确认/纠正推荐），body：`{"is_correct": true}` |
| `/api/search` | GET | 搜索影片，参数：`q`（番号）, `tag_id`, `page` |

### 本地文件

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/local` | GET | 本地文件列表 |
| `/api/local_fanhao` | GET/POST | 上传番号，body：`{"fanhao": "...", "tag_like": false, "movie_type": "mixed"}` |
| `/api/local_play/<id>` | GET | 播放本地文件 |

### 模型相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/model` | GET | 获取模型信息和评估指标 |
| `/api/do-training` | POST（兼容 GET） | 提交训练任务，返回 HTTP 202 + job；可选 `full_evaluation` |
| `/api/re-recommend` | POST | 提交清理旧推荐 + 重新推荐任务 |
| `/api/clear-recommend` | POST | 提交清理系统推荐任务（保留用户打标） |
| `/api/jobs` | GET | 最近 20 个后台任务及进度 |
| `/api/jobs/<id>` | GET | 单个后台任务状态、结果或错误 |
| `/api/tags` | GET | 搜索标签字典，支持 ETag；搜索分页不再重复返回字典 |

### 数据相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/load_db` | POST | 上传打标数据库文件导入 |
| `/api/img_proxy` | GET | 图片代理（带缓存），参数：`url` |
| `/api/version` | GET | 版本信息 |

### 番号格式说明

上传番号时支持以下格式（每行一个）：
- `ABC-123` — 自动识别为普通影片
- `ABC-123 | /path/to/file.mp4` — 番号 + 本地文件路径
- 通过 `movie_type` 参数指定类型：`normal`、`uncensored`、`mixed`（自动判断）

## data 目录结构

```
data/
├── config.ini          # 系统配置文件（必须）
├── bus.db              # SQLite 数据库（自动创建）
├── img_cache/          # 图片缓存目录（自动创建）
└── model/              # 模型文件（训练后自动创建）
    ├── model.pkl         # 模型、评分、编码器、特征名的原子快照
    ├── operation.lock    # 模型修改互斥锁
    └── worker.lock       # 后台进程互斥锁
```

## 技术栈

- **后端**：Python 3.11, Bottle, Peewee, APScheduler
- **前端**：Nuxt 3, Vue 3, Bootstrap 5
- **机器学习**：LightGBM, scikit-learn, pandas, numpy
- **爬虫**：javbus-api
- **部署**：Docker Compose, Nginx, Supervisor

## 性能与后台任务

训练、重新推荐、清理推荐和爬取在独立后台进程中串行执行。提交接口立即返回 `202 {"job": {...}}`，通过 `/api/jobs/<id>` 查询 `queued / running / succeeded / failed`、进度和结果。模型页面会自动轮询，离开页面后任务继续运行，重新打开可查看进度。训练默认采用早停，勾选「完整评估」才运行额外的五折交叉验证。

Docker 由 Supervisor 管理 worker；源码启动会自动拉起子进程，也可设置 `BUSTAG_EXTERNAL_WORKER=1` 并独立运行 `python -m bustag.app.worker`。中断的运行中任务在重启后标记失败，排队任务继续执行；完成记录保留七天。多个模型写入操作由跨进程锁保护，预测不会覆盖用户打标。

首次启动自动回填 `item.add_day` 并建立查询索引，保留原有按添加日期、发行日期和 ID 排序的语义。建议升级前备份数据库；大型数据库首次迁移需要额外时间与索引磁盘空间。旧版三文件模型继续可读，下次训练后使用单文件快照。

可在 `config.ini` 调整：

```ini
[download]
img_cache_enabled = true
# 可选：指定图片防盗链来源；默认传递影片来源页，无来源时使用 javbus_url
# img_referer = https://www.javbus.com/
img_cache_max_mb = 1024

[model]
predict_chunk_size = 1000
```

图片缓存上限包含原图和 480/960 像素 WebP 缩略图，后台约每分钟按最旧写入时间清理，流量突增期间可能暂时超过上限。预测批次限制为 1～5000，低内存设备可降低。保持原有爬虫限速，不额外提高上游并发。

源码运行可用 `BUSTAG_DATA_DIR` 指定数据目录；Nuxt 服务可通过运行时环境变量 `NUXT_API_BASE` 指定后端（默认 `http://127.0.0.1:8000`）。SSR 会转发登录 cookie，不共享用户页面缓存。

基准方法、结果和复现命令见 [性能验证记录](docs/performance.md)。

## 常见问题

**Q: 需要多少打标数据才能训练模型？**
A: 建议至少 300 条（喜欢 + 不喜欢），且必须同时包含两类。数据越多效果越好。

**Q: 模型效果如何？**
A: 使用 LightGBM 梯度提升树，配合概率阈值推荐，训练时会输出精确率、召回率、F1、AUC 等指标。可在模型页面查看。

**Q: 如何改变下载频率？**
A: 修改 `config.ini` 的 `interval` 参数，单位秒。

**Q: 如何同时爬取有码和无码？**
A: 设置 `movie_type = normal,uncensored`。

**Q: 推荐不准确怎么办？**
A: 在推荐页面确认/纠正推荐结果，积累更多打标数据后重新训练模型。

## 免责声明

本软件仅用于技术学习使用，禁止用于商业用途，使用本软件所造成的后果由使用者承担。