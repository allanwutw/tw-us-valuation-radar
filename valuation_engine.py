import math


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def finite_number(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def safe_positive(x):
    return finite_number(x) and x > 0


def dcf_per_share(fcf0, growth, wacc, terminal_growth, years, net_debt, shares):
    if not all(finite_number(v) for v in [fcf0, growth, wacc, terminal_growth, years, net_debt, shares]):
        return None
    if fcf0 <= 0 or shares <= 0 or years <= 0:
        return None
    if wacc <= terminal_growth or wacc <= 0:
        return None
    if growth <= -1 or growth > 0.50 or terminal_growth < -0.05 or terminal_growth > 0.06:
        return None
    pv = 0.0
    fcf = fcf0
    for y in range(1, int(years) + 1):
        fcf *= (1 + growth)
        pv += fcf / ((1 + wacc) ** y)
    terminal = fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv += terminal / ((1 + wacc) ** int(years))
    value = (pv - net_debt) / shares
    return value if safe_positive(value) else None


def pe_value(eps, multiple):
    if not safe_positive(eps) or not safe_positive(multiple):
        return None
    value = eps * multiple
    return value if safe_positive(value) else None


def pb_value(bvps, multiple):
    if not safe_positive(bvps) or not safe_positive(multiple):
        return None
    value = bvps * multiple
    return value if safe_positive(value) else None


def ev_ebitda_value(ebitda, multiple, net_debt, shares):
    if not all(finite_number(v) for v in [ebitda, multiple, net_debt, shares]):
        return None
    if ebitda <= 0 or multiple <= 0 or shares <= 0:
        return None
    value = (ebitda * multiple - net_debt) / shares
    return value if safe_positive(value) else None


def weighted(values, weights):
    pairs = [
        (v, w)
        for v, w in zip(values, weights)
        if safe_positive(v) and finite_number(w) and w > 0
    ]
    if not pairs:
        return None
    total_weight = sum(w for _, w in pairs)
    if total_weight <= 0:
        return None
    return sum(v * w for v, w in pairs) / total_weight


def robust_weighted(values, weights, max_ratio=3.0):
    pairs = [
        (float(v), float(w))
        for v, w in zip(values, weights)
        if safe_positive(v) and finite_number(w) and w > 0
    ]
    if not pairs:
        return None, [], True
    if len(pairs) == 1:
        return pairs[0][0], pairs, True

    ordered = sorted(v for v, _ in pairs)
    n = len(ordered)
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2

    adjusted = []
    had_outlier = False
    for value, weight in pairs:
        ratio = max(value, median) / max(min(value, median), 1e-12)
        if ratio > max_ratio:
            adjusted.append((value, weight * max_ratio / ratio))
            had_outlier = True
        else:
            adjusted.append((value, weight))

    total_weight = sum(w for _, w in adjusted)
    if total_weight <= 0:
        return None, pairs, had_outlier
    value = sum(v * w for v, w in adjusted) / total_weight
    return value, pairs, had_outlier


def estimate_quality(f):
    score = 50.0
    roe = f.get("roe")
    if finite_number(roe):
        score += clamp((roe - 0.10) * 80, -10, 10)
    fcf_margin = f.get("fcf_margin")
    if finite_number(fcf_margin):
        score += clamp((fcf_margin - 0.08) * 50, -8, 8)
    nde = f.get("net_debt_to_ebitda")
    if finite_number(nde):
        score += clamp(-nde * 4, -12, 8)
    return round(clamp(score, 0, 100), 1)


def data_quality_check(f):
    issues = []
    fields = {
        "forward_eps": f.get("forward_eps"),
        "bvps": f.get("bvps"),
        "forward_ebitda": f.get("forward_ebitda"),
        "forward_fcf": f.get("forward_fcf"),
        "net_debt": f.get("net_debt"),
        "diluted_shares": f.get("diluted_shares"),
        "price": f.get("price"),
        "market_cap": f.get("market_cap"),
    }
    for key, value in fields.items():
        if value is not None and not finite_number(value):
            issues.append(f"{key} 非有效數字")

    price = fields["price"]
    shares = fields["diluted_shares"]
    market_cap = fields["market_cap"]
    if safe_positive(price) and safe_positive(shares) and safe_positive(market_cap):
        implied = price * shares
        ratio = market_cap / implied
        if ratio < 0.50 or ratio > 2.00:
            issues.append("股價×股數與市值差異異常，可能存在股數/單位問題")

    eps = fields["forward_eps"]
    if safe_positive(eps) and safe_positive(price):
        pe = price / eps
        if pe > 250:
            issues.append("Forward PE 極端偏高")
        elif pe < 1:
            issues.append("Forward PE 極端偏低，需驗證 EPS")

    bvps = fields["bvps"]
    if safe_positive(bvps) and safe_positive(price) and price / bvps > 100:
        issues.append("PB 極端偏高，需驗證 BVPS 單位")

    ebitda = fields["forward_ebitda"]
    if safe_positive(ebitda) and safe_positive(market_cap) and market_cap / ebitda > 150:
        issues.append("市值/EBITDA 極端偏高")

    if safe_positive(ebitda) and finite_number(fields["net_debt"]):
        if fields["net_debt"] / ebitda > 15:
            issues.append("淨負債/EBITDA 過高")
    return issues


def run_valuation(f, assumptions):
    eps, bvps = f.get("forward_eps"), f.get("bvps")
    ebitda, fcf = f.get("forward_ebitda"), f.get("forward_fcf")
    net_debt, shares = f.get("net_debt"), f.get("diluted_shares")

    base_values = [
        pe_value(eps, assumptions.get("pe_base")),
        pb_value(bvps, assumptions.get("pb_base")),
        ev_ebitda_value(ebitda, assumptions.get("ev_ebitda_base"), net_debt, shares),
        dcf_per_share(fcf, assumptions.get("growth_base"), assumptions.get("wacc"),
                      assumptions.get("terminal_growth"), assumptions.get("years", 10), net_debt, shares)
    ]
    weights = [assumptions.get("w_pe", 0), assumptions.get("w_pb", 0),
               assumptions.get("w_ev", 0), assumptions.get("w_dcf", 0)]

    raw_base = weighted(base_values, weights)
    base, used_pairs, had_outlier = robust_weighted(base_values, weights)

    bear_values = [
        pe_value(eps, assumptions.get("pe_bear")),
        pb_value(bvps, assumptions.get("pb_bear")),
        ev_ebitda_value(ebitda, assumptions.get("ev_ebitda_bear"), net_debt, shares),
        dcf_per_share(fcf, assumptions.get("growth_bear"), assumptions.get("wacc_bear", assumptions.get("wacc")),
                      assumptions.get("terminal_growth"), assumptions.get("years", 10), net_debt, shares)
    ]
    bull_values = [
        pe_value(eps, assumptions.get("pe_bull")),
        pb_value(bvps, assumptions.get("pb_bull")),
        ev_ebitda_value(ebitda, assumptions.get("ev_ebitda_bull"), net_debt, shares),
        dcf_per_share(fcf, assumptions.get("growth_bull"), assumptions.get("wacc_bull", assumptions.get("wacc")),
                      assumptions.get("terminal_growth"), assumptions.get("years", 10), net_debt, shares)
    ]
    bear, _, bear_outlier = robust_weighted(bear_values, weights)
    bull, _, bull_outlier = robust_weighted(bull_values, weights)

    issues = data_quality_check(f)
    if had_outlier:
        issues.append("不同估值模型差距過大，已進行離群值降權")
    if bear_outlier or bull_outlier:
        issues.append("Bear/Bull 情境存在模型離群值，已進行降權")

    quality = estimate_quality(f)
    completeness = sum(v is not None for v in [eps, bvps, ebitda, fcf, net_debt, shares]) / 6
    confidence = 45 + completeness * 35 + quality * 0.20
    if had_outlier:
        confidence -= 12
    if len(used_pairs) < 2:
        confidence -= 15
    if len(issues) >= 2:
        confidence -= 8
    confidence = round(clamp(confidence, 0, 100), 1)

    severe = any(
        k in issue for issue in issues
        for k in ("股價×股數與市值差異異常", "BVPS 單位", "市值/EBITDA 極端")
    )
    if severe:
        fair_value = None
        status = "資料異常，暫不提供合理價"
    elif base is None:
        fair_value = None
        status = "資料不足，暫不提供合理價"
    elif len(used_pairs) < 2:
        fair_value = None
        status = "僅單一估值方法，暫不提供合理價"
    else:
        fair_value = base
        status = "模型計算（已進行離群值檢查）" if had_outlier else "模型計算（需人工/資料源驗證假設）"

    return {
        "bear_value": bear, "fair_value": fair_value, "bull_value": bull,
        "raw_fair_value": raw_base,
        "quality_score": quality, "confidence": confidence,
        "methods_used": len(used_pairs),
        "valuation_status": status,
        "valuation_anomalies": issues,
        "outlier_adjusted": had_outlier,
    }


def assumptions_for(industry):
    i = (industry or "").lower()
    if "financial" in i or "bank" in i:
        return dict(pe_base=12, pe_bear=9, pe_bull=15, pb_base=1.3, pb_bear=0.9, pb_bull=1.7,
                    w_pe=.35, w_pb=.65, w_ev=0, w_dcf=0, growth_base=.05, growth_bear=.00,
                    growth_bull=.08, wacc=.10, terminal_growth=.025, years=10)
    if "semiconductor" in i or "technology" in i or "software" in i:
        return dict(pe_base=24, pe_bear=18, pe_bull=30, pb_base=4, pb_bear=2.5, pb_bull=6,
                    w_pe=.40, w_pb=.05, w_ev=.15, w_dcf=.40, growth_base=.10, growth_bear=.04,
                    growth_bull=.16, wacc=.10, terminal_growth=.03, years=10,
                    ev_ebitda_base=18, ev_ebitda_bear=13, ev_ebitda_bull=23)
    return dict(pe_base=18, pe_bear=14, pe_bull=22, pb_base=2.5, pb_bear=1.7, pb_bull=3.2,
                w_pe=.50, w_pb=.15, w_ev=.15, w_dcf=.20, growth_base=.06, growth_bear=.02,
                growth_bull=.10, wacc=.09, terminal_growth=.025, years=10,
                ev_ebitda_base=13, ev_ebitda_bear=10, ev_ebitda_bull=16)
