# 数据来源与范围 / Dataset provenance

随包文件 `ibm_transactions.csv` 是 IBM AML-Data 的 `HI-Small_Trans.csv` 中**前 250,000 条原始交易记录**，保留原有 11 个字段和标签，没有改造或补造交易。2026-09-28 从 IBM 仓库指向的 Kaggle 发布页下载文件前部连续字节，并截取完整 CSV 行。

- 提供者与来源：IBM AML-Data — https://github.com/IBM/AML-Data
- 分发地址：https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
- 原始文件：`HI-Small_Trans.csv`，约 475,664,283 字节；本包只含前 250,000 行。
- 随包 CSV SHA-256：`fcba302758f5dc2ae7534dbc8cd3530227a9d4a16afc9af27a7d4e6b3ea862c8`
- 随包标签：0 = 249,974；1 = 26。多数记录集中在 2022-09-01 的前 30 分钟，因此网页默认可以按分钟查看走势。
- 许可：IBM 说明该数据采用 CDLA-Sharing-1.0，见 https://cdla.dev/sharing-1-0/ 。保留 IBM 的提供者署名；数据的再次共享仍按该协议办理。

请勿把这一份 25 万行片段说成完整的 500 多万行数据集，也不要将该模拟标签解释为真实犯罪认定。图表与结论只覆盖本包样本。`toy_demo.csv` 是本项目另行生成的功能演示，与 IBM 无关。

## 字段 / Fields

| 原始列 | 用途 |
| --- | --- |
| Timestamp | 交易时间 |
| From Bank, Account | 付款银行与付款账户 |
| To Bank, Account.1 | 收款银行与收款账户；Pandas 为重复列名自动加 `.1` |
| Amount Received, Receiving Currency | 收款金额及币种（原始保留） |
| Amount Paid, Payment Currency | 付款金额及币种；当前图表按付款金额分析 |
| Payment Format | 支付方式 |
| Is Laundering | 模拟标签 0/1，仅作规则结果对照 |

运行 `python scripts/download_full_ibm.py` 可下载完整 `HI-Small_Trans.csv` 到 `data/`；文件约 475 MB。当前网页的单次分析上限是连续 250,000 行，完整文件默认先取开头片段并显示提示。完整文件用于后续分段扩展，当前成果请按随包 25 万行解释。
