# 交易资金流与风险分析 / Transaction Risk Explorer

本项目有两个网页入口和一份可复核的数据：

| 内容 | 位置 | 如何打开 |
| --- | --- | --- |
| Python 分析网页（正式项目） | `app.py`、`src/dashboard_data.py` | Windows 双击 `run_windows.bat`；Mac/Linux 运行 `bash run_mac_linux.sh` |
| 免安装交互网页（界面预览） | `web-preview/index.html` | 直接双击 HTML；内嵌自制演示数据 |
| 随包真实 IBM 合成数据 | `data/ibm_transactions.csv` | Python 网页默认读取，可直接用 Excel/Python 查看 |

**先看界面：**双击 `web-preview/index.html`。该页面可上传 CSV、筛选数据、调整规则并观察图表和预警名单的变化；它在浏览器中计算，默认的内嵌数据是自制演示数据。其在线版本是 https://transaction-risk-explorer.chasedugroup.chatgpt.site 。

**分析 IBM 数据：**使用 Python 3.11 或 3.12，双击 `run_windows.bat`（Windows），或执行 `bash run_mac_linux.sh`（Mac/Linux）。首次启动会安装依赖，然后在浏览器打开 `http://localhost:8501`。网页自动选择随包的 IBM 样本，也支持上传自己有权分析的 CSV。

## 数据范围与来源

`data/ibm_transactions.csv` 是 IBM AML-Data `HI-Small_Trans.csv` 的**原始前 250,000 行**，保留 11 列。它不是完整的 500 多万行文件；样本标签 1 有 26 行，交易大部分集中在 2022-09-01 的前 30 分钟。本包没有把演示数据伪装成 IBM 数据。准确的来源、哈希、字段、样本边界及数据许可见 `data/DATA_SOURCE.md`。IBM 官方仓库：https://github.com/IBM/AML-Data 。

如需原始完整文件，运行 `python scripts/download_full_ibm.py`，下载约 475 MB 到 `data/HI-Small_Trans.csv`。当前网页单次最多分析连续 250,000 行；检测到大文件时会提示只读取开头部分。因此，不应把网页基于片段的结果称作完整数据集结论。

## 网页能做什么

1. **数据检查**：映射时间、付款账户、收款账户、金额等列；剔除无效时间、账户、非正金额及完全重复记录；按币种分别分析，不把不同币种的金额相加。
2. **金融分析**：交易笔数和金额走势、金额分布、支付方式、前十收款账户资金集中度、银行间资金路径、账户汇入汇出与样本内净流入。走势可以切换分钟、小时、天。
3. **规则预警**：调整大额、高频、多来源汇入、快速转出、跨行和最终得分门槛；即时查看待复核工作量、规则命中与交易依据。若有 0/1 模拟标签，显示命中及遗漏；无标签则不显示这类指标。
4. **复核与导出**：按账户、金额、预警状态查交易，下载复核队列或筛选数据；SQL 页面可在当前数据上查询资金集中度、银行路径与审查工作量。

规则权重：大额、高频、多来源汇入、快速转出各 2 分，跨行 1 分。得分**不是犯罪概率**，预警是人工复核建议。该项目没有训练或部署 AI 决策模型。窗口分析只基于当前选中的数据；缩小时间或币种范围后，窗口起点与结果可能变化。

## CSV 要求

上传文件至少需要时间、付款账户、收款账户、正数金额四列，页面可以手动匹配。付款银行、收款银行、币种、支付方式、模拟 0/1 标签为可选列。IBM 列名自动匹配。上传上限为 250,000 行；更大文件请先截取一个连续时间段，不要随机抽样后再解读交易频率。独立的 HTML 预览上传上限为 25 MB，Python 网页更适合正式分析。

## 文件与检查

- `src/dashboard_data.py`：读取、清洗、资金行为与规则计分。
- `app.py`：中英双语 Streamlit 网页与图表。
- `sql/risk_queries.sql`：八条 SQL 分析查询。
- `scripts/download_full_ibm.py`：可选的完整 IBM 文件下载。
- `tests/test_dashboard_data.py`：核心规则、清洗与阈值检查。

运行 `python -m unittest discover -s tests` 检查核心计算。项目可公开展示，但请保留 `data/DATA_SOURCE.md` 中的 IBM 数据署名和许可说明。
