# 架构说明

## 总流程

```text
客户端
  -> FastAPI
  -> 文档上传接口
  -> 本地/MinIO 存储
  -> 后台摄取任务
  -> 文档解析
  -> 文本切块
  -> Embedding
  -> PostgreSQL + pgvector

客户端提问
  -> FastAPI
  -> 查询向量化
  -> 向量检索
  -> 关键词检索
  -> RRF 融合
  -> 重排
  -> Prompt 组装
  -> LLM
  -> 回答 + 引用
  -> 会话和引用入库
```

## 分层

- `api`：HTTP 接口，只做参数校验和调用服务。
- `services`：业务能力，包括解析、切块、向量化、检索和 LLM。
- `models`：数据库表结构。
- `schemas`：请求和响应结构。
- `rag`：RAG 主流程、Prompt 和引用。
- `eval`：评测指标和批量评测。

## 关键设计

### 租户隔离

所有查询都带 `tenant_id` 条件。当前 API 通过 `X-Tenant-Id` 请求头传递租户 ID，后续可以替换成登录态和 JWT。

### 向量维度

`document_chunks.embedding` 的维度来自 `EMBEDDING_DIM`。切换模型时必须保持一致，否则需要重建向量数据。

### 检索策略

- 向量检索负责语义相似。
- 关键词检索负责精确匹配。
- RRF 负责融合两路排名。
- 重排负责把最相关的块放到前面。

### 引用溯源

回答中的 `[1]`、`[2]` 对应检索结果编号。引用信息单独写入 `message_citations`，方便前端展示来源。

### 失败处理

文档摄取失败会写入 `error_message` 并把状态改为 `failed`。重新摄取会先清理旧的文档块。

## 后续演进

1. 把同步数据库访问替换成异步 SQLAlchemy。
2. 把后台任务替换成 Celery、RQ 或 Arq。
3. 接入 Rerank 模型。
4. 增加向量索引参数调优。
5. 增加权限过滤和文档级 ACL。
6. 增加 SSE 流式输出。
7. 增加观测和评测面板。

## 登录鉴权

- 用户密码使用 PBKDF2 哈希保存。
- 登录成功返回 HS256 签名的访问令牌。
- 业务接口通过 Bearer Token 获取当前用户和租户。
- 默认 AUTH_REQUIRED=false，生产和演示环境可以打开强制登录。

## SSE 流式输出

RAG 流式接口返回 text/event-stream，事件顺序如下：

1. citations：先返回引用来源，前端可以提前展示。
2. token：逐段返回模型输出。
3. done：返回会话 ID 和耗时。

前端使用 fetch + ReadableStream 解析 SSE，因为 EventSource 不支持 POST 请求。

## 真实评测集

内置 rag_benchmark.jsonl，每条用例包含：

- question：用户问题。
- expected_answer：参考回答。
- relevant_keywords：相关片段应该包含的关键词。

评测时先做检索，再根据关键词判断命中，最后统计 hit rate、MRR 和回答关键词覆盖率。
