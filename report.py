from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf_report(results, filepath="ev_report.pdf"):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filepath, pagesize=A4)

    story = []

    # Title
    story.append(Paragraph("Electric Vehicle Feasibility Report", styles["Title"]))
    story.append(Spacer(1, 12))

    # Executive summary
    dv = results["diesel_vs_ev"]
    load = results["load"]
    ec = results["energy_cost"]

    summary = f"""
    <b>Total savings (€/year):</b> {dv['total_savings_incl_toll_eur']:.0f}<br/>
    <b>CO₂ savings (kg/year):</b> {dv['co2_savings_kg']:.0f}<br/>
    <b>Annual energy (MWh):</b> {ec['annual_energy_mwh']:.0f}<br/>
    <b>Capacity OK:</b> {"Yes" if load['capacity_ok'] else "No"}
    """
    story.append(Paragraph(summary, styles["Normal"]))
    story.append(Spacer(1, 12))

    # Grid section
    grid_text = f"""
    <b>New theoretical peak (kW):</b> {load['new_theoretical_peak_kw']:.0f}<br/>
    <b>New average load (kW):</b> {load['new_avg_load_kw']:.0f}
    """
    story.append(Paragraph("Grid & Load", styles["Heading2"]))
    story.append(Paragraph(grid_text, styles["Normal"]))

    doc.build(story)
