import os
import json
import requests
import streamlit as st

# --------------------------------------------------
# 0. CONSTANTS
# --------------------------------------------------

diesel_co2_per_l = 2.64  # kg CO2 per litre

grid_co2_g_per_kwh = [
    80, 78, 75, 70, 65, 60, 60, 65, 70, 75, 60, 50,
    45, 45, 50, 60, 70, 80, 90, 95, 90, 83, 78, 76
]

price_eur_per_kwh = [
    0.20, 0.195, 0.19, 0.185, 0.18, 0.18, 0.185, 0.19,
    0.21, 0.24, 0.23, 0.22, 0.20, 0.20, 0.205, 0.21,
    0.23, 0.26, 0.30, 0.33, 0.31, 0.28, 0.24, 0.22
]


# --------------------------------------------------
# 1. MODEL FUNCTIONS
# --------------------------------------------------

def compute_shares(start_hour: int, end_hour: int):
    """Return (flags, shares) for each of 24 hours given a charging window."""
    flags = [0] * 24
    for h in range(24):
        flag = 0
        if start_hour < end_hour:
            if start_hour <= h < end_hour:
                flag = 1
        elif start_hour > end_hour:
            if h >= start_hour or h < end_hour:
                flag = 1
        else:
            flag = 1  # full day
        flags[h] = flag

    total_flags = sum(flags)
    if total_flags == 0:
        shares = [0] * 24
    else:
        shares = [f / total_flags for f in flags]
    return flags, shares


def run_model(
    num_trucks,
    operating_days,
    events_per_truck_per_day,
    battery_kwh,
    start_soc,
    target_soc,
    kwh_per_km,
    diesel_l_per_100,
    diesel_price,
    toll_per_truck,
    start_hour,
    end_hour,
):
    num_trucks = max(1, num_trucks)
    operating_days = max(1, operating_days)
    events_per_truck_per_day = max(0.0, events_per_truck_per_day)
    kwh_per_km = max(0.01, kwh_per_km)

    # 1) SoC & energy
    soc_diff = max(0.0, min(1.0, target_soc) - max(0.0, start_soc))
    kwh_per_event = battery_kwh * soc_diff
    total_daily_energy = kwh_per_event * events_per_truck_per_day * num_trucks
    kwh_per_truck_per_day = total_daily_energy / num_trucks
    km_per_truck_per_day = kwh_per_truck_per_day / kwh_per_km

    # 2) Charging window
    start_h = start_hour % 24
    end_h = end_hour % 24
    flags, shares = compute_shares(start_h, end_h)
    charging_hours = sum(flags)

    # 3) Dynamic grid CO2 & price
    eff_co2_g = sum(g * s for g, s in zip(grid_co2_g_per_kwh, shares))
    eff_co2_kg = eff_co2_g / 1000.0
    eff_price = sum(p * s for p, s in zip(price_eur_per_kwh, shares))

    # 4) Per-km metrics
    diesel_co2_per_km = (diesel_l_per_100 / 100.0) * diesel_co2_per_l
    ev_co2_per_km = kwh_per_km * eff_co2_kg

    diesel_cost_per_km = (diesel_l_per_100 / 100.0) * diesel_price
    ev_cost_per_km = kwh_per_km * eff_price

    # 5) Annual
    annual_dist_per_truck = km_per_truck_per_day * operating_days
    toll_per_km = toll_per_truck / annual_dist_per_truck if annual_dist_per_truck > 0 else 0.0

    diesel_total_cost_per_km = diesel_cost_per_km + toll_per_km
    ev_total_cost_per_km = ev_cost_per_km

    annual_diesel_co2_per_truck = diesel_co2_per_km * annual_dist_per_truck
    annual_ev_co2_per_truck = ev_co2_per_km * annual_dist_per_truck

    annual_diesel_cost_per_truck = diesel_total_cost_per_km * annual_dist_per_truck
    annual_ev_cost_per_truck = ev_total_cost_per_km * annual_dist_per_truck

    return dict(
        soc_diff=soc_diff,
        kwh_per_event=kwh_per_event,
        total_daily_energy_kwh=total_daily_energy,
        kwh_per_truck_per_day=kwh_per_truck_per_day,
        km_per_truck_per_day=km_per_truck_per_day,
        charging_hours=charging_hours,
        start_hour=start_h,
        end_hour=end_h,
        effective_grid_co2_kg_per_kwh=eff_co2_kg,
        effective_grid_price_eur_per_kwh=eff_price,
        diesel_co2_per_km=diesel_co2_per_km,
        ev_co2_per_km=ev_co2_per_km,
        diesel_total_cost_per_km=diesel_total_cost_per_km,
        ev_total_cost_per_km=ev_total_cost_per_km,
        annual_distance_per_truck_km=annual_dist_per_truck,
        annual_diesel_co2_per_truck_kg=annual_diesel_co2_per_truck,
        annual_ev_co2_per_truck_kg=annual_ev_co2_per_truck,
        annual_diesel_cost_per_truck_eur=annual_diesel_cost_per_truck,
        annual_ev_cost_per_truck_eur=annual_ev_cost_per_truck,
    )


def format_results(res: dict) -> str:
    lines = [
        f"SoC difference: {res['soc_diff']:.3f}",
        f"Energy per event: {res['kwh_per_event']:.1f} kWh",
        f"Total daily energy (fleet): {res['total_daily_energy_kwh']:.1f} kWh/day",
        f"Energy per truck per day: {res['kwh_per_truck_per_day']:.1f} kWh/day",
        f"Distance per truck per day: {res['km_per_truck_per_day']:.1f} km/day",
        "",
        f"Charging hours per day: {res['charging_hours']} "
        f"(logic {res['start_hour']}:00 → {res['end_hour']}:00)",
        f"Effective grid CO₂: {res['effective_grid_co2_kg_per_kwh']:.3f} kg/kWh",
        f"Effective price: {res['effective_grid_price_eur_per_kwh']:.3f} €/kWh",
        "",
        f"Diesel CO₂: {res['diesel_co2_per_km']:.3f} kg/km",
        f"EV CO₂: {res['ev_co2_per_km']:.3f} kg/km",
        f"Diesel total cost: {res['diesel_total_cost_per_km']:.3f} €/km",
        f"EV total cost: {res['ev_total_cost_per_km']:.3f} €/km",
        "",
        f"Annual distance per truck: {res['annual_distance_per_truck_km']:.0f} km/year",
        f"Annual diesel CO₂ per truck: {res['annual_diesel_co2_per_truck_kg']:.1f} kg/year",
        f"Annual EV CO₂ per truck: {res['annual_ev_co2_per_truck_kg']:.1f} kg/year",
        f"Annual diesel cost per truck: {res['annual_diesel_cost_per_truck_eur']:.0f} €/year",
        f"Annual EV cost per truck: {res['annual_ev_cost_per_truck_eur']:.0f} €/year",
    ]
    return "\n".join(lines)


# --------------------------------------------------
# 2. GEMINI CALL
# --------------------------------------------------

def call_gemini(question: str, results: dict) -> str:
    api_key = (
        st.secrets.get("GEMINI_API_KEY", None)
        or os.getenv("GEMINI_API_KEY", "")
    )
    if not api_key:
        return "GEMINI_API_KEY is not set in Streamlit secrets or environment."

    if not question.strip():
        return "Please type a question first."

    prompt = (
        "You are an assistant explaining an electric truck fleet model "
        "to a non-technical audience.\n\n"
        "Approximate model results (JSON):\n"
        f"{json.dumps(results)}\n\n"
        "User question:\n"
        f"{question}\n\n"
        "Answer clearly and briefly, using the numbers where helpful."
    )

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    params = {"key": api_key}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        resp = requests.post(url, params=params, json=payload, timeout=30)
    except Exception as e:
        return f"Error calling Gemini: {e}"

    if resp.status_code >= 300:
        return f"Gemini call failed with status {resp.status_code}:\n{resp.text}"

    try:
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return "Got a response from Gemini, but could not read the text field."


# --------------------------------------------------
# 3. STREAMLIT UI
# --------------------------------------------------

st.set_page_config("EV vs Diesel Calculator + Gemini", layout="wide")
st.title("EV vs Diesel Calculator + Gemini Chatbot")

if "model_results" not in st.session_state:
    st.session_state["model_results"] = None

with st.sidebar:
    st.header("Input parameters")

    num_trucks = st.number_input("Number of trucks charging per day", 1, 10000, 10, 1)
    operating_days = st.number_input("Operating days per year", 1, 366, 250, 1)
    events_per_truck = st.number_input("Charging events per truck per day", 0.0, 10.0, 1.0, 0.5)

    st.markdown("---")
    battery_kwh = st.number_input("Battery capacity (kWh)", 1.0, 2000.0, 500.0, 10.0)
    start_soc = st.slider("Start SoC (0–1)", 0.0, 1.0, 0.2, 0.05)
    target_soc = st.slider("Target SoC (0–1)", 0.0, 1.0, 1.0, 0.05)
    kwh_per_km = st.number_input("EV consumption (kWh/km)", 0.1, 10.0, 1.6, 0.1)

    st.markdown("---")
    diesel_l_per_100 = st.number_input("Diesel consumption (L/100 km)", 1.0, 100.0, 28.0, 1.0)
    diesel_price = st.number_input("Diesel price (€/L)", 0.0, 5.0, 1.8, 0.05)
    toll_per_truck = st.number_input("Toll cost per diesel truck per year (€/truck/year)", 0.0, 1_000_000.0, 50_000.0, 1000.0)

    st.markdown("---")
    start_hour = st.slider("Start charging hour", 0, 23, 6, 1)
    end_hour = st.slider("End charging hour", 0, 23, 20, 1)

    run_button = st.button("Run calculation")

if run_button:
    st.session_state["model_results"] = run_model(
        num_trucks=num_trucks,
        operating_days=operating_days,
        events_per_truck_per_day=events_per_truck,
        battery_kwh=battery_kwh,
        start_soc=start_soc,
        target_soc=target_soc,
        kwh_per_km=kwh_per_km,
        diesel_l_per_100=diesel_l_per_100,
        diesel_price=diesel_price,
        toll_per_truck=toll_per_truck,
        start_hour=start_hour,
        end_hour=end_hour,
    )

results = st.session_state["model_results"]

st.subheader("Model results")
if results is None:
    st.info("Click **Run calculation** in the sidebar to see results.")
else:
    st.text(format_results(results))

st.markdown("---")
st.subheader("Ask Gemini about these results")

question = st.text_area("Your question", "")
ask_button = st.button("Ask Gemini")

if ask_button:
    if results is None:
        st.warning("Run the calculation first.")
    else:
        answer = call_gemini(question, results)
        st.text_area("Gemini answer", answer, height=250)
