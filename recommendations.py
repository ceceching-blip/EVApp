# recommendations.py

def detect_issues(results):
    issues = []

    load = results["load"]
    dv = results["diesel_vs_ev"]

    # Capacity issue
    if not load["capacity_ok"]:
        issues.append({
            "id": "capacity_exceeded",
            "severity": "high",
            "description": "Site connection / grid capacity is exceeded by EV charging load."
        })

    # Financial issue
    if dv["total_savings_incl_toll_eur"] <= 0:
        issues.append({
            "id": "negative_business_case",
            "severity": "medium",
            "description": "EV operating costs are not lower than diesel under current assumptions."
        })

    # Peak concentration issue
    if load["new_theoretical_peak_kw"] > 1.5 * load["new_avg_load_kw"]:
        issues.append({
            "id": "high_peak_concentration",
            "severity": "medium",
            "description": "Charging demand is highly concentrated, creating peak stress."
        })

    return issues
    
def generate_solution_set(results, issues):
    load = results["load"]
    inp = results["inputs"]

    solutions = []

    # -------- Derived severity metrics --------
    overload_kw = max(
        0.0,
        load["new_theoretical_peak_kw"] - inp["site_capacity_limit_kva"]
    )

    overload_ratio = (
        overload_kw / inp["site_capacity_limit_kva"]
        if inp["site_capacity_limit_kva"] > 0
        else 0.0
    )

    # =========================
    # SOLUTION 1: SMART CHARGING
    # =========================
    smart_score = 0

    if overload_kw > 0:
        smart_score += 40
    if inp["charging_window_hours"] >= 8:
        smart_score += 30
    if overload_ratio < 0.3:
        smart_score += 20
    smart_score += 10  # low CAPEX bonus

    solutions.append({
        "title": "Smart charging / load management",
        "rank_score": smart_score,
        "pros": [
            "Lowest CAPEX",
            "Fast to implement",
            "No grid upgrade required"
        ],
        "cons": [
            "Requires charging flexibility",
            "May extend charging duration"
        ],
        "quantitative": {
            "required_peak_reduction_kw": round(overload_kw, 1),
            "charging_window_hours": inp["charging_window_hours"]
        },
        "when_to_use": "Best first option when overload is moderate and time flexibility exists."
    })

    # =========================
    # SOLUTION 2: BATTERY STORAGE
    # =========================
    battery_score = 0

    if overload_kw > 0:
        battery_score += min(overload_kw / 10, 40)
    battery_score += 20  # technical robustness
    battery_score -= 25  # CAPEX penalty

    solutions.append({
        "title": "Battery energy storage (peak shaving)",
        "rank_score": battery_score,
        "pros": [
            "Physically reduces peak load",
            "Improves resilience",
            "Independent of charging behaviour"
        ],
        "cons": [
            "High CAPEX",
            "Efficiency losses"
        ],
        "quantitative": {
            "required_battery_kwh": round(load["required_battery_energy_kwh"], 1)
        },
        "when_to_use": "When smart charging is insufficient or operational flexibility is limited."
    })

    # =========================
    # SOLUTION 3: GRID UPGRADE
    # =========================
    grid_score = 0

    if overload_ratio > 0.5:
        grid_score += 60
    elif overload_ratio > 0.3:
        grid_score += 40
    else:
        grid_score += 10

    grid_score -= 40  # cost + permitting penalty

    solutions.append({
        "title": "Grid connection / transformer upgrade",
        "rank_score": grid_score,
        "pros": [
            "Permanent solution",
            "Supports long-term fleet growth"
        ],
        "cons": [
            "Very high CAPEX",
            "Long lead time",
            "Permitting required"
        ],
        "quantitative": {
            "required_capacity_kva": round(load["new_theoretical_peak_kw"], 1),
            "current_limit_kva": inp["site_capacity_limit_kva"]
        },
        "when_to_use": "When overload is structurally large or long-term expansion is planned."
    })

    # -------- Filter only applicable solutions --------
    issue_ids = {i["id"] for i in issues}

    applicable = []
    for s in solutions:
        if "capacity_exceeded" in issue_ids:
            applicable.append(s)

    # -------- Rank best → worst --------
    applicable.sort(key=lambda x: x["rank_score"], reverse=True)

    return applicable[:3]

