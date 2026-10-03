# 隔离采用演练的起点

这是教学 fixture，**故意保留同步替身与真实异步 client 的错配**。不是生产组件，也不冒充知乎历史原始实现。演练借鉴的真实事故见 docs/design-history.md H03 / 知乎 PR #87。

将本目录复制到一个新目录并初始化独立 Git 仓后，按 [贯穿案例](https://github.com/FlapPearLabs/agent-engineering-governance/blob/main/docs/adoption-walkthrough.md)执行。该链接是在线导航；已固定治理版本时，从该版本读取 `docs/adoption-walkthrough.md`，离线用开工时提供的治理副本。不要在治理仓中提交 fixture 的练习修复。复制时同时保留治理仓的 LICENSE。

```bash
python3 -m unittest discover -s tests -v
python3 app.py
```

起点预期：一个同步替身测试通过，真实 entrypoint 因缺少 await 失败并产生 coroutine 警告。这组预期不是验收 PASS；任务是先用生产形状反例复现，再修复它。

任务合同：SPEC.md。治理采用与演练范围：AGENTS.md。现有起点没有项目状态索引，由接管 Agent 按既有仓 lazy adoption 初始化。
