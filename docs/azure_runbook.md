# Azure Runbook

## 目标

使用 Azure 容器化 GPU 资源运行 J-space observation 实验。

优先使用 Azure Container Apps Jobs / GPU T4 作为 batch experiment 环境。第一批任务为：

1. Phase 0.5 J-lens feasibility and saturation spike。
2. Phase 1 behavioral reasoning-depth gradient。

## 资源原则

- 不长期运行 GPU 服务。
- 不暴露无认证 Jupyter。
- 资源创建、运行、清理必须记录到 `docs/run_log.md`。
- 所有 Azure secrets 只能放在本地环境或安全 secret store，不能提交到 GitHub。

## 建议资源

- Resource group：`rg-jspace-observation`
- Region：优先 `southeastasia`
- GPU：T4
- Container Registry：自定义 ACR
- Workload：manual job / batch job

## Copilot 执行要求

每次创建或启动 Azure 资源后，必须追加记录：

```text
Date:
Command:
Resource:
Region:
SKU:
Run ID:
Start time:
Stop/Cleanup status:
Cost-control notes:
```

## 停止规则

如果遇到：

- GPU quota 不足；
- J-lens fitting 显存失败；
- 模型下载失败；
- 运行时间异常；

请停止，更新 `docs/decision_log.md`，等待下一步决定。
