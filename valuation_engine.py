
import math

def clamp(x, lo, hi): return max(lo, min(hi, x))

def dcf_per_share(fcf0, growth, wacc, terminal_growth, years, net_debt, shares):
    if not all(v is not None for v in [fcf0,growth,wacc,terminal_growth,years,net_debt,shares]) or shares<=0:
        return None
    if wacc <= terminal_growth or wacc <= 0:
        return None
    pv=0.0
    fcf=fcf0
    for y in range(1, years+1):
        fcf *= (1+growth)
        pv += fcf/((1+wacc)**y)
    terminal=fcf*(1+terminal_growth)/(wacc-terminal_growth)
    pv += terminal/((1+wacc)**years)
    equity=pv-net_debt
    return equity/shares

def pe_value(eps, multiple):
    return None if eps is None or multiple is None else eps*multiple

def pb_value(bvps, multiple):
    return None if bvps is None or multiple is None else bvps*multiple

def ev_ebitda_value(ebitda, multiple, net_debt, shares):
    if None in (ebitda,multiple,net_debt,shares) or shares<=0: return None
    return (ebitda*multiple-net_debt)/shares

def weighted(values, weights):
    pairs = [
        (v, w)
        for v, w in zip(values, weights)
        if (
            v is not None
            and math.isfinite(v)
            and v > 0
            and w is not None
            and math.isfinite(w)
            and w > 0
        )
    ]

    if not pairs:
        return None

    total_weight = sum(w for _, w in pairs)
    if total_weight <= 0:
        return None

    return sum(v * w for v, w in pairs) / total_weight


def estimate_quality(f):
    # Only scores observed inputs; missing values reduce confidence.
    score=50.0
    if f.get("roe") is not None: score += clamp((f["roe"]-0.10)*80,-10,10)
    if f.get("fcf_margin") is not None: score += clamp((f["fcf_margin"]-0.08)*50,-8,8)
    if f.get("net_debt_to_ebitda") is not None: score += clamp(-f["net_debt_to_ebitda"]*4,-12,8)
    return round(clamp(score,0,100),1)

def run_valuation(f, assumptions):
    # assumptions contains industry-appropriate base/bear/bull settings.
    eps=f.get("forward_eps")
    bvps=f.get("bvps")
    ebitda=f.get("forward_ebitda")
    fcf=f.get("forward_fcf")
    net_debt=f.get("net_debt")
    shares=f.get("diluted_shares")
    vals=[]
    weights=[]
    pe=pe_value(eps, assumptions.get("pe_base"))
    if pe is not None: vals.append(pe); weights.append(assumptions.get("w_pe",0))
    pb=pb_value(bvps, assumptions.get("pb_base"))
    if pb is not None: vals.append(pb); weights.append(assumptions.get("w_pb",0))
    ev=ev_ebitda_value(ebitda, assumptions.get("ev_ebitda_base"),net_debt,shares)
    if ev is not None: vals.append(ev); weights.append(assumptions.get("w_ev",0))
    dcf=dcf_per_share(fcf,assumptions.get("growth_base"),assumptions.get("wacc"),
                      assumptions.get("terminal_growth"),assumptions.get("years",10),net_debt,shares)
    if dcf is not None: vals.append(dcf); weights.append(assumptions.get("w_dcf",0))
    base=weighted(vals,weights)
    bear=weighted([
        pe_value(eps,assumptions.get("pe_bear")),
        pb_value(bvps,assumptions.get("pb_bear")),
        ev_ebitda_value(ebitda,assumptions.get("ev_ebitda_bear"),net_debt,shares),
        dcf_per_share(fcf,assumptions.get("growth_bear"),assumptions.get("wacc_bear",assumptions.get("wacc")),
                      assumptions.get("terminal_growth"),assumptions.get("years",10),net_debt,shares)
    ],weights)
    bull=weighted([
        pe_value(eps,assumptions.get("pe_bull")),
        pb_value(bvps,assumptions.get("pb_bull")),
        ev_ebitda_value(ebitda,assumptions.get("ev_ebitda_bull"),net_debt,shares),
        dcf_per_share(fcf,assumptions.get("growth_bull"),assumptions.get("wacc_bull",assumptions.get("wacc")),
                      assumptions.get("terminal_growth"),assumptions.get("years",10),net_debt,shares)
    ],weights)
    quality=estimate_quality(f)
    completeness=sum(v is not None for v in [eps,bvps,ebitda,fcf,net_debt,shares])/6
    confidence=round(clamp(45 + completeness*35 + quality*0.20,0,100),1)
    return {"bear_value":bear,"fair_value":base,"bull_value":bull,
            "quality_score":quality,"confidence":confidence,
            "methods_used":len(vals)}

def assumptions_for(industry):
    # Transparent neutral defaults. These are model defaults, not facts.
    i=(industry or "").lower()
    if "financial" in i or "bank" in i:
        return dict(pe_base=12,pe_bear=9,pe_bull=15,pb_base=1.3,pb_bear=0.9,pb_bull=1.7,
                    w_pe=.35,w_pb=.65,w_ev=0,w_dcf=0,growth_base=.05,growth_bear=.00,growth_bull=.08,
                    wacc=.10,terminal_growth=.025,years=10)
    if "semiconductor" in i or "technology" in i or "software" in i:
        return dict(pe_base=24,pe_bear=18,pe_bull=30,pb_base=4,pb_bear=2.5,pb_bull=6,
                    w_pe=.40,w_pb=.05,w_ev=.15,w_dcf=.40,growth_base=.10,growth_bear=.04,growth_bull=.16,
                    wacc=.10,terminal_growth=.03,years=10,ev_ebitda_base=18,ev_ebitda_bear=13,ev_ebitda_bull=23)
    return dict(pe_base=18,pe_bear=14,pe_bull=22,pb_base=2.5,pb_bear=1.7,pb_bull=3.2,
                w_pe=.50,w_pb=.15,w_ev=.15,w_dcf=.20,growth_base=.06,growth_bear=.02,growth_bull=.10,
                wacc=.09,terminal_growth=.025,years=10,ev_ebitda_base=13,ev_ebitda_bear=10,ev_ebitda_bull=16)
