# 后端组周报 — 2026 年第 17 周（04-20 ~ 04-24）

## 本周重点事项

### 1. 支付中心迁移

支付中心已从旧集群（IDC-A）迁移至新集群（IDC-B），API 网关路由已切换。迁移后观察到连接池偶发超时，初步怀疑与 Hikari 配置有关。

旧集群连接池配置：Hikari 4.x，connectionTimeout=30s，maximumPoolSize=20。
新集群连接池配置：Hikari 5.0.10，connectionTimeout=10s（默认值），maximumPoolSize=20。

需要确认 Hikari 从 4.x 升级到 5.x 后 connectionTimeout 的默认值变更是否与超时相关。

—— 张三（后端组）

### 2. 连接池超时排查

支付中心迁移后，赵六持续排查连接池超时问题。本周进展：

- 4/20：发现 Hikari 5.x connectionTimeout 默认值从 30s 变为 10s
- 4/21：临时将 connectionTimeout 调回 30s，超时频率从 15% 降至 3%
- 4/22：定位根因——Hikari 5.0.10 存在一个与 PostgreSQL 驱动的兼容性 bug（#1234），在特定网络延迟下连接验证阶段会超时
- 4/23：测试 Hikari 5.0.14 候选版本，问题修复
- 4/24：生产环境升级到 5.0.14，connectionTimeout 最终调整为 30s，超时问题已解决

数据库端 wait_timeout 也曾被列为备选根因，已于 4/22 排除（确认 MySQL wait_timeout 为 8 小时，远大于连接池超时时间）。

—— 赵六（SRE）

### 3. Redis 集群迁移计划

李四提交了 Redis 迁移方案初稿：

- 当前：Redis Sentinel 模式（3 主 3 从），数据量约 120GB
- 目标：Redis Cluster 模式，按 slot 分片
- 迁移窗口：5 月中旬
- 风险点：
  - 水平扩展能力提升，但运维复杂度增加
  - 某些多 key 命令在 Cluster 模式下不可用
  - 客户端需要支持 Cluster 协议重定向

架构组倾向于 Redis Cluster（水平扩展场景），但运维组认为 Sentinel 运维更简单，当前规模也不需要分片。待 CTO 决策。

—— 李四（基础架构组）

### 4. traceId 全链路追踪需求

产品组要求在下个迭代支持 traceId 贯穿 API 网关 → 后端服务 → 数据库查询。技术选型尚未完成，初步方案：

- 接入层：Nginx 生成或透传 X-Trace-Id
- 后端服务：通过 SLF4J MDC 传递
- 数据库：通过 SQL 注释注入 traceId（需 DBA 评估性能影响）

—— 王五（架构组）

### 5. 风险与阻塞

| 事项 | 风险等级 | 状态 | 负责人 |
|------|----------|------|--------|
| UAT 环境 SSL 证书 5 月 1 日到期 | 高 | 已申请新证书，等待 CA 签发 | 赵六 |
| 支付中心迁移后性能回归 | 中 | 监控中，连接池超时已基本解决 | 张三 |
| Redis 迁移方案决策延迟 | 低 | 等待 CTO 确认 | 李四 |

### 6. 数据归档

- 去年 Q3（2025 年 9 月）支付中心迁移前做过一轮性能基准测试，对比数据已归档至内部 Wiki（链接：wiki.internal/payment-benchmark-2025-q3）

---

_周报整理：张三 | 审核：CTO | 归档日期：2026-04-24_
