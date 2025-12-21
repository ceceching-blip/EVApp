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

    issue_ids = {i["id"] for i in issues}
    solutions = []

    # ---------- Common metrics ----------
    overload_kw = max(
        0.0,
        load["new_theoretical_peak_kw"] - inp["site_capacity_limit_kva"]
    )

    overload_ratio = (
        overload_kw / inp["site_capacity_limit_kva"]
        if inp["site_capacity_limit_kva"] > 0
        else 0.0
    )

    # ==================================================
    # SOLUTION 1: Smart charging / staggering
    # ==================================================
    if "capacity_exceeded" in issue_ids or "high_peak_concentration" in issue_ids:
        score = 60
        if inp["charging_window_hours"] >= 8:
            score += 20
        if overload_ratio < 0.3:
            score += 10

        solutions.append({
            "title": "Smart charging / load staggering",
            "rank_score": score,
            "pros": [
                "Lowest CAPEX",
                "Immediate impact",
                "No grid upgrade required"
            ],
            "cons": [
                "Requires operational flexibility",
                "May increase charging duration"
            ],
            "quantitative": {
                "peak_reduction_kw": round(overload_kw, 1),
                "charging_window_hours": inp["charging_window_hours"]
            },
            "when_to_use": "First-line solution when charging peaks are concentrated."
        })

    # ==================================================
    # SOLUTION 2: Reduce charger power / sequential charging
    # ==================================================
    if "high_peak_concentration" in issue_ids:
        solutions.append({
            "title": "Reduce charger power or stagger vehicles",
            "rank_score": 55,
            "pros": [
                "Zero infrastructure CAPEX",
                "Fast operational fix"
            ],
            "cons": [
                "Longer charging sessions",
                "Operational discipline required"
            ],
            "quantitative": {
                "current_charger_power_kw": inp["charger_power_per_truck_kw"],
                "fleet_size": inp["num_trucks"]
            },
            "when_to_use": "When grid capacity is sufficient but peaks are poorly distributed."
        })

    # ==================================================
    # SOLUTION 3: Battery energy storage
    # ==================================================
    if "capacity_exceeded" in issue_ids:
        solutions.append({
            "title": "Battery energy storage (peak shaving)",
            "rank_score": 45,
            "pros": [
                "Physically caps peak demand",
                "Improves resilience"
            ],
            "cons": [
                "High CAPEX",
                "Efficiency losses"
            ],
            "quantitative": {
                "required_battery_kwh": round(load["required_battery_energy_kwh"], 1)
            },
            "when_to_use": "When smart charging alone cannot resolve overload."
        })

    # ==================================================
    # SOLUTION 4: Grid / transformer upgrade
    # ==================================================
    if "capacity_exceeded" in issue_ids and overload_ratio > 0.3:
        solutions.append({
            "title": "Grid connection / transformer upgrade",
            "rank_score": 30,
            "pros": [
                "Permanent solution",
                "Supports long-term expansion"
            ],
            "cons": [
                "Very high CAPEX",
                "Permitting and long lead times"
            ],
            "quantitative": {
                "required_capacity_kva": round(load["new_theoretical_peak_kw"], 1),
                "current_limit_kva": inp["site_capacity_limit_kva"]
            },
            "when_to_use": "When overload is structural or fleet growth is planned."
        })

    # -------- Rank best → worst --------
    solutions.sort(key=lambda x: x["rank_score"], reverse=True)

    return solutions[:3]


