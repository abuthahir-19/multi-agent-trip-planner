"""PDF Generator — produces a professional travel report using ReportLab."""
import os
import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus import ListFlowable, ListItem

# Brand colours
PRIMARY = colors.HexColor("#1A6B3C")
SECONDARY = colors.HexColor("#F5A623")
ACCENT = colors.HexColor("#2C3E50")
LIGHT_GREEN = colors.HexColor("#E8F5E9")
LIGHT_AMBER = colors.HexColor("#FFF8E1")
WHITE = colors.white


def generate_trip_pdf(state: dict, output_dir: str = "output") -> str:
    """Generate a complete trip report PDF and return the file path."""
    os.makedirs(output_dir, exist_ok=True)

    prefs = state.get("trip_preferences", {})
    dest = prefs.get("destination", "Destination")
    src = prefs.get("source", "Source")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"TripPlan_{dest}_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Trip Plan: {src} → {dest}",
        author="Multi-Agent Trip Planner",
    )

    styles = _build_styles()
    story = []

    # ── COVER PAGE ──────────────────────────────────────────
    _add_cover_page(story, styles, state)
    story.append(PageBreak())

    # ── SECTION 1: TRANSPORT ────────────────────────────────
    _add_transport_section(story, styles, state)
    story.append(PageBreak())

    # ── SECTION 2: HOTEL ────────────────────────────────────
    _add_hotel_section(story, styles, state)
    story.append(PageBreak())

    # ── SECTION 3: DAY-WISE ITINERARY ───────────────────────
    _add_itinerary_section(story, styles, state)
    story.append(PageBreak())

    # ── SECTION 4: BUDGET REPORT ────────────────────────────
    _add_budget_section(story, styles, state)
    story.append(PageBreak())

    # ── SECTION 5: PACKING CHECKLIST ────────────────────────
    _add_packing_section(story, styles, state)

    # ── SECTION 6: EMERGENCY CONTACTS ───────────────────────
    story.append(Spacer(1, 0.5*cm))
    _add_emergency_section(story, styles, state)

    doc.build(story)
    return filepath


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", fontSize=28, textColor=WHITE,
                                 alignment=TA_CENTER, fontName="Helvetica-Bold",
                                 spaceAfter=6),
        "subtitle": ParagraphStyle("SubTitle", fontSize=14, textColor=SECONDARY,
                                    alignment=TA_CENTER, fontName="Helvetica",
                                    spaceAfter=4),
        "section_header": ParagraphStyle("SHeader", fontSize=16, textColor=WHITE,
                                          fontName="Helvetica-Bold", spaceAfter=8,
                                          backColor=PRIMARY, leftIndent=-10,
                                          rightIndent=-10, leading=22),
        "sub_header": ParagraphStyle("SubHeader", fontSize=12, textColor=PRIMARY,
                                      fontName="Helvetica-Bold", spaceAfter=4,
                                      spaceBefore=8),
        "body": ParagraphStyle("Body", fontSize=10, textColor=ACCENT,
                                fontName="Helvetica", spaceAfter=4, leading=14),
        "bullet": ParagraphStyle("Bullet", fontSize=10, textColor=ACCENT,
                                  fontName="Helvetica", leftIndent=15,
                                  spaceAfter=2, leading=14),
        "highlight": ParagraphStyle("Highlight", fontSize=10, textColor=ACCENT,
                                     fontName="Helvetica-Bold", backColor=LIGHT_GREEN,
                                     spaceAfter=4, leading=14),
        "small": ParagraphStyle("Small", fontSize=8, textColor=colors.grey,
                                  fontName="Helvetica", spaceAfter=2),
        "center": ParagraphStyle("Center", fontSize=10, textColor=ACCENT,
                                  alignment=TA_CENTER, fontName="Helvetica"),
    }


def _section_header(text: str, styles: dict):
    """Return a styled section header table."""
    data = [[Paragraph(f"  {text}", styles["section_header"])]]
    t = Table(data, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PRIMARY]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def _info_table(rows: list, col_widths=None) -> Table:
    """Two-column label → value table."""
    col_widths = col_widths or [5*cm, 11*cm]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREEN),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), PRIMARY),
        ("TEXTCOLOR", (1, 0), (1, -1), ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_AMBER]),
    ]))
    return t


def _add_cover_page(story, styles, state):
    prefs = state.get("trip_preferences", {})
    weather = state.get("weather_data", {})
    budget = state.get("budget_summary", {})

    # Hero banner
    banner_data = [[Paragraph(
        f"<b>✈  AI-POWERED TRIP PLAN</b>", styles["title"]
    )]]
    banner = Table(banner_data, colWidths=["100%"])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
        ("TOPPADDING", (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.4*cm))

    dest = prefs.get("destination", "—")
    src = prefs.get("source", "—")
    story.append(Paragraph(f"{src}  →  {dest}", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=SECONDARY))
    story.append(Spacer(1, 0.3*cm))

    # Trip summary table
    rows = [
        ["Destination", dest],
        ["Source", src],
        ["Travel Dates", prefs.get("travel_dates", "—")],
        ["Duration", f"{prefs.get('num_days', '—')} days"],
        ["Travelers", f"{prefs.get('num_travelers', '—')} person(s)"],
        ["Trip Type", prefs.get("trip_type", "—").title()],
        ["Total Budget", f"₹{int(prefs.get('budget', 0)):,}"],
        ["Est. Total Cost", f"₹{budget.get('total_estimated', 0):,}"],
        ["Weather", weather.get("summary", "See weather section")],
        ["Generated On", datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")],
        ["Generated By", "Multi-Agent AI Trip Planner (LangGraph)"],
    ]
    story.append(_info_table(rows))
    story.append(Spacer(1, 0.5*cm))

    # Budget status
    if budget.get("over_budget"):
        alert = budget.get("budget_alert", "Over budget — see optimization tips.")
        story.append(Paragraph(f"⚠  {alert}", styles["highlight"]))
    else:
        ok = budget.get("budget_status", "Trip fits within budget.")
        story.append(Paragraph(f"✓  {ok}", styles["highlight"]))

    # Weather advisory
    advisory = weather.get("travel_advisory", "")
    if advisory:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f"🌤  Weather Advisory: {advisory}", styles["body"]))


def _add_transport_section(story, styles, state):
    story.append(_section_header("Section 1 — Flights & Transport", styles))
    story.append(Spacer(1, 0.3*cm))

    transport = state.get("transport_data", {})
    prefs = state.get("trip_preferences", {})

    # Recommended
    rec = transport.get("recommended", "")
    if rec:
        story.append(Paragraph(f"Recommended: {rec}", styles["highlight"]))
        story.append(Spacer(1, 0.2*cm))

    # Flights table
    flights = transport.get("flights", [])
    if flights:
        story.append(Paragraph("Flight Options", styles["sub_header"]))
        headers = ["Flight", "Airline", "Departure", "Arrival", "Duration", "Class", "Price/Person", "Total"]
        data = [headers]
        for f in flights[:4]:
            data.append([
                f.get("flight_no", ""),
                f.get("airline", ""),
                f.get("departure", ""),
                f.get("arrival", ""),
                f.get("duration", ""),
                f.get("class", ""),
                f"₹{f.get('price_per_person', 0):,}",
                f"₹{f.get('total_price', 0):,}",
            ])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_AMBER]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))

    # Train options
    trains = transport.get("trains", [])
    if trains:
        story.append(Paragraph("Train Options", styles["sub_header"]))
        headers = ["Train", "Name", "Departure", "Arrival", "Duration", "Class", "Price/Person"]
        data = [headers]
        for tr in trains[:3]:
            data.append([
                tr.get("train_no", ""),
                tr.get("name", ""),
                tr.get("departure", ""),
                tr.get("arrival", ""),
                tr.get("duration", ""),
                tr.get("class", ""),
                f"₹{tr.get('price_per_person', 0):,}",
            ])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_AMBER]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))

    # Transfer tips
    tips = transport.get("transfer_tips", [])
    if tips:
        story.append(Paragraph("Transfer Tips", styles["sub_header"]))
        for tip in tips:
            story.append(Paragraph(f"• {tip}", styles["bullet"]))


def _add_hotel_section(story, styles, state):
    story.append(_section_header("Section 2 — Hotel Recommendations", styles))
    story.append(Spacer(1, 0.3*cm))

    hotel_data = state.get("hotel_data", {})
    hotels = hotel_data.get("hotels", [])
    recommended = hotel_data.get("recommended", {})

    if recommended:
        story.append(Paragraph(f"Top Pick: {recommended.get('name', '')}", styles["sub_header"]))
        rows = [
            ["Category", recommended.get("category", "")],
            ["Area", recommended.get("area", "")],
            ["Rating", f"⭐ {recommended.get('rating', '')} / 5"],
            ["Price/Night", f"₹{recommended.get('price_per_night', 0):,}"],
            ["Amenities", ", ".join(recommended.get("amenities", []))],
            ["Room Types", ", ".join(recommended.get("room_types", []))],
            ["Reviews", recommended.get("reviews", "")],
            ["Booking", recommended.get("booking_link", "")],
        ]
        story.append(_info_table(rows))
        story.append(Spacer(1, 0.4*cm))

    if hotels:
        story.append(Paragraph("All Options", styles["sub_header"]))
        headers = ["Hotel", "Category", "Area", "Rating", "Price/Night", "Booking"]
        data = [headers]
        for h in hotels:
            data.append([
                h.get("name", ""),
                h.get("category", ""),
                h.get("area", ""),
                f"⭐ {h.get('rating', '')}",
                f"₹{h.get('price_per_night', 0):,}",
                h.get("booking_link", ""),
            ])
        t = Table(data, colWidths=[4.5*cm, 3*cm, 2.5*cm, 1.8*cm, 2.2*cm, 3*cm],
                  repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_AMBER]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]))
        story.append(t)

    tips = hotel_data.get("booking_tips", [])
    if tips:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("Booking Tips", styles["sub_header"]))
        for tip in tips:
            story.append(Paragraph(f"• {tip}", styles["bullet"]))


def _add_itinerary_section(story, styles, state):
    story.append(_section_header("Section 3 — Day-wise Itinerary", styles))
    story.append(Spacer(1, 0.3*cm))

    itinerary = state.get("itinerary", {})
    days = itinerary.get("days", [])

    if not days:
        story.append(Paragraph("Itinerary not yet generated.", styles["body"]))
        return

    for day in days:
        day_num = day.get("day", "")
        date = day.get("date", "")
        title = day.get("title", "")
        story.append(KeepTogether([
            Paragraph(f"Day {day_num} — {date}: {title}", styles["sub_header"]),
        ]))

        activities = day.get("activities", [])
        rows = []
        for act in activities:
            time_slot = act.get("time", "")
            activity = act.get("activity", "")
            details = act.get("details", "")
            cost = act.get("cost", "")
            rows.append([time_slot, activity, details, cost])

        if rows:
            data = [["Time", "Activity", "Details", "Est. Cost"]] + rows
            t = Table(data, colWidths=[2.5*cm, 4*cm, 8*cm, 2.5*cm], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREEN]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("WORDWRAP", (0, 0), (-1, -1), True),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(t)

        notes = day.get("notes", "")
        if notes:
            story.append(Paragraph(f"Note: {notes}", styles["small"]))
        story.append(Spacer(1, 0.3*cm))


def _add_budget_section(story, styles, state):
    story.append(_section_header("Section 4 — Budget Report", styles))
    story.append(Spacer(1, 0.3*cm))

    budget = state.get("budget_summary", {})
    prefs = state.get("trip_preferences", {})

    # Summary
    rows = [
        ["Total Budget", f"₹{budget.get('total_budget', 0):,}"],
        ["Total Estimated Cost", f"₹{budget.get('total_estimated', 0):,}"],
        ["Budget per Person", f"₹{budget.get('budget_per_person', 0):,}"],
        ["Estimated per Person", f"₹{budget.get('estimated_per_person', 0):,}"],
        ["Savings / Deficit", f"₹{abs(budget.get('savings_or_deficit', 0)):,} "
                              f"({'Over' if budget.get('over_budget') else 'Under'} budget)"],
    ]
    story.append(_info_table(rows))
    story.append(Spacer(1, 0.3*cm))

    # Breakdown chart (table-based)
    breakdown = budget.get("breakdown", {})
    percentages = budget.get("percentages", {})
    if breakdown:
        story.append(Paragraph("Cost Breakdown", styles["sub_header"]))
        headers = ["Category", "Total Cost", "Per Person", "% of Budget"]
        data = [headers]
        for cat, vals in breakdown.items():
            pct = percentages.get(cat, 0)
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            data.append([
                cat.replace("_", " ").title(),
                f"₹{vals['total']:,}",
                f"₹{vals['per_person']:,}",
                f"{pct}%  {bar[:10]}",
            ])
        t = Table(data, colWidths=[4*cm, 4*cm, 4*cm, 5*cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_AMBER]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)

    tips = budget.get("optimization_tips", [])
    if tips:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("Budget Optimization Tips", styles["sub_header"]))
        for tip in tips:
            story.append(Paragraph(f"💡 {tip}", styles["bullet"]))


def _add_packing_section(story, styles, state):
    story.append(_section_header("Section 5 — Packing Checklist", styles))
    story.append(Spacer(1, 0.3*cm))

    places = state.get("places_data", {})
    checklist = places.get("packing_checklist", [
        "Valid ID / Passport", "Phone charger & power bank", "First aid kit",
        "Comfortable walking shoes", "Sunscreen", "Camera", "Cash & Cards",
        "Reusable water bottle", "Light clothes", "Sunglasses",
    ])

    # Two-column checklist
    mid = len(checklist) // 2 + len(checklist) % 2
    left = checklist[:mid]
    right = checklist[mid:]
    rows = []
    for i in range(mid):
        l = f"☐  {left[i]}" if i < len(left) else ""
        r = f"☐  {right[i]}" if i < len(right) else ""
        rows.append([l, r])

    if rows:
        t = Table(rows, colWidths=[9*cm, 9*cm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GREEN]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
        ]))
        story.append(t)


def _add_emergency_section(story, styles, state):
    story.append(_section_header("Section 6 — Emergency Contacts & Travel Tips", styles))
    story.append(Spacer(1, 0.3*cm))

    places = state.get("places_data", {})
    emergency = places.get("emergency_info", {})

    if emergency:
        rows = [
            ["Emergency", emergency.get("emergency_number", "112")],
            ["Police", emergency.get("police", "100")],
            ["Ambulance", emergency.get("ambulance", "108")],
            ["Fire", emergency.get("fire", "101")],
            ["Tourist Helpline", emergency.get("tourist_helpline", "1363")],
            ["Nearest Hospital", emergency.get("nearest_hospital", "Check locally")],
        ]
        story.append(_info_table(rows))
        story.append(Spacer(1, 0.3*cm))

        em_tips = emergency.get("tips", [])
        if em_tips:
            story.append(Paragraph("Safety Tips", styles["sub_header"]))
            for tip in em_tips:
                story.append(Paragraph(f"• {tip}", styles["bullet"]))

    travel_tips = places.get("travel_tips", [])
    if travel_tips:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("General Travel Tips", styles["sub_header"]))
        for tip in travel_tips:
            story.append(Paragraph(f"• {tip}", styles["bullet"]))

    # Footer note
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
    story.append(Paragraph(
        "Generated by Multi-Agent AI Trip Planner • Powered by LangGraph + Claude AI",
        styles["small"]
    ))
