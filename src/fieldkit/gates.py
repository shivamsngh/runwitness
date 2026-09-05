OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}


def evaluate(gates, metrics, run_valid=True):
    decisions = []
    for gate in gates:
        metric, op = gate["metric"], gate["op"]
        actual = metrics.get(metric)
        expected = gate.get("value")
        if not run_valid:
            status, reason = "invalid", "benchmark run did not complete successfully"
        elif op == "exists":
            status, reason = ("pass", None) if metric in metrics else ("unknown", "metric unavailable")
        elif metric not in metrics:
            status, reason = "unknown", "metric unavailable"
        else:
            try:
                status = "pass" if OPS[op](actual, expected) else "fail"
                reason = None
            except (TypeError, ValueError) as exc:
                status, reason = "invalid", str(exc)
        decisions.append({"metric": metric, "op": op, "expected": expected,
                          "actual": actual, "status": status, "reason": reason})
    statuses = {item["status"] for item in decisions}
    if not run_valid or "invalid" in statuses:
        overall = "invalid"
    elif "fail" in statuses:
        overall = "fail"
    elif "unknown" in statuses:
        overall = "unknown"
    else:
        overall = "pass"
    return {"overall": overall, "gates": decisions}
