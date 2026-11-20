"""Snapshot-based order-book metrics. No trade aggressor inference is performed."""
from datetime import datetime, timedelta
from collections import defaultdict


def _valid_levels(levels):
    result = []
    for level in levels or []:
        try:
            price = float(level["price"])
            quantity = float(level["quantity"])
            if price > 0 and quantity >= 0:
                result.append({"price": price, "quantity": quantity})
        except (KeyError, TypeError, ValueError):
            continue
    return result


def depth_metrics(buy_levels, sell_levels):
    """Return book pressure and spread metrics for the first 5/10/20 levels."""
    buys, sells = _valid_levels(buy_levels), _valid_levels(sell_levels)
    out = {"bid_levels": len(buys), "ask_levels": len(sells)}
    for n in (5, 10, 20):
        bid_qty = sum(x["quantity"] for x in buys[:n])
        ask_qty = sum(x["quantity"] for x in sells[:n])
        total = bid_qty + ask_qty
        out[f"bid_qty_{n}"] = bid_qty
        out[f"ask_qty_{n}"] = ask_qty
        out[f"imbalance_{n}"] = ((bid_qty - ask_qty) / total * 100.0) if total else 0.0
    if buys and sells:
        best_bid = max(x["price"] for x in buys)
        best_ask = min(x["price"] for x in sells)
        best_bid_qty = sum(x["quantity"] for x in buys if x["price"] == best_bid)
        best_ask_qty = sum(x["quantity"] for x in sells if x["price"] == best_ask)
        out["best_bid"], out["best_ask"] = best_bid, best_ask
        out["spread"] = best_ask - best_bid
        out["mid_price"] = (best_bid + best_ask) / 2.0
        denominator = best_bid_qty + best_ask_qty
        out["weighted_mid"] = ((best_ask * best_bid_qty + best_bid * best_ask_qty) / denominator
                               if denominator else out["mid_price"])
    else:
        out.update({"best_bid": None, "best_ask": None, "spread": None,
                    "mid_price": None, "weighted_mid": None})
    return out


def liquidity_changes(previous_buys, previous_sells, current_buys, current_sells):
    """Compare displayed quantities at identical prices across two snapshots."""
    changes = []
    for side, previous, current in (("Bid", previous_buys, current_buys),
                                    ("Ask", previous_sells, current_sells)):
        before = {x["price"]: x["quantity"] for x in _valid_levels(previous)}
        after = {x["price"]: x["quantity"] for x in _valid_levels(current)}
        for price in sorted(set(before) | set(after), reverse=(side == "Bid")):
            old_qty, new_qty = before.get(price, 0.0), after.get(price, 0.0)
            delta = new_qty - old_qty
            if delta:
                changes.append({"side": side, "price": price, "previous_qty": old_qty,
                                "current_qty": new_qty, "change_qty": delta,
                                "change_type": "Added/increased" if delta > 0 else "Reduced/absent"})
    return sorted(changes, key=lambda x: abs(x["change_qty"]), reverse=True)


def rolling_depth_analysis(records, window_minutes):
    """Compute rolling means and dominance persistence from timestamped snapshots."""
    parsed = []
    for record in records:
        try:
            stamp = datetime.fromisoformat(str(record["received_timestamp"]))
            metrics = depth_metrics(record["buys"], record["sells"])
            parsed.append((stamp, metrics))
        except (KeyError, TypeError, ValueError):
            continue
    if not parsed:
        return {}
    latest_time = max(x[0] for x in parsed)
    cutoff = latest_time - timedelta(minutes=window_minutes)
    window = [(ts, m) for ts, m in parsed if cutoff <= ts <= latest_time]
    if not window:
        return {}
    result = {"samples": len(window), "window_minutes": window_minutes}
    for n in (5, 10, 20):
        values = [m[f"imbalance_{n}"] for _, m in window]
        result[f"mean_imbalance_{n}"] = sum(values) / len(values)
        result[f"positive_persistence_{n}"] = sum(v >= 15 for v in values) / len(values) * 100
        result[f"negative_persistence_{n}"] = sum(v <= -15 for v in values) / len(values) * 100
    latest = window[-1][1]
    result["latest_imbalance_5"] = latest["imbalance_5"]
    result["latest_imbalance_20"] = latest["imbalance_20"]
    result["divergence"] = (
        "Near bid-heavy / deeper ask-heavy"
        if latest["imbalance_5"] >= 15 and latest["imbalance_20"] <= -10 else
        "Near ask-heavy / deeper bid-heavy"
        if latest["imbalance_5"] <= -15 and latest["imbalance_20"] >= 10 else
        "No strong near/deep disagreement"
    )
    result["alert"] = (
        "Near/deep liquidity divergence"
        if len(window) >= 3 and result["divergence"] != "No strong near/deep disagreement"
        else "No divergence alert"
    )
    return result
