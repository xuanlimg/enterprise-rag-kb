# Enterprise RAG KB · 企业知识库 RAG 后端服务

面向企业文档场景的检索增强生成（RAG）后端服务：支持多格式文档管理、混合检索、SSE 流式问答与引用溯源。

`Python 3.12` · `FastAPI` · `SQLAlchemy 2.0` · `PostgreSQL + pgvector` · `Docker Compose`

## 项目简介

企业内部文档散落在 PDF、Word、Excel、Markdown 等各种格式里，大模型又不知道私有数据。本项目把「文档入库 → 检索召回 → 生成带引用的回答」做成一条可评测、可复现的完整链路，重点解决四类工程问题：

1. **文档处理**：多格式解析、Token 级切块、元数据与页码保留、失败可重试；
2. **检索质量**：向量检索与关键词检索双路召回 + RRF 融合 + 重排；
3. **权限与数据建模**：多租户隔离、登录鉴权、会话与引用落库；
4. **接口工程化**：统一请求响应模型、SSE 流式输出、结构化日志、可评测回归。

## 功能特性

**文档管理**

- 支持 PDF、Word（docx）、Excel（xlsx）、Markdown、TXT 五类文档解析
- 近似 Token 切块（默认上限 500 Token、重叠 80 Token），保留页码、标题层级与元数据
- 文档状态机（pending → parsing → chunking → embedding → ready / failed）与失败原因记录
- 支持文档分页、按名称搜索、删除、失败重试与全量重新摄取

**检索与生成**

- 向量检索（pgvector）负责语义召回，关键词检索负责精确匹配，各召回 Top 30
- RRF（Reciprocal Rank Fusion）融合两路排名，再做启发式重排输出 Top 5
- 非流式问答 + SSE 流式问答（`citations` → `token` → `done` 事件）
- 回答以 `[1]` `[2]` 标注来源编号，引用明细单独写入 `message_citations` 表，可逐句溯源
- 检索为空时明确拒答"知识库中没有检索到相关内容"，而不是编答案

**模型可插拔**

- Embedding Provider：`fake`（哈希假向量）/ `openai` 兼容接口 / `fastembed` 本地模型
- LLM Provider：`echo`（离线回显）/ `openai` 兼容接口（DeepSeek、通义等）
- 大模型与向量模型可分开配置；封装维度迁移与一键重建向量，避免换模型后检索失效

**平台能力**

- 多租户数据隔离：所有查询强制携带 `tenant_id`
- 用户注册/登录：PBKDF2 加盐哈希存密码，HS256 签发访问令牌，Bearer Token 解析用户与租户
- Alembic 数据库迁移、Docker Compose 一键起库、内置最小前端（登录 / 上传 / 流式问答 / 评测趋势）
- 6 组 pytest 单测覆盖切块、评测指标、令牌与健康检查

## 整体流程

```text
文档入库
  上传 → 存储 → 解析 → 切块 → 向量化 → PostgreSQL + pgvector

问答
  提问 → 查询向量化 → 向量检索 ┐
                        ├─ RRF 融合 → 重排 → Prompt 组装 → LLM → 回答 + 引用 → 会话落库
                  关键词检索 ┘
```

## 技术栈

| 分类 | 选型 |
| --- | --- |
| 语言 / 框架 | Python 3.12、FastAPI、Pydantic v2 |
| 数据层 | PostgreSQL 16/17 + pgvector、SQLAlchemy 2.0、Alembic |
| 文档解析 | pypdf、python-docx、openpyxl |
| 检索 | pgvector 向量检索、关键词检索、RRF 融合、启发式重排 |
| 模型 | 本地 fastembed（BAAI/bge-small-zh-v1.5，512 维）+ OpenAI 兼容大模型接口 |
| 工程 | Docker Compose、SSE、pytest、Ruff、结构化日志 |

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
git clone https://github.com/xuanlimg/enterprise-rag-kb.git
cd enterprise-rag-kb
cp .env.example .env
docker compose up --build
```

打开 <http://127.0.0.1:8000/> 使用前端页面，<http://127.0.0.1:8000/docs> 查看 Swagger。

### 方式二：本地虚拟环境

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
pip install -e ".[dev]"

docker compose up -d db            # 只起数据库
uvicorn app.main:app --reload
```

默认配置使用 `fake` 向量与 `echo` 模型，**不需要任何 API Key 即可跑通全流程**；填写 Key 后自动切换到真实模型。

## 关键配置

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DATABASE_URL` | 数据库连接串 | `postgresql+psycopg://rag:rag@localhost:5432/rag` |
| `EMBEDDING_PROVIDER` | `fake` / `openai` / `fastembed` | `fake` |
| `EMBEDDING_DIM` | 向量维度，必须与模型一致 | `1536` |
| `LLM_PROVIDER` | `echo` / `openai` | `echo` |
| `CHUNK_MAX_TOKENS` | 切块上限 | `500` |
| `CHUNK_OVERLAP_TOKENS` | 切块重叠 | `80` |
| `RETRIEVAL_VECTOR_TOP_K` | 向量召回数量 | `30` |
| `RETRIEVAL_KEYWORD_TOP_K` | 关键词召回数量 | `30` |
| `RETRIEVAL_RERANK_TOP_K` | 重排后送入生成的数量 | `5` |
| `AUTH_REQUIRED` | 是否强制登录 | `false` |

> 使用本地中文向量模型的推荐配置：`EMBEDDING_PROVIDER=fastembed`、`EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5`、`EMBEDDING_DIM=512`、`EMBEDDING_QUERY_PREFIX=为这个句子生成表示以用于检索相关文章：`。
> 切换向量模型后维度会变，需重建 `document_chunks.embedding` 列并调用 `/api/v1/documents/reingest-all` 重新摄取。

## 主要接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 登录并签发访问令牌 |
| POST | `/api/v1/documents` | 上传文档并触发摄取 |
| GET | `/api/v1/documents?limit=&offset=&q=` | 文档分页与搜索 |
| POST | `/api/v1/documents/{id}/reingest` | 重新摄取单个文档 |
| POST | `/api/v1/documents/reingest-all` | 全量重新摄取（换模型后使用） |
| POST | `/api/v1/chat` | 非流式问答 |
| POST | `/api/v1/chat/stream` | SSE 流式问答（citations / token / done） |
| POST | `/api/v1/eval/runs` | 运行评测集 |
| GET | `/api/v1/eval/runs?limit=` | 评测历史与指标趋势 |
| GET | `/api/v1/health` | 健康检查 |

## 效果评测

内置真实评测集 `app/eval/datasets/rag_benchmark.jsonl`（10 条用例，覆盖可直接命中、需跨文档综合、知识库无答案等场景），指标定义：

- `hit_rate`：Top K 是否命中相关片段；
- `mrr`：第一个相关片段的排名倒数；
- `avg_answer_keyword_coverage`：回答覆盖评测关键词的比例。

**实测结果**（本地 `BAAI/bge-small-zh-v1.5` 向量 + DeepSeek 大模型）：

```json
{"hit_rate": 1.0, "mrr": 0.9, "avg_answer_keyword_coverage": 0.6333, "cases": 10}
```

## 目录结构

```text
enterprise-rag-kb/
├─ app/
│  ├─ api/v1/            # HTTP 接口：鉴权、文档、问答、评测、健康检查
│  ├─ core/              # 配置、日志、密码哈希、令牌
│  ├─ db/                # 数据库连接与会话
│  ├─ models/            # SQLAlchemy 模型（租户、用户、文档、分块、会话、评测）
│  ├─ schemas/           # Pydantic 请求响应模型
│  ├─ services/          # 解析、切块、向量化、检索、LLM provider
│  ├─ rag/               # RAG 主流程、Prompt、引用组装
│  ├─ eval/              # 评测集、指标、运行器
│  └─ static/            # 最小前端页面
├─ alembic/              # 数据库迁移
├─ docs/                 # 架构说明与设计笔记
├─ tests/                # 单元测试
├─ docker-compose.yml
└─ Dockerfile
```

## 测试

```bash
pytest
```

## 已知限制与后续计划

- [ ] 数据库访问目前为同步 SQLAlchemy，计划迁移到异步
- [ ] 后台摄取任务为进程内任务，计划接入 Celery / Arq
- [ ] 重排目前为启发式实现，计划接入专用 Rerank 模型
- [ ] 权限为租户级隔离，计划补充文档级 ACL
- [ ] 计划补充 p95 延迟与 Token 成本观测面板

## 免责声明

仓库内不包含任何真实企业文档；`data/` 目录下仅保留本地演示数据，已通过 `.gitignore` 排除。请勿将涉密文档提交到公开仓库。

## License

[MIT](LICENSE)
