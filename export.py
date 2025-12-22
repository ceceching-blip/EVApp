import pandas as pd

def export_full_report_to_excel(results, issues, solutions, filepath):
    writer = pd.ExcelWriter(filepath, engine="xlsxwriter", engine_kwargs={"options": {"nan_inf_to_errors": True}})


    # ---------- INPUTS ----------
    pd.DataFrame.from_dict(
        results["inputs"], orient="index", columns=["Value"]
    ).to_excel(writer, sheet_name="Inputs")

    # ---------- OVERVIEW ----------
    dv = results["diesel_vs_ev"]
    ec = results["energy_cost"]
    load = results["load"]

    overview = {
        "Total savings (€ / year)": dv["total_savings_incl_toll_eur"],
        "CO₂ savings (kg / year)": dv["co2_savings_kg"],
        "Annual energy (MWh)": ec["annual_energy_mwh"],
        "Capacity OK": load["capacity_ok"],
    }
    pd.DataFrame.from_dict(
        overview, orient="index", columns=["Value"]
    ).to_excel(writer, sheet_name="Overview")

    # ---------- FINANCE ----------
    pd.DataFrame(results["energy_cost"]).to_excel(
        writer, sheet_name="Finance", index=False
    )

    # ---------- CO₂ ----------
    pd.DataFrame(results["co2"], index=[0]).to_excel(
        writer, sheet_name="CO2", index=False
    )

    # ---------- GRID / LOAD ----------
    pd.DataFrame(results["load"], index=[0]).to_excel(
        writer, sheet_name="Grid_Load", index=False
    )

    # ---------- HOURLY PROFILE ----------
    prof = results["charging_profile"]
    hourly_df = pd.DataFrame({
        "hour": list(range(24)),
        "charging_flag": prof["flags"],
        "share": prof["shares"],
        "grid_co2_g_per_kwh": prof["grid_co2_g_per_kwh"],
        "tou_price_eur_per_kwh": prof["tou_price_eur_per_kwh"],
    })
    hourly_df.to_excel(writer, sheet_name="Hourly_Profile", index=False)

    # ---------- ISSUES ----------
    if issues:
        pd.DataFrame(issues).to_excel(writer, sheet_name="Issues", index=False)
    else:
        pd.DataFrame([{"message": "No issues detected"}]).to_excel(
            writer, sheet_name="Issues", index=False
        )

    # ---------- SOLUTIONS ----------
    solution_rows = []
    for s in solutions:
        solution_rows.append({
            "Title": s.get("title"),
            "Priority": s.get("priority", ""),
            "Rank score": s.get("rank_score"),
            "Pros": " | ".join(s.get("pros", [])),
            "Cons": " | ".join(s.get("cons", [])),
            "Quantitative impact": str(s.get("quantitative", s.get("quantitative_effect", {}))),
            "When to use": s.get("when_to_use", ""),
        })

    if solution_rows:
        pd.DataFrame(solution_rows).to_excel(
            writer, sheet_name="Solutions", index=False
        )
    else:
        pd.DataFrame([{"message": "No solutions applicable"}]).to_excel(
            writer, sheet_name="Solutions", index=False
        )

    writer.close()
