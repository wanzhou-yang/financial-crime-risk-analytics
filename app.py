"""Bilingual transaction and money-flow dashboard."""
from io import BytesIO
from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard_data import FIELDS, REQUIRED, OPTIONAL, Rules, financial_summary, normalize, read_csv, review_metrics, score_transactions

ROOT = Path(__file__).resolve().parent
IBM_FILE = next((p for p in [ROOT / "data" / x for x in ("HI-Small_Trans.csv", "LI-Small_Trans.csv", "ibm_transactions.csv")] if p.exists()), None)
DEMO_FILE = ROOT / "data" / "toy_demo.csv"
PAGES = ["概览 / Overview", "资金流 / Money flows", "预警分析 / Review", "交易明细 / Transactions", "SQL 查询 / SQL"]

st.set_page_config(page_title="交易资金流与风险分析 | Transaction Risk", page_icon="◈", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
html,body,[class*=st-],button,input{font-family:'DM Sans','Noto Sans SC',sans-serif}
.stApp{background:#f6f8fa;color:#172d39}section[data-testid="stSidebar"]{background:#eaf1f4;border-right:1px solid #d5e1e7}
.block-container{padding-top:1.8rem;max-width:1450px}
.hero{background:linear-gradient(112deg,#102c3e,#195568);padding:28px 34px;border-radius:18px;color:white;margin-bottom:24px}
.hero small{font-size:.72rem;letter-spacing:.17em;text-transform:uppercase;color:#91d4d6;font-weight:700}
.hero h1{font-size:2.05rem;margin:8px 0 7px;line-height:1.25;color:white}.hero p{font-size:.98rem;color:#d6e5e9;margin:0}
.section-title{font-size:1.45rem;font-weight:700;color:#163848;margin:16px 0 3px}
.small-sub{color:#637b87;font-size:.88rem;margin-bottom:15px}
.insight{border-left:4px solid #2e92a2;background:#e9f5f5;border-radius:0 12px 12px 0;padding:12px 18px;margin:10px 0;color:#173b46}
div[data-testid="stMetric"]{background:white;border:1px solid #e0e8eb;padding:14px 18px;border-radius:12px}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner="读取交易数据 / Loading transactions…")
def load_path(path, stamp):
    frame = read_csv(path, allow_prefix=True)
    return frame, bool(frame.attrs.get("prefix_limited"))


@st.cache_data(show_spinner="解析上传文件 / Parsing CSV…")
def load_bytes(blob):
    return read_csv(BytesIO(blob)), False


@st.cache_data(show_spinner="计算交易模式 / Computing patterns…")
def compute(df, amount, window, freq, fanin, hours, ratio, threshold):
    return score_transactions(df, Rules(amount, window, freq, fanin, hours, ratio, threshold))


def section(main, sub):
    st.markdown(f'<div class="section-title">{main}</div><div class="small-sub">{sub}</div>', unsafe_allow_html=True)


def plot(fig, key):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#284756"), margin=dict(l=12, r=12, t=42, b=14), height=345,
                      colorway=["#227d92", "#69bdb4", "#f1ad66", "#dd7063"])
    st.plotly_chart(fig, width="stretch", key=key)


st.markdown('<div class="hero"><small>Financial transaction analytics / 金融交易分析</small>'
            '<h1>交易资金流与风险分析<br>Transaction Risk Explorer</h1>'
            '<p>选择数据、查看资金行为、调整审查规则。预警用于辅助人工核查，不等于犯罪认定。<br>'
            'Explore money flows, adjust review rules, and inspect the underlying transactions.</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 数据 / Data")
    sources = ["IBM 合成数据 / IBM synthetic", "上传 CSV / Upload CSV", "演示样本 / Demo"]
    source = st.radio("数据来源 / Source", sources, index=0 if IBM_FILE else 2)
    if source == sources[1]:
        uploaded = st.file_uploader("选择交易 CSV / Choose transaction CSV", type=["csv"])
        if uploaded is None:
            st.info("上传 CSV 后即可匹配列并分析。/ Upload a CSV to begin.")
            st.stop()
        try:
            raw, limited = load_bytes(uploaded.getvalue())
        except Exception as exc:
            st.error(str(exc))
            st.stop()
        source_label = uploaded.name + " · 用户上传 / User upload"
    elif source == sources[0]:
        if IBM_FILE is None:
            st.warning("本地尚无 IBM CSV。请把 HI-Small_Trans.csv 放进 data 文件夹，或上传文件。演示样本可先预览页面。")
            st.markdown("[IBM 数据来源 / Dataset source](https://github.com/IBM/AML-Data)")
            st.stop()
        raw, limited = load_path(str(IBM_FILE), IBM_FILE.stat().st_mtime_ns)
        source_label = f"IBM AML-Data · {IBM_FILE.name}"
    else:
        raw, limited = load_path(str(DEMO_FILE), DEMO_FILE.stat().st_mtime_ns)
        source_label = "演示样本 / Toy demo — 非 IBM 数据 / NOT IBM"
    st.caption(f"当前 / Active: {source_label}")
    if limited:
        st.warning("仅分析文件开头连续 250,000 行 / First 250,000 consecutive rows only; not the whole file.")
    if source == sources[2]:
        st.info("自制演示交易，仅用于体验功能，不作为 IBM 分析结果。/ Toy data for interface preview.")

    with st.expander("字段匹配 / Map columns", expanded=source == sources[1]):
        st.caption("必要：时间、付款账户、收款账户、金额。其他列可选。/ Time, sender, receiver and amount are required.")
        labels = {"time":"时间 / Time", "sender":"付款账户 / Sender", "receiver":"收款账户 / Receiver",
                  "amount":"金额 / Amount", "from_bank":"付款银行 / From bank", "to_bank":"收款银行 / To bank",
                  "currency":"币种 / Currency", "method":"支付方式 / Method", "label":"模拟标签 / Label (0/1)"}
        mapping = {}
        for key in (*REQUIRED, *OPTIONAL):
            candidate = FIELDS[key] if FIELDS[key] in raw.columns else None
            choices = ["— 请选择 / Select" if key in REQUIRED else "— 不使用 / None"] + list(raw.columns)
            value = st.selectbox(labels[key], choices, index=choices.index(candidate) if candidate else 0, key="map_" + key)
            mapping[key] = value if value in raw.columns else None
    try:
        data, quality = normalize(raw, mapping)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    currencies = sorted(data["currency"].unique().tolist())
    most_common = data["currency"].value_counts().idxmax()
    currency = st.selectbox("币种 / Currency", currencies, index=currencies.index(most_common))
    data = data[data["currency"] == currency].copy()
    low, high = data["time"].min().date(), data["time"].max().date()
    dates = st.date_input("日期 / Date range", (low, high), min_value=low, max_value=high)
    if len(dates) != 2:
        st.info("请选择起止日期 / Select both dates.")
        st.stop()
    data = data[(data["time"].dt.date >= dates[0]) & (data["time"].dt.date <= dates[1])].copy()
    if data.empty:
        st.warning("当前筛选没有交易 / No transactions in this range.")
        st.stop()
    st.markdown("### 规则 / Rules")
    st.caption("当前筛选范围内重新计算 / Recomputed within the selected slice")
    default_amount = max(1., float(data["amount"].quantile(.9)))
    amount = st.number_input("大额交易门槛 / Large amount", min_value=.01, value=round(default_amount, 2), step=max(1., round(default_amount / 10, 2)))
    window = st.slider("观察窗口（小时）/ Window", 1, 168, 24)
    freq = st.slider("同账户交易次数 / Sender frequency", 2, 20, 5)
    fanin = st.slider("不同汇入账户数 / Distinct senders", 2, 20, 4)
    hours = st.slider("转入后转出时限（小时）/ Outflow window", 1, 168, 24)
    ratio = st.slider("近期入账覆盖转出比例 / Inflow coverage", .1, 2.0, .8, .1)
    threshold = st.slider("预警分数门槛 / Alert score threshold", 1, 9, 4)
    page = st.radio("页面 / Explore", PAGES, label_visibility="collapsed")

d = compute(data, amount, window, freq, fanin, hours, ratio, threshold)
alerts = d[d["alert"]]
st.caption(f"{source_label} · {len(d):,} transactions · {dates[0]} – {dates[1]} · {currency}")

if page == PAGES[0]:
    section("从交易到结论 / From transactions to insight", "先看规模和资金分布，再检查账户关系与预警依据。/ Start with activity, then investigate flows and alerts.")
    a, b, c, e = st.columns(4)
    a.metric("交易笔数 / Transactions", f"{len(d):,}")
    b.metric("交易总额 / Volume", f"{d['amount'].sum():,.0f} {currency}")
    c.metric("金额中位数 / Median", f"{d['amount'].median():,.0f} {currency}")
    e.metric("需复核 / Alerts", f"{len(alerts):,}", f"{len(alerts)/len(d):.1%} of transactions", delta_color="off")
    default_bucket = "分钟 / Minute" if (d["time"].dt.date.value_counts().max() / len(d) > .95) else "天 / Day"
    bucket = st.selectbox("走势时间粒度 / Timeline interval", ["分钟 / Minute", "小时 / Hour", "天 / Day"], index=["分钟 / Minute", "小时 / Hour", "天 / Day"].index(default_bucket))
    interval = {"分钟 / Minute": "min", "小时 / Hour": "h", "天 / Day": "D"}[bucket]
    daily = d.groupby(d["time"].dt.floor(interval)).agg(count=("row_id", "size"), volume=("amount", "sum")).reset_index(names="date")
    left, right = st.columns(2)
    with left:
        plot(px.line(daily, x="date", y="count", markers=True, title="交易笔数走势 / Transaction count over time"), "daily-count")
    with right:
        plot(px.line(daily, x="date", y="volume", markers=True, title=f"交易金额走势 / Volume over time · {currency}"), "daily-volume")
    left, right = st.columns(2)
    with left:
        plot(px.histogram(d, x="amount", nbins=30, title=f"金额分布 / Transaction amounts · {currency}"), "amounts")
    with right:
        methods = d.groupby("method", as_index=False).agg(count=("row_id", "size"))
        plot(px.bar(methods.sort_values("count"), x="count", y="method", orientation="h", title="支付方式 / Payment methods"), "methods")
    s = financial_summary(d)
    st.markdown(f'<div class="insight"><b>资金集中度 / Concentration</b>：前 10 个收款账户收到 {s["top10_share"]:.1%} 的所选币种交易金额。'
                f' 跨行交易占 {s["cross_bank_share"]:.1%}；最密集的日期为 {s["peak_day"]}。'
                f'<br>Top 10 recipients received {s["top10_share"]:.1%} of selected-currency volume; cross-bank share was {s["cross_bank_share"]:.1%}. Interpret these patterns in business context.</div>', unsafe_allow_html=True)

elif page == PAGES[1]:
    section("钱流向哪里 / Where money moves", "按收款账户和银行路径分析；净流入只是样本内交易差额，不是实际余额。")
    recipients = d.groupby("receiver_key").agg(amount=("amount", "sum"), count=("row_id", "size"), senders=("sender_key", "nunique")).sort_values("amount", ascending=False).head(15).reset_index()
    routes = d.groupby(["from_bank", "to_bank"], as_index=False).agg(amount=("amount", "sum"), count=("row_id", "size")).sort_values("amount", ascending=False).head(15)
    routes["route"] = routes["from_bank"] + " → " + routes["to_bank"]
    left, right = st.columns(2)
    with left:
        plot(px.bar(recipients.sort_values("amount"), x="amount", y="receiver_key", orientation="h", hover_data=["count", "senders"], title=f"前 15 个收款账户 / Top recipients · {currency}"), "recipients")
    with right:
        plot(px.bar(routes.sort_values("amount"), x="amount", y="route", orientation="h", hover_data=["count"], title="前 15 条银行路径 / Top bank routes"), "routes")
    inbound = d.groupby("receiver_key")["amount"].sum()
    outbound = d.groupby("sender_key")["amount"].sum()
    accounts = pd.concat([inbound.rename("inflow"), outbound.rename("outflow")], axis=1).fillna(0)
    accounts["net_inflow"] = accounts["inflow"] - accounts["outflow"]
    section("账户资金收支 / Account flows", "搜索账户查看所选期间的汇入、汇出和交易。/ Search an account to inspect its flows.")
    needle = st.text_input("搜索银行或账户 / Search bank or account")
    visible = accounts[accounts.index.str.contains(needle, case=False, regex=False)] if needle else accounts
    st.dataframe(visible.sort_values("inflow", ascending=False).head(100).style.format("{:,.2f}"), width="stretch")
    if needle:
        matched = d[d["sender_key"].str.contains(needle, case=False, regex=False) | d["receiver_key"].str.contains(needle, case=False, regex=False)]
        st.caption(f"相关交易 / Related transactions: {len(matched):,}")
        st.dataframe(matched[["time", "sender_key", "receiver_key", "amount", "method", "score"]].head(100), width="stretch", hide_index=True)

elif page == PAGES[2]:
    section("预警为何出现 / Why alerts appear", "五条可调规则给交易计分；达到门槛后进入人工复核队列。得分不是犯罪概率。")
    a, b, c = st.columns(3)
    a.metric("待复核 / Review queue", f"{len(alerts):,}")
    b.metric("预警率 / Alert rate", f"{len(alerts)/len(d):.1%}")
    c.metric("规则命中总数 / Rule hits", f"{int(d[['high_amount','high_frequency','fan_in','rapid_outflow','cross_bank']].sum().sum()):,}")
    st.caption("权重 / Weights: 大额 2 · 高频 2 · 多来源汇入 2 · 快速转出 2 · 跨行 1。交易可同时满足多条。")
    labels = {"high_amount":"大额 / Large amount", "high_frequency":"高频 / Frequent sender", "fan_in":"多来源 / Fan-in", "rapid_outflow":"快速转出 / Rapid outflow", "cross_bank":"跨行 / Cross-bank"}
    hits = pd.DataFrame({"rule":list(labels.values()), "count":[int(d[k].sum()) for k in labels]})
    left, right = st.columns(2)
    with left:
        plot(px.bar(hits.sort_values("count"), x="count", y="rule", orientation="h", title="各规则命中笔数 / Rule hits"), "hits")
    with right:
        distribution = d["score"].value_counts().sort_index().rename_axis("score").reset_index(name="count")
        fig = px.bar(distribution, x="score", y="count", title="交易得分分布 / Score distribution")
        fig.add_vline(x=threshold - .5, line_dash="dash", line_color="#dd7063")
        plot(fig, "scores")
    metrics = review_metrics(d)
    if metrics:
        st.markdown("#### 对照模拟标签 / Against simulated labels")
        st.caption("只在文件有 0/1 标签时计算；仅反映当前样本与模拟标签的重合，不代表真实世界的识别能力。")
        cols = st.columns(4)
        cols[0].metric("命中标签 / TP", metrics["tp"])
        cols[1].metric("非标签预警 / FP", metrics["fp"])
        cols[2].metric("遗漏标签 / FN", metrics["fn"])
        cols[3].metric("召回率 / Recall", f'{metrics["recall"]:.1%}')
        st.caption(f'精确率 / Precision: {metrics["precision"]:.1%}。')
    else:
        st.info("数据没有模拟标签，因此不显示准确率、漏报或误报。/ No labels; classification metrics are unavailable.")
    if len(alerts):
        table = alerts.sort_values(["score", "amount"], ascending=False)[["time", "sender_key", "receiver_key", "amount", "score", *labels.keys(), "label"]]
        st.markdown("#### 人工复核队列 / Review queue")
        st.dataframe(table.head(500), width="stretch", hide_index=True)
        st.download_button("下载当前预警 / Download alerts CSV", table.to_csv(index=False).encode("utf-8-sig"), "review_queue.csv", "text/csv")
    else:
        st.info("当前门槛下没有预警。降低分数门槛即可比较工作量。/ No alerts at this threshold.")

elif page == PAGES[3]:
    section("查看交易 / Inspect transactions", "筛选账户、金额和预警状态；下载包含全部匹配记录。")
    a, b, c = st.columns([2, 1, 1])
    query = a.text_input("账户搜索 / Account search")
    minimum = b.number_input("最低金额 / Minimum amount", min_value=0.0, value=0.0)
    status = c.selectbox("状态 / Status", ["全部 / All", "仅预警 / Alerts", "未预警 / Others"])
    view = d[d["amount"] >= minimum]
    if query:
        view = view[view["sender_key"].str.contains(query, case=False, regex=False) | view["receiver_key"].str.contains(query, case=False, regex=False)]
    if status == "仅预警 / Alerts":
        view = view[view["alert"]]
    elif status == "未预警 / Others":
        view = view[~view["alert"]]
    display = view[["time", "sender_key", "receiver_key", "amount", "currency", "method", "score", "alert", "label"]]
    st.caption(f"匹配 {len(view):,} 笔；表格显示前 1,000 笔，下载包含全部。/ Showing first 1,000; export includes all matches.")
    st.dataframe(display.head(1000), width="stretch", hide_index=True)
    st.download_button("下载筛选结果 / Download filtered CSV", display.to_csv(index=False).encode("utf-8-sig"), "filtered_transactions.csv", "text/csv")
    with st.expander("清洗记录 / Data quality"):
        st.write(f"读取 {quality['read']:,} 行，移除缺失或无效时间、账户、非正金额 {quality['invalid']:,} 行，移除完全重复 {quality['duplicates']:,} 行，得到 {quality['usable']:,} 行。")
        st.write(f"有效 0/1 标签 {quality['labelled']:,} 行；源文件列名：{', '.join(map(str, raw.columns))}")

else:
    section("用 SQL 复核交易 / SQL checks", "在当前币种和日期的数据上执行查询；规则得分由 Python 计算。")
    queries = {
        "收款账户集中度 / Recipient concentration": "SELECT receiver_key, COUNT(*) AS transactions, COUNT(DISTINCT sender_key) AS distinct_senders, ROUND(SUM(amount), 2) AS incoming_amount FROM transactions GROUP BY receiver_key ORDER BY incoming_amount DESC LIMIT 20",
        "银行之间资金流 / Bank flows": "SELECT from_bank, to_bank, COUNT(*) AS transactions, ROUND(SUM(amount), 2) AS volume FROM transactions GROUP BY from_bank, to_bank ORDER BY volume DESC LIMIT 20",
        "规则得分与复核量 / Scores and workload": "SELECT score, COUNT(*) AS transactions, SUM(alert) AS alerts, ROUND(SUM(amount), 2) AS volume FROM transactions GROUP BY score ORDER BY score DESC",
    }
    choice = st.selectbox("查询 / Query", list(queries))
    st.code(queries[choice], language="sql")
    with sqlite3.connect(":memory:") as con:
        subset = d[["time", "sender_key", "receiver_key", "amount", "from_bank", "to_bank", "method", "currency", "label", "score", "alert"]].copy()
        subset["time"] = subset["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        subset["label"] = subset["label"].astype("float")
        subset["alert"] = subset["alert"].astype(int)
        subset.to_sql("transactions", con, index=False)
        result = pd.read_sql_query(queries[choice], con)
    st.dataframe(result, width="stretch", hide_index=True)

st.caption("规则分析原型 / Rule-based analytical prototype · 合成数据仅用于学习。/ Synthetic data for education.")
