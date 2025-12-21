# recommendations.py
from typing import List, Dict


def make_reco(
    title: str,
    category: str,
    definition: str,
    reason: str,
    quantitative: Dict[str, float],
    pros: List[str],
    cons: List[str],
    when_to_use: str,
    priority: str,
) -> Dict:
    return {
        "title": title,
        "category": category,  # Finance | CO2 | Grid | Transformer
        "definition": definition,
        "reason": reason,
        "quantitative": quantitative,
        "pros": pros,
        "cons": cons,
        "when_to_use": when_to_use,
        "priority": priority,
    }


def generate_recommendations(results: dict) -> List[Dict]:
    recos = []

    inp = results["inputs"]
    dv = results["diesel_vs_ev"]
    ec = results["energy_cost"]
    co2 = results["co2"]
    load = results["load"]
    dist = results["distance"]

    # -------------------------
    # CORE METRICS
    # -------------------------
    annual_km = dist["annual_km_fleet"]
    cost_savings = dv["cost_savings_eur"]
    total_savings = dv["total_savings_incl_toll_eur"]
    co2_savings = dv["co2_savings_kg"]

    transformer_kva = inp["site_capacity_limit_kva"]
    peak_kw = load["new_theoretical_peak_kw"]
    charger_kw = inp["charger_power_per_truck_kw"]
    num_trucks = inp["num_trucks"]

    transformer_util = peak_kw / transformer_kva if transformer_kva > 0 else 0.0

    # -------------------------
    # FINANCIAL OPTIMISATION
    # -------------------------
    if cost_savings <= 0:
        delta_per_km = cost_savings / annual_km if annual_km > 0 else 0.0

        recos.append(make_reco(
            title="Reduce electricity cost via charging optimisation",
            category="Finance",
            definition=(
                "Adjust charging timing or power to reduce the effective electricity cost per km."
            ),
            reason=(
                "Under the current assumptions, EV electricity cost exceeds diesel fuel cost."
            ),
            quantitative={
                "annual_cost_gap_eur": abs(cost_savings),
                "cost_gap_eur_per_km": abs(delta_per_km),
                "annual_energy_mwh": ec["annual_energy_mwh"],
            },
            pros=[
                "Direct operating cost reduction",
                "No capital investment required",
            ],
            cons=[
                "May reduce operational flexibility",
            ],
            when_to_use="When electricity prices or charging patterns are unfavourable.",
            priority="high",
        ))

    # -------------------------
    # CO₂ OPTIMISATION
    # -------------------------
    if co2_savings <= 0:
        co2_per_km_gap = co2_savings / annual_km if annual_km > 0 else 0.0

        recos.append(make_reco(
            title="Shift charging to lower-carbon hours",
            category="CO2",
            definition=(
                "Align EV charging with hours of lower grid CO₂ intensity."
            ),
            reason=(
                "The effective grid CO₂ intensity during the charging window is high enough "
                "that EV emissions approach or exceed diesel emissions."
            ),
            quantitative={
                "annual_co2_gap_kg": abs(co2_savings),
                "co2_gap_kg_per_km": abs(co2_per_km_gap),
                "effective_grid_co2_kg_per_kwh": co2["effective_grid_co2_kg_per_kwh"],
            },
            pros=[
                "Improves CO₂ performance immediately",
                "Supports ESG reporting",
            ],
            cons=[
                "Low-CO₂ hours may not align with operations",
            ],
            when_to_use="When emissions reduction is a priority or required for reporting.",
            priority="high",
        ))

    # -------------------------
    # TRANSFORMER / GRID CONSTRAINTS
    # -------------------------
    if transformer_util >= 1.0:
        overload_kw = peak_kw - transformer_kva

        recos.append(make_reco(
            title="Transformer overload – mitigation or upgrade required",
            category="Transformer",
            definition=(
                "The projected EV charging load exceeds the transformer’s rated capacity "
                "and is not feasible for continuous operation."
            ),
            reason=(
                f"Projected peak load is {peak_kw:.0f} kW versus a transformer rating of "
                f"{transformer_kva:.0f} kVA."
            ),
            quantitative={
                "transformer_loading_pct": transformer_util * 100,
                "overload_kw": overload_kw,
                "required_peak_reduction_kw": overload_kw,
            },
            pros=[
                "Ensures grid compliance",
                "Avoids transformer overheating and failure",
            ],
            cons=[
                "Transformer upgrade is capital-intensive",
                "Mitigation may limit charging speed",
            ],
            when_to_use=(
                "When peak EV charging coincides with other site loads and exceeds transformer limits."
            ),
            priority="high",
        ))

    elif transformer_util >= 0.8:
        headroom_kw = transformer_kva - peak_kw

        recos.append(make_reco(
            title="High transformer utilisation – manage charging peaks",
            category="Transformer",
            definition=(
                "Operate the transformer below sustained high-load conditions to reduce ageing risk."
            ),
            reason=(
                f"Transformer utilisation reaches {transformer_util:.0%}, which is high for "
                "daily continuous operation."
            ),
            quantitative={
                "transformer_loading_pct": transformer_util * 100,
                "remaining_headroom_kw": headroom_kw,
                "charger_power_kw": charger_kw,
                "num_trucks": num_trucks,
            },
            pros=[
                "Extends transformer lifetime",
                "Avoids immediate reinforcement",
            ],
            cons=[
                "Requires charging coordination",
                "May increase charging duration",
            ],
            when_to_use=(
                "When EV charging occurs daily and overlaps with site peak demand."
            ),
            priority="medium",
        ))

    # -------------------------
    # GOOD SCENARIO / SCALE-UP
    # -------------------------
    if cost_savings > 0 and co2_savings > 0 and transformer_util < 0.8:
        recos.append(make_reco(
            title="Scenario is robust – suitable for scale-up",
            category="Summary",
            definition=(
                "The current assumptions deliver cost savings, CO₂ reduction, and grid feasibility."
            ),
            reason=(
                "All key indicators are positive and transformer loading remains within safe limits."
            ),
            quantitative={
                "total_savings_eur_per_year": total_savings,
                "co2_savings_kg_per_year": co2_savings,
                "transformer_loading_pct": transformer_util * 100,
            },
            pros=[
                "Strong operating-cost business case",
                "Technically feasible",
                "Aligned with decarbonisation goals",
            ],
            cons=[
                "Results depend on price and usage assumptions",
                "CAPEX not included",
            ],
            when_to_use="As a baseline scenario for investment or rollout decisions.",
            priority="low",
        ))

    return recos
