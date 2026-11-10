"""Transparent multi-method valuation engine.

Supports 5-year DCF (Gordon growth, revenue exit, EBITDA exit), DDM,
and selected trading multiples. Models are grouped to avoid double-counting
highly correlated valuation methods. Financial companies use a separate set.
"""
import math


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def finite_number(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def safe_positive(x):
    return finite_number(x) and x > 0


def pv_factor(rate, year):
    if not finite_number(rate) or rate <= -1 or year <= 0:
        return None
    return (1 + rate) ** year


def dcf_forecast_pv(fcf0, growth, wacc, years=5):
    """PV of explicit annual FCFs only; terminal value is handled separately."""
    if not all(finite_number(v) for v in (fcf0, growth, wacc, years)):
        return None
    if fcf0 <= 0 or years != 5 or growth <= -1 or growth > 0.50 or wacc <= 0:
        return None
    pv = 0.0
    fcf = fcf0
    for year in range(1, 6):
        fcf *= 1 + growth
        factor = pv_factor(wacc, year)
        if factor is None:
            return None
        pv += fcf / factor
    return pv, fcf


def dcf_gordon_per_share(fcf0, growth, wacc, terminal_growth, net_debt, shares):
    """5-year DCF with Gordon-growth terminal value."""
    if not all(finite_number(v) for v in (net_debt, shares, terminal_growth)):
        return None
    if shares <= 0 or wacc <= terminal_growth or terminal_growth < -0.02 or terminal_growth > 0.04:
        return None
    result = dcf_forecast_pv(fcf0, growth, wacc, 5)
    if result is None:
        return None
    pv_explicit, fcf5 = result
    terminal = fcf5 * (1 + terminal_growth) / (wacc - terminal_growth)
    value = (pv_explicit + terminal / pv_factor(wacc, 5) - net_debt) / shares
    return value if safe_positive(value) else None


def dcf_revenue_exit_per_share(revenue, growth, fcf_margin, wacc,
                               exit_ev_sales, net_debt, shares):
    """5-year DCF: project revenue and FCF margin, then apply terminal EV/Sales."""
    vals = (revenue, growth, fcf_margin, wacc, exit_ev_sales, net_debt, shares)
    if not all(finite_number(v) for v in vals):
        return None
    if revenue <= 0 or fcf_margin <= 0 or exit_ev_sales <= 0 or shares <= 0:
        return None
    if growth <= -1 or growth > 0.50 or wacc <= 0:
        return None
    pv_explicit = 0.0
    revenue_t = revenue
    for year in range(1, 6):
        revenue_t *= 1 + growth
        projected_fcf = revenue_t * fcf_margin
        pv_explicit += projected_fcf / pv_factor(wacc, year)
    revenue5 = revenue * (1 + growth) ** 5
    terminal_ev = revenue5 * exit_ev_sales
    value = (pv_explicit + terminal_ev / pv_factor(wacc, 5) - net_debt) / shares
    return value if safe_positive(value) else None


def dcf_ebitda_exit_per_share(fcf0, ebitda, growth, wacc,
                              exit_ev_ebitda, net_debt, shares):
    """5-year DCF: explicit FCF plus terminal EBITDA x EV/EBITDA exit multiple."""
    vals = (fcf0, ebitda, growth, wacc, exit_ev_ebitda, net_debt, shares)
    if not all(finite_number(v) for v in vals):
        return None
    if fcf0 <= 0 or ebitda <= 0 or exit_ev_ebitda <= 0 or shares <= 0:
        return None
    if growth <= -1 or growth > 0.50 or wacc <= 0:
        return None
    result = dcf_forecast_pv(fcf0, growth, wacc, 5)
    if result is None:
        return None
    pv_explicit, _ = result
    ebitda5 = ebitda * (1 + growth) ** 5
    terminal_ev = ebitda5 * exit_ev_ebitda
    value = (pv_explicit + terminal_ev / pv_factor(wacc, 5) - net_debt) / shares
    return value if safe_positive(value) else None


# Backward-compatible alias: legacy callers now receive the requested 5-year DCF.
def dcf_per_share(fcf0, growth, wacc, terminal_growth, years, net_debt, shares):
    if years != 5:
        return None
    return dcf_gordon_per_share(fcf0, growth, wacc, terminal_growth, net_debt, shares)


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


def ps_value(revenue, market_cap, shares, multiple):
    if not all(safe_positive(v) for v in (revenue, market_cap, shares, multiple)):
        return None
    value = (revenue * multiple) / shares
    return value if safe_positive(value) else None


def ev_sales_value(revenue, multiple, net_debt, shares):
    if not all(finite_number(v) for v in (revenue, multiple, net_debt, shares)):
        return None
    if revenue <= 0 or multiple <= 0 or shares <= 0:
        return None
    value = (revenue * multiple - net_debt) / shares
    return value if safe_positive(value) else None


def ev_ebit_value(ebit, multiple, net_debt, shares):
    if not all(finite_number(v) for v in (ebit, multiple, net_debt, shares)):
        return None
    if ebit <= 0 or multiple <= 0 or shares <= 0:
        return None
    value = (ebit * multiple - net_debt) / shares
    return value if safe_positive(value) else None


def ev_ebitda_value(ebitda, multiple, net_debt, shares):
    if not all(finite_number(v) for v in (ebitda, multiple, net_debt, shares)):
        return None
    if ebitda <= 0 or multiple <= 0 or shares <= 0:
        return None
    value = (ebitda * multiple - net_debt) / shares
    return value if safe_positive(value) else None


def ddm_stable(dividend, cost_of_equity, growth):
    """Gordon DDM; dividend is the latest annual dividend per share."""
    if not all(finite_number(v) for v in (dividend, cost_of_equity, growth)):
        return None
    if dividend <= 0 or cost_of_equity <= growth or growth < 0 or growth > 0.06:
        return None
    value = dividend * (1 + growth) / (cost_of_equity - growth)
    return value if safe_positive(value) else None


def ddm_multistage(dividend, cost_of_equity, high_growth, stable_growth, years=5):
    """5-year high-growth dividend stage followed by Gordon terminal value."""
    vals = (dividend, cost_of_equity, high_growth, stable_growth, years)
    if not all(finite_number(v) for v in vals):
        return None
    if dividend <= 0 or years != 5 or cost_of_equity <= stable_growth:
        return None
    if high_growth < -0.20 or high_growth > 0.30 or stable_growth < 0 or stable_growth > 0.05:
        return None
    pv = 0.0
    d = dividend
    for year in range(1, 6):
        d *= 1 + high_growth
        pv += d / pv_factor(cost_of_equity, year)
    terminal = d * (1 + stable_growth) / (cost_of_equity - stable_growth)
    value = pv + terminal / pv_factor(cost_of_equity, 5)
    return value if safe_positive(value) else None


def weighted(values, weights):
    pairs = [(v, w) for v, w in zip(values, weights)
             if safe_positive(v) and finite_number(w) and w > 0]
    if not pairs:
        return None
    total_weight = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total_weight if total_weight > 0 else None


def robust_weighted(values, weights, max_ratio=3.0):
    pairs = [(float(v), float(w)) for v, w in zip(values, weights)
             if safe_positive(v) and finite_number(w) and w > 0]
    if not pairs:
        return None, [], False
    if len(pairs) == 1:
        return pairs[0][0], pairs, False
    ordered = sorted(v for v, _ in pairs)
    n = len(ordered)
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    adjusted, had_outlier = [], False
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
    return sum(v * w for v, w in adjusted) / total_weight, pairs, had_outlier


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


def is_financial_sector(f):
    """Return True for banks/insurers, not every company in Financial Services."""
    industry = str(f.get("industry") or "").lower()
    sector = str(f.get("sector") or "").lower()
    if industry:
        return any(k in industry for k in ("bank", "insurance", "銀行", "保險"))
    return any(k in sector for k in ("bank", "insurance", "銀行", "保險")) or "financial" in sector


def sanitize_financial_inputs(f):
    f = dict(f)
    ticker = str(f.get("ticker", "")).upper()
    price, bvps = f.get("price"), f.get("bvps")
    if ticker == "BRK-B" and safe_positive(price) and safe_positive(bvps) and bvps > price * 100:
        f["bvps"] = bvps / 1500.0
    if is_financial_sector(f):
        # Standard industrial EV/FCF methods are not suitable for banks/insurers.
        for key in ("forward_ebitda", "forward_fcf", "revenue", "ebit", "fcf_margin"):
            f[key] = None
    return f


def data_quality_check(f):
    issues = []
    keys = ("forward_eps", "bvps", "forward_ebitda", "forward_fcf", "revenue",
            "ebit", "dividend_rate", "net_debt", "diluted_shares", "price", "market_cap")
    fields = {key: f.get(key) for key in keys}
    for key, value in fields.items():
        if value is not None and not finite_number(value):
            issues.append(f"{key} 非有效數字")
    price, shares, market_cap = fields["price"], fields["diluted_shares"], fields["market_cap"]
    if safe_positive(price) and safe_positive(shares) and safe_positive(market_cap):
        ratio = market_cap / (price * shares)
        if ratio < 0.50 or ratio > 2.00:
            issues.append("股價×股數與市值差異異常，可能存在股數/單位問題")
    eps = fields["forward_eps"]
    if safe_positive(eps) and safe_positive(price):
        pe = price / eps
        if pe > 250:
            issues.append("Forward PE 極端偏高")
        elif pe < 3:
            issues.append("Forward PE 極端偏低，可能是景氣循環股高峰期或一次性獲利")
    bvps = fields["bvps"]
    if safe_positive(bvps) and safe_positive(price) and price / bvps > 100:
        issues.append("PB 極端偏高，需驗證 BVPS 單位")
    ebitda = fields["forward_ebitda"]
    if safe_positive(ebitda) and safe_positive(market_cap) and market_cap / ebitda > 150:
        issues.append("市值/EBITDA 極端偏高")
    if safe_positive(ebitda) and finite_number(fields["net_debt"]) and fields["net_debt"] / ebitda > 15:
        issues.append("淨負債/EBITDA 過高")
    if safe_positive(fields["revenue"]) and safe_positive(market_cap):
        if market_cap / fields["revenue"] > 100:
            issues.append("市值/營收極端偏高，需確認營收及幣別單位")
    return issues


def _scenario_values(f, a, scenario):
    growth = a.get(f"growth_{scenario}", a.get("growth_base", 0.05))
    wacc = a.get(f"wacc_{scenario}", a.get("wacc", 0.10))
    eps = f.get("forward_eps")
    bvps = f.get("bvps")
    ebitda = f.get("forward_ebitda")
    fcf = f.get("forward_fcf")
    revenue = f.get("revenue")
    ebit = f.get("ebit")
    dividend = f.get("dividend_rate")
    net_debt, shares, market_cap = f.get("net_debt"), f.get("diluted_shares"), f.get("market_cap")
    fcf_margin = f.get("fcf_margin")
    v = {}
    v["DCF_Growth_Exit_5Y"] = dcf_gordon_per_share(
        fcf, growth, wacc, a.get("terminal_growth", 0.025), net_debt, shares)
    v["DCF_Revenue_Exit_5Y"] = dcf_revenue_exit_per_share(
        revenue, growth, fcf_margin, wacc,
        a.get(f"ev_sales_{scenario}", a.get("ev_sales_base", 3.0)), net_debt, shares)
    v["DCF_EBITDA_Exit_5Y"] = dcf_ebitda_exit_per_share(
        fcf, ebitda, growth, wacc,
        a.get(f"ev_ebitda_{scenario}", a.get("ev_ebitda_base", 12.0)), net_debt, shares)
    v["DDM_Stable"] = ddm_stable(
        dividend, a.get("cost_of_equity", 0.10), a.get("ddm_stable_growth", 0.02))
    v["DDM_Multistage"] = ddm_multistage(
        dividend, a.get("cost_of_equity", 0.10),
        a.get("ddm_high_growth", 0.06), a.get("ddm_stable_growth", 0.02), 5)
    v["PE"] = pe_value(eps, a.get(f"pe_{scenario}"))
    v["EV_Sales"] = ev_sales_value(
        revenue, a.get(f"ev_sales_{scenario}", a.get("ev_sales_base")), net_debt, shares)
    v["EV_EBIT"] = ev_ebit_value(ebit, a.get(f"ev_ebit_{scenario}", a.get("ev_ebit_base")), net_debt, shares)
    v["EV_EBITDA"] = ev_ebitda_value(
        ebitda, a.get(f"ev_ebitda_{scenario}", a.get("ev_ebitda_base")), net_debt, shares)
    v["PS"] = ps_value(revenue, market_cap, shares, a.get(f"ps_{scenario}", a.get("ps_base")))
    v["PB"] = pb_value(bvps, a.get(f"pb_{scenario}"))
    return v


def _aggregate_models(model_values, f, a):
    # Equal share within each family; family caps prevent correlated methods
    # (e.g. P/S and EV/Sales, or three DCF variants) dominating the result.
    if is_financial_sector(f):
        families = {
            "earnings": (0.35, ("PE",)),
            "book": (0.45, ("PB",)),
            "dividend": (0.20, ("DDM_Stable", "DDM_Multistage")),
        }
    else:
        families = {
            "dcf": (0.30, ("DCF_Growth_Exit_5Y", "DCF_Revenue_Exit_5Y", "DCF_EBITDA_Exit_5Y")),
            "earnings": (0.20, ("PE",)),
            "enterprise_profit": (0.20, ("EV_EBIT", "EV_EBITDA")),
            "sales": (0.15, ("EV_Sales", "PS")),
            "book": (0.05, ("PB",)),
            "dividend": (0.10, ("DDM_Stable", "DDM_Multistage")),
        }
    vals, weights = [], []
    active_families = []
    for family, (family_weight, names) in families.items():
        available = [name for name in names if safe_positive(model_values.get(name))]
        if available:
            active_families.append((family_weight, available))
    total_family_weight = sum(w for w, _ in active_families)
    for family_weight, names in active_families:
        each_weight = (family_weight / total_family_weight) / len(names)
        for name in names:
            vals.append(model_values[name])
            weights.append(each_weight)
    value, pairs, outlier = robust_weighted(vals, weights)
    raw = weighted(vals, weights)
    return value, raw, pairs, outlier, [name for _, names in active_families for name in names]


def run_valuation(f, assumptions):
    f = sanitize_financial_inputs(f)
    base_values = _scenario_values(f, assumptions, "base")
    bear_values = _scenario_values(f, assumptions, "bear")
    bull_values = _scenario_values(f, assumptions, "bull")
    base, raw_base, used_pairs, had_outlier, used_names = _aggregate_models(base_values, f, assumptions)
    bear, _, _, bear_outlier, _ = _aggregate_models(bear_values, f, assumptions)
    bull, _, _, bull_outlier, _ = _aggregate_models(bull_values, f, assumptions)

    issues = data_quality_check(f)
    if had_outlier:
        issues.append("不同估值模型差距過大，已進行離群值降權")
    if bear_outlier or bull_outlier:
        issues.append("Bear/Bull 情境存在模型離群值，已進行降權")

    price = f.get("price")
    fair_value_extreme = False
    if safe_positive(base) and safe_positive(price):
        ratio = base / price
        if ratio > 2.0 or ratio < 0.50:
            issues.append(f"推估合理價與現價差距較大 ({ratio:.2f}x)，需檢查獲利正常化及估值倍數")
        if ratio > 3.5 or ratio < 0.25:
            fair_value_extreme = True
            issues.append(f"推估合理價與現價偏離過大 ({ratio:.2f}x)，觸發估值保護機制")

    quality = estimate_quality(f)
    if is_financial_sector(f):
        input_keys = ("forward_eps", "bvps")
    else:
        input_keys = ("forward_eps", "forward_ebitda", "forward_fcf",
                      "revenue", "ebit", "net_debt", "diluted_shares")
    completeness = sum(f.get(k) is not None for k in input_keys) / len(input_keys)
    confidence = 45 + completeness * 30 + quality * 0.25
    if had_outlier:
        confidence -= 12
    if len(used_pairs) < 2:
        confidence -= 15
    if len(issues) >= 2:
        confidence -= 8
    if fair_value_extreme:
        confidence -= 20
    confidence = round(clamp(confidence, 0, 100), 1)

    severe = any(k in issue for issue in issues for k in (
        "股價×股數與市值差異異常", "BVPS 單位", "市值/EBITDA 極端"))
    if severe or fair_value_extreme:
        fair_value, status = None, "資料或估值結果偏離過大，暫不提供合理價"
    elif base is None:
        fair_value, status = None, "資料不足，暫不提供合理價"
    elif len(used_pairs) < 2:
        fair_value, status = None, "僅單一估值方法，暫不提供合理價"
    else:
        fair_value = base
        status = "模型計算（已進行離群值檢查）" if had_outlier else "模型計算（需人工/資料源驗證假設）"

    return {
        "bear_value": bear if not fair_value_extreme else None,
        "fair_value": fair_value,
        "bull_value": bull if not fair_value_extreme else None,
        "raw_fair_value": raw_base,
        "quality_score": quality,
        "confidence": confidence,
        "methods_used": len(used_pairs),
        "methods_used_names": used_names,
        "model_values_base": base_values,
        "model_values_bear": bear_values,
        "model_values_bull": bull_values,
        "valuation_status": status,
        "valuation_anomalies": issues,
        "outlier_adjusted": had_outlier,
    }


def assumptions_for(industry):
    i = str(industry or "").lower()
    common = dict(
        growth_base=0.06, growth_bear=0.02, growth_bull=0.10,
        wacc=0.10, wacc_bear=0.11, wacc_bull=0.09,
        terminal_growth=0.025,
        cost_of_equity=0.10, ddm_stable_growth=0.02, ddm_high_growth=0.06,
        pe_base=18, pe_bear=14, pe_bull=22,
        pb_base=2.5, pb_bear=1.7, pb_bull=3.2,
        ev_sales_base=3.0, ev_sales_bear=2.0, ev_sales_bull=4.0,
        ps_base=3.0, ps_bear=2.0, ps_bull=4.0,
        ev_ebit_base=15, ev_ebit_bear=11, ev_ebit_bull=19,
        ev_ebitda_base=13, ev_ebitda_bear=10, ev_ebitda_bull=16,
    )
    if any(k in i for k in ("financial", "bank", "insurance", "金融", "銀行", "保險")):
        common.update(pe_base=12, pe_bear=9, pe_bull=15,
                      pb_base=1.2, pb_bear=0.8, pb_bull=1.6,
                      cost_of_equity=0.11, ddm_stable_growth=0.02, ddm_high_growth=0.04)
    elif any(k in i for k in ("semiconductor", "technology", "software", "半導體", "科技")):
        common.update(growth_base=0.10, growth_bear=0.04, growth_bull=0.16,
                      pe_base=24, pe_bear=18, pe_bull=30,
                      pb_base=4, pb_bear=2.5, pb_bull=6,
                      ev_sales_base=5, ev_sales_bear=3, ev_sales_bull=7,
                      ps_base=5, ps_bear=3, ps_bull=7,
                      ev_ebit_base=20, ev_ebit_bear=15, ev_ebit_bull=25,
                      ev_ebitda_base=18, ev_ebitda_bear=13, ev_ebitda_bull=23)
    return common
