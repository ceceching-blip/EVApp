def detect_issues(results):
    issues = []

    load = results["load"]
    dv = results["diesel_vs_ev"]
    ec = results["energy_cost"]

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

    # Peak intensity issue (soft)
    if load["new_theoretical_peak_kw"] > 1.5 * load["new_avg_load_kw"]:
        issues.append({
            "id": "high_peak_concentration",
            "severity": "medium",
            "description": "Charging demand is highly concentrated, increasing peak stress."
        })

    return issues

def generate_solution_set(results, issues):
    load = results["load"]
    inp = results["inputs"]
    ec = results["energy_cost"]

    solutions = []

    # ---------- SOLUTION 1: Smart charging ----------
    solutions.append({
        "name": "Smart charging / load management",
        "rank_score": 90,
        "applicable_if": ["capacity_exceeded", "high_peak_concentration"],
        "pros": [
            "No grid upgrade required",
            "Low CAPEX compared to infrastructure upgrades",
            "Fast to implement"
        ],
        "cons": [
            "Requires backend control system",
            "May increase charging time"
        ],
        "quantitative_effect": {
            "peak_reduction_kw": load["required_shaving_kw"],
            "capex_level": "low"
        }
    })

    # ---------- SOLUTION 2: Battery energy storage ----------
    solutions.append({
        "name": "Battery storage (peak shaving)",
        "rank_score": 70,
        "applicable_if": ["capacity_exceeded", "high_peak_concentration"],
        "pros": [
            "Physically reduces peak load",
            "Improves resilience",
            "Future-proof for expansion"
        ],
        "cons": [
            "High CAPEX",
            "Efficiency losses"
        ],
        "quantitative_effect": {
            "required_battery_kwh": load["required_battery_energy_kwh"],
            "capex_level": "high"
        }
    })

    # ---------- SOLUTION 3: Grid / transformer upgrade ----------
    solutions.append({
        "name": "Grid connection / transformer upgrade",
        "rank_score": 50,
        "applicable_if": ["capacity_exceeded"],
        "pros": [
            "Permanent solution",
            "No operational constraints"
        ],
        "cons": [
            "Very high CAPEX",
            "Long lead time",
            "Permitting required"
        ],
        "quantitative_effect": {
            "required_capacity_kva": load["new_theoretical_peak_kw"],
            "capex_level": "very high"
        }
    })

    # Filter only relevant solutions
    issue_ids = {i["id"] for i in issues}
    applicable = [
        s for s in solutions
        if any(i in issue_ids for i in s["applicable_if"])
    ]

    # Rank best → worst
    applicable.sort(key=lambda x: x["rank_score"], reverse=True)

    return applicable[:3]  # max 3
