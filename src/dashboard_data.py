from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np
import pandas as pd


FIELDS = {
    "time": "Timestamp", "sender": "Account", "receiver": "Account.1",
    "amount": "Amount Paid", "from_bank": "From Bank", "to_bank": "To Bank",
    "currency": "Payment Currency", "method": "Payment Format",
    "label": "Is Laundering",
}
REQUIRED = ("time", "sender", "receiver", "amount")
OPTIONAL = ("from_bank", "to_bank", "currency", "method", "label")


@dataclass
class Rules:
    amount: float = 10000
    window_hours: int = 24
    frequency: int = 5
    fan_in: int = 4
    transfer_hours: int = 24
    transfer_ratio: float = 0.8
    alert_score: int = 4


def read_csv(source, max_rows=250000, allow_prefix=False):
    if hasattr(source, "seek"):
        source.seek(0)
    try:
        frame = pd.read_csv(source, nrows=max_rows + 1, low_memory=False, encoding="utf-8-sig")
    except UnicodeDecodeError:
        if hasattr(source, "seek"):
            source.seek(0)
        frame = pd.read_csv(source, nrows=max_rows + 1, low_memory=False, encoding="gb18030")
    if len(frame) > max_rows:
        if not allow_prefix:
            raise ValueError(f"CSV 超过 {max_rows:,} 行。请先截取连续时间段的数据；随机抽样会破坏频率与资金流分析。")
        frame = frame.iloc[:max_rows].copy()
        frame.attrs["prefix_limited"] = True
    if frame.empty:
        raise ValueError("CSV 没有交易记录。")
    return frame


def normalize(raw, mapping):
    absent = [key for key in REQUIRED if not mapping.get(key) or mapping[key] not in raw]
    if absent:
        raise ValueError("缺少必要字段：" + ", ".join(absent))
    chosen = [mapping[k] for k in (*REQUIRED, *OPTIONAL) if mapping.get(k)]
    if len(chosen) != len(set(chosen)):
        raise ValueError("每个字段必须映射到不同的 CSV 列。")
    data = pd.DataFrame({k: raw[mapping[k]] if mapping.get(k) else pd.Series([pd.NA] * len(raw), index=raw.index)
                         for k in (*REQUIRED, *OPTIONAL)})
    original = len(data)
    data["time"] = pd.to_datetime(data["time"], errors="coerce", utc=True)
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce")
    for key in ("sender", "receiver"):
        data[key] = data[key].astype("string").str.strip()
    bad = data["time"].isna() | data["amount"].isna() | (data["amount"] <= 0)
    bad |= data["sender"].isna() | data["receiver"].isna()
    bad |= data["sender"].eq("").fillna(True) | data["receiver"].eq("").fillna(True)
    invalid = int(bad.sum())
    data = data.loc[~bad].copy()
    duplicates = int(data.duplicated().sum())
    data = data.drop_duplicates().copy()
    for key in ("from_bank", "to_bank", "currency", "method"):
        data[key] = data[key].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    if mapping.get("label"):
        values = pd.to_numeric(data["label"], errors="coerce")
        if values.notna().any() and not values.dropna().isin((0, 1)).all():
            raise ValueError("模拟标签列仅支持 0、1 或空值。")
        data["label"] = values.astype("Int64")
    else:
        data["label"] = pd.Series(pd.NA, index=data.index, dtype="Int64")
    if data.empty:
        raise ValueError("清洗后没有可用交易，请检查时间、金额和账户列。")
    data = data.sort_values("time", kind="stable").reset_index(drop=True)
    data.insert(0, "row_id", np.arange(1, len(data) + 1))
    data["sender_key"] = data["from_bank"] + ":" + data["sender"].astype(str)
    data["receiver_key"] = data["to_bank"] + ":" + data["receiver"].astype(str)
    quality = {"read": original, "invalid": invalid, "duplicates": duplicates, "usable": len(data),
               "labelled": int(data["label"].notna().sum())}
    return data, quality


def score_transactions(data, rules):
    d = data.copy().reset_index(drop=True)
    times = d["time"].astype("int64").to_numpy() // 10**9
    window = rules.window_hours * 3600
    short = rules.transfer_hours * 3600
    sender_windows = defaultdict(deque)
    receiver_windows = defaultdict(deque)
    incoming_windows = defaultdict(deque)
    frequencies = np.zeros(len(d), dtype=int)
    fanins = np.zeros(len(d), dtype=int)
    quick = np.zeros(len(d), dtype=bool)
    amounts = d["amount"].to_numpy(dtype=float)
    senders = d["sender_key"].to_numpy()
    receivers = d["receiver_key"].to_numpy()
    for i, (t, source, target) in enumerate(zip(times, senders, receivers)):
        outbox = sender_windows[source]
        while outbox and outbox[0] < t - window:
            outbox.popleft()
        outbox.append(t)
        frequencies[i] = len(outbox)
        inbound = receiver_windows[target]
        while inbound and inbound[0][0] < t - window:
            inbound.popleft()
        inbound.append((t, source))
        fanins[i] = len({item[1] for item in inbound})
        recent = incoming_windows[source]
        while recent and recent[0][0] < t - short:
            recent.popleft()
        quick[i] = bool(recent) and sum(item[1] for item in recent) >= amounts[i] * rules.transfer_ratio
        incoming_windows[target].append((t, amounts[i]))
    d["high_amount"] = d["amount"].to_numpy() >= rules.amount
    d["high_frequency"] = frequencies >= rules.frequency
    d["fan_in"] = fanins >= rules.fan_in
    d["rapid_outflow"] = quick
    d["cross_bank"] = (d["from_bank"] != d["to_bank"]) & (d["from_bank"] != "Unknown") & (d["to_bank"] != "Unknown")
    d["score"] = (2 * d["high_amount"].astype(int) + 2 * d["high_frequency"].astype(int)
                  + 2 * d["fan_in"].astype(int) + 2 * d["rapid_outflow"].astype(int)
                  + d["cross_bank"].astype(int))
    d["alert"] = d["score"] >= rules.alert_score
    d["frequency_rolling"] = frequencies
    d["distinct_senders_rolling"] = fanins
    return d


def review_metrics(d):
    labelled = d[d["label"].notna()]
    if labelled.empty:
        return None
    truth = labelled["label"].to_numpy(dtype=int) == 1
    alerts = labelled["alert"].to_numpy(dtype=bool)
    tp = int((truth & alerts).sum())
    fp = int((~truth & alerts).sum())
    fn = int((truth & ~alerts).sum())
    tn = int((~truth & ~alerts).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0}


def financial_summary(d):
    receivers = d.groupby("receiver_key")["amount"].sum().sort_values(ascending=False)
    return {
        "median": float(d["amount"].median()),
        "top10_share": float(receivers.head(10).sum() / d["amount"].sum()),
        "cross_bank_share": float(d["cross_bank"].mean()),
        "alert_share": float(d["alert"].mean()),
        "peak_day": str(d.groupby(d["time"].dt.date).size().idxmax()),
    }
