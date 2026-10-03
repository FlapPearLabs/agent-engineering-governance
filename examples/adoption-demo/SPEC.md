# DEMO-1：异步 producer 的真实入口合同（演练 fixture）

这是测试协调者批准的演练输入，不是待 Worker 自行批准的产品设计。

目标：真实入口 `run(transport)` 能通过 `FeedClient.fetch` 获取记录，并返回记录数量。

| 面 | 冻结合同 |
|---|---|
| producer | `FeedClient.fetch()` 是 async，await 传入的 async transport；每次调用一次 |
| consumer | `count_records(client)` 是 async，await `client.fetch()` 后计算数量 |
| entrypoint | `run(transport)` 构造真实 FeedClient，再 await consumer |
| 空结果 | 返回 0 |
| 失败 | transport 的原异常向上传递；不伪造空结果或成功 |
| 禁止 | 同步替身不能取代已冻结的 async producer；不新增重试、缓存、分页或网络依赖 |

验收需要入口到 consumer 到真实 producer 的测试，transport 可以使用 test-owned fake。仅 consumer 自造同步替身绿灯不能关闭本票。

本仓已有单票边界：producer 的返回形状由 FeedClient 拥有，consumer 负责等待并计数，transport 负责供数；无跨票共享写面或待批准架构选择。执行期若发现冻结合同之外的问题，记录而不扩 scope。
