import os
import time
import base64
from datetime import datetime
import streamlit as st
import json
import smtplib
from email.message import EmailMessage

#--- PERSISTENCE HELPERS
PERSISTENT_KEYS = [
    "records",
    "labor_records",
    "payroll_expenses",
    "planner_tasks",
    "budget",
    "remaining_money",
    "view"
]

try:
    from persistence import delete_report_file, list_saved_reports, load_state, save_report_html, save_state
except ImportError:
    import json
    
    def load_state():
        if os.path.exists("app_state.json"):
            try:
                with open("app_state.json", "r") as f:
                    data = json.load(f)
                # Filter out any streamlit internal widget/form submitter keys
                return {k: v for k, v in data.items() if k in PERSISTENT_KEYS}
            except Exception:
                return {}
        return {}

    def save_state(state):
        data = {k: state[k] for k in PERSISTENT_KEYS if k in state}
        with open("app_state.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

def save_report_html(report_type, html_content, title="Receipt"):
    os.makedirs(f"archive/{report_type}", exist_ok=True)
    filename = f"archive/{report_type}/{title}_{int(time.time())}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filename

def list_saved_reports(report_type):
    folder = f"archive/{report_type}"
    if not os.path.exists(folder):
        return []
    from pathlib import Path
    return list(Path(folder).glob("*.html"))

def delete_report_file(path):
    if os.path.exists(path):
        os.remove(path)

#--- TIER SCHEDULE & PAYROLL CALCULATOR CORE LOGIC ---
TIER_TABLE = {
    0.1: {"Labor": 0.00, "Skill": 0.00, "Forman": 0.00},
    0.2: {"Labor": 62.50, "Skill": 81.25, "Forman": 100.00},
    0.3: {"Labor": 125.00, "Skill": 162.50, "Forman": 200.00},
    0.4: {"Labor": 187.50, "Skill": 243.75, "Forman": 300.00},
    0.5: {"Labor": 250.00, "Skill": 325.00, "Forman": 400.00},
    0.6: {"Labor": 312.50, "Skill": 406.25, "Forman": 500.00},
    0.7: {"Labor": 375.00, "Skill": 487.50, "Forman": 600.00},
    0.8: {"Labor": 437.50, "Skill": 568.75, "Forman": 700.00},
    0.9: {"Labor": 500.00, "Skill": 650.00, "Forman": 800.00}
}

FULL_DAY_RATES = {
    "Labor": 500.00,
    "Skill": 650.00,
    "Forman": 800.00
}

def get_partial_rate(decimal_part: float, role: str) -> float:
    decimal_key = round(decimal_part, 1)
    return TIER_TABLE.get(decimal_key, {}).get(role, 0.0)

def calculate_labor_pay(worked_days: float, role: str):
    full_days = int(worked_days)
    decimal_part = round(worked_days - full_days, 1)
    full_days_pay = full_days * FULL_DAY_RATES.get(role, 0.0)
    partial_days_pay = get_partial_rate(decimal_part, role)
    gross_pay = full_days_pay + partial_days_pay
    return gross_pay, full_days_pay, partial_days_pay

APP_VERSION = "AILYHOUSEPROJECT — Ailyn Project Management System"

# ================================================================
# EDIT HERE #0 — ALL RECEIPTS USE THE SAME V10 VISUAL SYSTEM
# Construction/Materials, Payroll, and Schedule are intentionally unified.
# ================================================================

RECEIVER_EMAIL = "garryboypepito2004@gmail.com"
RECEIVER_AILYN = "ailyn_peps0678@yahoo.com"
AILYN_LOGO_DATA = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJsAAAC5CAYAAAA/BU2xAAANMklEQVR4nO3de1gU9RrA8XcEr5kmnvB21DI1zSOleclQIw0yj2bFelBKCCQJD3hBQVGCRRINEJRFyAviXbSFQBHjYooJKpgim2IqykXIW2haltbj7/zRc56HR0V22Zn3NzP7fv51mHmd/Trs7M6MAmMMCMHQjPcAxHJQbAQNxUbQUGwEDcVG0FBsBA3FRtBQbAQNxUbQUGwEDcVG0FBsBA3FRtBQbAQNxUbQUGwEDcVG0FBsnHxz6juLu0SaYuNgy3cZLCYrmfcY6Cg2ZDFZyeyTdcG8x+DCmvcAliQoZQWLzdrIewxuKDYkXmuD2dbDGbzH4IpiQzAp2odllx7mPQZ3FJvE7EOnsO8vneY9hizQCYJEqm7Usj5znSi0eujIJoETl86wsUvd4Pf793iPIit0ZBNZnqGQvR7qQqE9BsUmop1HstiEKG/eY8gWxSaSxNwdzD1xAe8xZI3es4kgPC2BLU1P5D2G7FFsZpq7JYIl5u7gPYYiUGxmcE9cwHYeyeI9hmJQbE1w/XYd81gTBHmGQt6jKArFZqKztRfZx4kLoaSyjPcoikOxmaDw3Ak2LSEQauqu8h5FkSg2I+05cYB9GD8P7v/1J+9RFIs+ZzPCxvw0NnnlLArNTHRka8SKvRvY4p2xvMdQBTqyNYJCEw/FRtBQbAQNxUbQUGwEDcVG0FBsBA3FRtBQbAQNxUbQUGwEDcVG0FBsBA3FRtBQbASNImMLT0uwuOfRqoHiYgvYFkmhKZSiYpux/jOmy97CewzSRIq4LPynW9fZ3M0RkH48j/coxAyyj62sppz5b10GB04f4z0KMZOsYzt6voTN27oc6OmN6iDb2LJLD7N5W5fDhSuVvEchIpFlbLuO7mPzti6H67freI9CRCS72NYf+IrN27oc7v15n/coRGSyio1uCFY32cQW8tUqFrlnPe8xiIRkEdvsTUvZmv0pvMcgEuMe28dfLmQphXt5j0EQcI3tgxhfllWSz3MEgojLd6PlV6vY2KXuFJqFQT+ynag4w7zXfQaG6nPYmyacocZ24Mwx5r0+BKpu1GJulsgEWmxfF+cyn6RQuHX3DtYmicygxLYxP435bNACY3TdoyWT/ARh5b5N7NOkUAoNiaH6HDtUVizLnS1pbGGp8WzhjmgpN0HqST+ex4YuduY9RoMk+zU6d3MES8xT9v/pNDHS+9EjBAMAAX+Wxijhe2VJYvNcs4htL9gjxarRjAhxYScrzjz6BzIMzSdJy5LzU3mP0SjRY3OO9WN7Tx4Ue7VoLtddYW8t9YCK65cbX1gGRzmnZZ7sUFkx3yGMJFpsl+uuMPfEBVDw4wmxVomuqNzAPoj5L9y4c5P3KI0yVJ9jk6J9oPbmNd6jGE202N5bMRN+qD4v1urQbTz0NfPfEgF37/1h/A9xOqqlH89jU+Lm8tm4GUSLTcmhLd4Zw2L3bYIHDx40fSWMAQjS16eEE4GGcL/EiLcpurksvViE+1ERQlPKiUBDLDa2ogulzG9zOJyqOCv+yiU4cVDSiUBDLDK2zYfSWeD2KLh197Y0GxAxNCWeCDTE4mJblBLDYrKSeY9hFKWeCDTEYmI7WVHGwtNWg1Iu2FTyiUBDLCK2HYV7Wag+TjHX0Sn9RKAhqo9Nq9ex5bvX8h7DaGo4EWiIamM7ffkCC09brZjHbKnpRKAhqowttSiHfbZrJVy8Vs17lAaVXb4A5Ver2AudeghqOxFoiOpiW5r+JQtPW817jEZdv3MTNCtnwcs9+7OUwkze46BQTWznr1Sw8LQE2HV0H+9RjFZWUw5lNeW8x0CjitgyTx5ki1Ni4MefLkm2jT6de8J5elacWRT1AOfHid67gWli/SQLrW+X52Cb7wowRGYKgRO9JNmGpVBsbFU3atn0tYtZsIQffC6a5A2lX+wRnIc5CQAASybPFoo+18P4V96QbJtqpshfo+VXq+CDWF/JLmt699UxoNX4wUvdej/yLaddjxeFNP942F6wh4XqdVD980+SzKBGgli32LVyG4h0+5gAf19WIb5ett0h1NkXXEaMN/qrdDl+15oTtAFG9x8qu7slFPhrVJrQAid6wZnoLMGU0AAAIqb4CwVhKeBkN1KSudREgbGJa/wrb0DR53pYMnl2k48Erz4/QNg9P1FY6xUOXTrYijmeqlhsbN07doEN3hGQ5h8v2PV4UZRfOW6j3xMurdovzBrnJsbqVMciY/Mf7wHnY3MEV/uJkryviXQNEA6FbIMxA16TYvWKZVGxOdmNhIKwFIiY4i/5m+dhve2ErAXrhATPUHi2nY00G5HdKcCTWURsXTrYwlqvcNg9P1F49fkBqC+Rp4NGqI7PF2Y6uoq/clk+PqZhqo9t1jg3uLRqv+A2+j2ux4GYaUHCt8GbYFS/IRKsXRmHONXGNmbAa3AoZBtEugbI5pV4ve9gIXdRshDnHgw2T7UXcc3KOMSpLrZn29lAgmcoZC1YJwzrbSeb0OqbMdZFqE08LMwY68J7FFT8YpPgH+NMR1eojs8XPB00sozsYXHuwUJO0AYY0WeQqOvNOL5f1PWJRYFfVz1qVL8hEKbxg9f7DlZEZI+TkLudafU6uP37r6Ksz330+7DGa4ms9oeiY7N5qj1oNX4wY6yLrHZqU1375WcWmqqD5IPi3Fk1tNdAiHELgqG9Bspi/yg2thljXSDOPVgWO1Fs354+ykL1OiguLzV7XW1btYHlU+eD15uTue8rxcU2os8gCNP4yfKqBrHFfbOZafU6uHvfhMd4NcDrzckQ7xHCdZ8hxCYAA2b2J0HtWrcFrcYPZjq6qj6y+mpvXmOh+jjY8l2G2esa1tsO4tyD4ZWe/bnsQ0Uc2TwcnCHM2Q9s23e0qNDqyyk9zLR6HZx43HN+TdCudVuI+jAQ3Ee/j74vZR3b0BfsIEzjB2MGvGaxkT0sJiuZafU6uP/Xn2atx+etqRDrtgh1v8oytjYtWoFW4wezxrlRZI9RdaOWhep1sMPM+01H9BkE8R4hMOCfj17+LgXZxTZt1CQI08yCrh1sKbRGZJXkM61eB6VVPzZ5Hc+0eRpipgWBVJdb1SdKbJfrrrDecxzNWsfg514CrcYPnOxGUmQm+mL3OhaWGg8PWNOfCTxr3DSIdA2UdN+bHdu+kkPMd+MSqKm72uR1REzxB//xHpL8RU9VnpXdt9Qv9+wn+t/14rVqpk3Vwa4jTX8iwOh+QyHeIwT6dnlOktfCrNiWZaxhYanxZg3Qqf0/oFJ3QLJ/UW4JgcyURzIETJgOLZu3NHr5ovJSyCk9bPTyu+cnSnb0zik9zN6N9gHHgfaQayho0jps2raHVe7BMHn4ONFnbNJ9o9d++Zn5bQyHjO/l+YWvOcL/M8eknRyfvZWZEhuGgAnTYd0n4RCVmQSrc7aZ9LN1v/4C01YHwKnKs+xzE/dFY0y+6iPXUMBGhbmqMjQ16fzMs8KKjxYKf2w2CIsmeUNzK9OOK9GZSTAhyptVXK8R7W2ISbFFZSaxiVGfQqXJjwul9/wYnOxGCn9sNggPf5UX4uwr3Ek+KSyfOh86Pt3B6PXlGQphpHYqpB/PEyU4o3P/aPV8pj+WbfSKh/T6FzjZ2UO3Dp3B2soKrIRmYGVlDdZWVmDdzAqsrazBupkVtGnZukmDE9PNecddmPOOO2w4qGdRe5LgkhH/GdyNOzdhStxcCJrkzUKdfc06ajQa28Ezx5jvxnC4YOTjomY6ukLAhOnQhT4nky1PB43g6aAB/bFsFp2ZBCWVZY3+zLKMNVBSWcbiPw6BbjadmvTaPjG2lfs2saySfOjawRa6NnKnt33fwWBu+QSXZvjbgmb425BrKGBRmUmNLv/bvd/BY00QzB7nxv49yMHk1/qJsf3/sEvUzXGgveA40F7y7ajuhhciX6J9NypXaUU5zJQ70kf1G2LSr4fam9dY+dUqo5dvYd0chvd+2SLfbijyYYCm6GbTSdIXt2sHW6Gx97P1nbh0Wt3/up+Afo0SNBQbQUOxETQUG0Gj+hOEovJSyDUUGv2mPPh9H5NOJorLS1l2qfGX8zj0H2rK6lUFNbbkg6noZ2K7jmRB8cUfjF7e5qn2rHUL469n+/b0Ufjq2DdGL3/rt4/g/JVK9P3g4eDM/eMW1M/ZArZFMl32FrTtkb+1at4SbiUd5x4bvWcjaCg2ggb1PVvbVm0gaJI35iYh4/h+OFNzwejl/cd7QMvmLYxevrjcAHk/FBq9vMuI8dDLtrvRy6sJamw8LkEqv1rFenfuYfTymuFvQysTThC6d+wMbVq2Mnr5D+0nWuztiqr/Ip7IB71nI2goNoKGYiNoKDaChmIjaCg2goZiI2goNoKGYiNoKDaChmIjaCg2goZiI2goNoKGYiNoKDaChmIjaCg2goZiI2goNoKGYiNoKDaChmIjaCg2goZiI2goNoKGYiNoKDaChmIjaCg2goZiI2goNoKGYiNoKDaChmIjaCg2goZiI2goNoKGYiNoKDaChmIjaCg2goZiI2goNoLmfyASapdvGeRmAAAAAElFTkSuQmCC"
SENDER_EMAIL = "garryboypepito71@gmail.com"
SENDER_PASSWORD = "fhyv cimp gync wjmj"

st.set_page_config(
    page_title="Ailyn Project Management System",
    page_icon="🅰️",
    layout="wide",
)

# Load persisted state safely
state_data = load_state()
for key in PERSISTENT_KEYS:
    if key in state_data and key not in st.session_state:
        st.session_state[key] = state_data[key]

if "records" not in st.session_state:
    st.session_state.records = []
if "labor_records" not in st.session_state:
    st.session_state.labor_records = []
if "payroll_expenses" not in st.session_state:
    st.session_state.payroll_expenses = []
if "planner_tasks" not in st.session_state:
    st.session_state.planner_tasks = []
if "budget" not in st.session_state:
    st.session_state.budget = 0.0
if "remaining_money" not in st.session_state:
    st.session_state.remaining_money = 0.0
if "view" not in st.session_state:
    st.session_state.view = "home"
if "selected_role" not in st.session_state:
    st.session_state.selected_role = "Labor"

def set_view(v):
    st.session_state.view = v
    persist_state()
    st.rerun()

def total_materials():
    return sum(r["amount"] for r in st.session_state.records if r["type"] == "material")

def total_expenses():
    return sum(r["amount"] for r in st.session_state.records if r["type"] == "expense")

def total_excess():
    return sum(r["amount"] for r in st.session_state.records if r["type"] == "excess")

def get_total():
    return total_materials() + total_expenses()

def get_balance():
    return float(st.session_state.budget) + total_excess() - get_total()

def clear_all():
    st.session_state.records = []
    st.session_state.labor_records = []
    st.session_state.payroll_expenses = []
    st.session_state.planner_tasks = []
    st.session_state.budget = 0.0
    st.session_state.remaining_money = 0.0
    st.session_state.view = "home"
    st.session_state.selected_role = "Labor"
    save_state(st.session_state)

def persist_state():
    save_state(st.session_state)

def add_tx(name, price, qty, delivery, ttype, sender):
    p = float(price or 0.0)
    q = int(qty or 0)
    d = float(delivery or 0.0)
    if p <= 0 or q <= 0:
        return False
    amount = (p * q) + d if ttype == "material" else p
    st.session_state.records.append({
        "id": str(time.time()),
        "date": datetime.now().strftime("%b %d, %Y"),
        "name": name.upper(),
        "price": p,
        "qty": q,
        "delivery": d,
        "amount": float(amount),
        "type": ttype,
        "sender": sender
    })
    persist_state()
    return True

# ================================================================
# EDIT HERE #1 — UNIVERSAL RECEIPT DESIGN: CONSTRUCTION / MATERIALS
# All receipt templates use the same Ailyn V10 visual system.
# ================================================================

# ================================================================
# EDIT HERE #8 — MAIN RECEIPTS + V10 UI/LOGO
# Receipt layouts above come from the MAIN receipt design, while the
# V10 application shell, colors, logo, and responsive behavior remain.
# Export is UNIVERSAL NATURAL RATIO only — no phone/laptop ratio selector.
# ================================================================

# ================================================================
# V10 RECEIPT REPLACEMENT — BUILD_HTML_REPORT
# EDIT HERE: This receipt design was replaced with the MAIN receipt layout
# and restyled to match the V10 UI/logo system.
# Phone/tablet/desktop use the same responsive receipt.
# ================================================================

# ================================================================
# MAIN RECEIPTS APPLIED EXACTLY — DO NOT USE V10 RECEIPT DESIGN
# MATERIALS + PAYROLL BELOW ARE COPIED VERBATIM FROM MAIN RECEIPT CODE
# ================================================================


# ================================================================
# EDIT HERE — RECEIPT LOOK ONLY v2
# MAIN receipt structure/data/calculations are preserved.
# The CSS inserted inside the three receipt functions controls only
# the visual presentation and responsive fit in the V10 system.
# ================================================================
def build_html_report(records, budget, custom_title="INVENTORY RECEIPT"):
    material_and_expense_records = [r for r in records if r["type"] in ["material", "expense"]]
    excess_records = [r for r in records if r["type"] == "excess"]
    material_total = sum(r["amount"] for r in material_and_expense_records)
    excess_total = sum(r["amount"] for r in excess_records)
    remaining_balance = get_balance()
    date_now = datetime.now().strftime("%B %d, %Y")
    sobra_amount = 0.0
    kulang_amount = 0.0
    if remaining_balance > 0:
        sobra_amount = remaining_balance
    elif remaining_balance < 0:
        kulang_amount = abs(remaining_balance)
    balance_color = "#ffffff" if budget <= 0 else ("#e57373" if remaining_balance < 0 else "#a5d6a7")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css?family=Inter:wght@400;600;700&display=swap');
body {{ font-family: 'Inter', sans-serif; background-color: #f0f4f0; margin: 0; padding: 20px; color: #333; }}
.receipt-container {{ max-width: 1000px; margin: auto; background: #fff; padding: 30px; border-radius: 4px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border-top: 10px solid #1b5e20; }}
.header {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; margin-bottom: 30px; border-bottom: 2px solid #f0f0f0; padding-bottom: 15px; }}
.company-info h1 {{ color: #1b5e20; margin: 0; font-size: 24px; letter-spacing: -1px; }}
.company-info p {{ margin: 4px 0; font-size: 12px; color: #666; }}
.receipt-meta {{ text-align: left; margin-top: 10px; }}
@media (min-width: 768px) {{ .receipt-meta {{ text-align: right; margin-top: 0; }} }}
.receipt-meta h2 {{ margin: 0; font-size: 16px; text-transform: uppercase; color: #1b5e20; }}
.receipt-meta p {{ margin: 4px 0; font-size: 12px; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }}
th {{ background-color: #1b5e20; color: #ffffff; text-align: left; padding: 10px; text-transform: uppercase; letter-spacing: 1px; }}
td {{ padding: 10px 8px; border-bottom: 1px solid #f0f0f0; }}
.qty-col, .desccol, .pricecol, .deliverycol, .totalcol {{ text-align: left; }}
.desccol {{ font-weight: 700; color: #1b5e20; }}
.summary-container {{ display: flex; justify-content: flex-end; }}
.summary-table {{ width: 100%; }}
@media (min-width: 768px) {{ .summary-table {{ width: 420px; }} }}
.grand-total {{ background: #1b5e20; color: white; padding: 20px; border-radius: 4px; margin-top: 15px; }}
.balance-info {{ font-size: 13px; line-height: 1.8; }}
.balance-row {{ display: flex; justify-content: space-between; }}
.material-row {{ font-size: 18px; font-weight: bold; }}
.final-balance-row {{ display: flex; justify-content: space-between; border-top: 1px dashed rgba(255,255,255,0.4); margin-top: 8px; padding-top: 8px; font-size: 18px; font-weight: bold; }}
.footer {{ margin-top: 30px; text-align: center; font-size: 9px; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }}
.save-btn-container {{ text-align: center; margin-bottom: 25px; }}
.save-img-btn {{ background-color: #1b5e20; color: white; border: none; padding: 12px 24px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }}
.save-img-btn:hover {{ background-color: #2e7d32; }}
@media print {{ .save-btn-container {{ display: none; }} }}
/* V10 RECEIPT VISUAL REDESIGN — LOOK ONLY */
:root {{ --v10-green:#075d2c; --v10-green-2:#0b7a3b; --v10-gold:#d6a84f; --v10-cream:#f7f5ee; --v10-ink:#17352a; --v10-line:#dfe7df; }}
body {{ background:linear-gradient(180deg,#eef5ef 0%,#f8faf7 100%) !important; color:var(--v10-ink) !important; }}
.receipt-container, .receipt-card, #receiptContent {{ border-top-color:var(--v10-green) !important; border-radius:18px !important; box-shadow:0 16px 45px rgba(7,93,44,.12),0 2px 8px rgba(0,0,0,.05) !important; position:relative; overflow:hidden; }}
.receipt-container::before, .receipt-card::before, #receiptContent::before {{ content:"⌂"; position:absolute; top:22px; left:28px; width:44px; height:44px; border-radius:12px; background:var(--v10-green); color:#fff; display:grid; place-items:center; font-size:25px; font-weight:800; box-shadow:0 5px 14px rgba(7,93,44,.22); }}
.company-info, .title {{ padding-left:62px; }}
.company-info h1, .title h1 {{ color:var(--v10-green) !important; letter-spacing:-.5px !important; font-weight:800 !important; }}
.company-info p, .title p {{ color:#617168 !important; }}
.receipt-meta h2, .meta h3 {{ color:var(--v10-green) !important; }}
.receipt-meta, .meta {{ background:var(--v10-cream); border:1px solid #eadfbe; border-radius:12px; padding:12px 15px; }}
th {{ background:var(--v10-green) !important; }}
thead tr {{ box-shadow:inset 0 -2px 0 var(--v10-gold); }}
td {{ border-bottom-color:var(--v10-line) !important; }}
tr:nth-child(even) td {{ background:#fbfcfa; }}
.desccol, .task-name {{ color:var(--v10-green) !important; }}
.grand-total {{ background:linear-gradient(135deg,var(--v10-green),#064622) !important; border:1px solid rgba(214,168,79,.45); border-radius:14px !important; box-shadow:0 10px 25px rgba(7,93,44,.16); }}
.task-card {{ border-left-color:var(--v10-gold) !important; border-radius:14px !important; box-shadow:0 6px 18px rgba(7,93,44,.07); }}
.task-date {{ color:var(--v10-green) !important; background:#eef7f0 !important; }}
.save-img-btn {{ background:var(--v10-green) !important; border-radius:10px !important; border:1px solid var(--v10-gold) !important; box-shadow:0 6px 16px rgba(7,93,44,.18) !important; }}
.save-img-btn:hover {{ background:var(--v10-green-2) !important; }}
.footer {{ color:#718078 !important; }}
@media (max-width:700px) {{ body {{ padding:8px !important; }} .receipt-container, .receipt-card, #receiptContent {{ padding:18px !important; border-radius:14px !important; }} .receipt-container::before, .receipt-card::before, #receiptContent::before {{ top:15px; left:16px; width:36px; height:36px; font-size:20px; }} .company-info, .title {{ padding-left:48px; }} .company-info h1, .title h1 {{ font-size:20px !important; }} .receipt-meta, .meta {{ padding:9px 10px; }} th, td {{ padding:8px 6px !important; font-size:11px !important; }} .save-img-btn {{ width:100%; }} }}

/* ================================================================
   AILYN HOUSE RECEIPT VISUAL OVERHAUL — LOOK ONLY
   Structure, calculations, records and export logic are unchanged.
   ================================================================ */
:root {{ --ah-green:#064f2a; --ah-green-2:#0b6b38; --ah-gold:#c89b3c; --ah-gold-soft:#f5ecd8; --ah-cream:#fbfaf5; --ah-ink:#17372a; --ah-muted:#68776f; --ah-line:#d9e1da; }}
body {{ background:radial-gradient(circle at 15% 0%,#edf6ef 0,#f7faf7 35%,#eef4ef 100%) !important; color:var(--ah-ink) !important; }}
#receiptContent, .receipt-container, .receipt-card {{ background:#fff !important; border:1px solid #dfe7df !important; border-top:6px solid var(--ah-green) !important; border-radius:22px !important; box-shadow:0 24px 60px rgba(6,79,42,.13),0 4px 14px rgba(20,45,30,.06) !important; overflow:hidden !important; }}
#receiptContent {{ position:relative !important; }}
#receiptContent::after, .receipt-container::after, .receipt-card::after {{ content:""; position:absolute; top:0; right:0; width:180px; height:6px; background:var(--ah-gold); opacity:.95; }}
.company-info h1, .title h1, #receiptContent h1 {{ color:var(--ah-green) !important; font-weight:900 !important; letter-spacing:.4px !important; }}
.company-info p, .title p {{ color:var(--ah-muted) !important; }}
.receipt-meta, .meta {{ background:linear-gradient(135deg,#fffdf8,#f7f4e9) !important; border:1px solid #eadfbe !important; border-radius:14px !important; box-shadow:0 4px 12px rgba(120,92,35,.06); }}
.receipt-meta h2, .meta h3 {{ color:var(--ah-green) !important; font-weight:900 !important; }}
#receiptContent table {{ border-collapse:separate !important; border-spacing:0 !important; overflow:hidden !important; }}
#receiptContent th {{ background:linear-gradient(135deg,var(--ah-green),var(--ah-green-2)) !important; color:#fff !important; font-weight:800 !important; border:0 !important; }}
#receiptContent td {{ color:#263b31 !important; border-bottom:1px solid var(--ah-line) !important; background:#fff !important; }}
#receiptContent tr:nth-child(even) td {{ background:#f8fbf8 !important; }}
#receiptContent tr:hover td {{ background:#f5f8f5 !important; }}
.desccol {{ color:var(--ah-green) !important; font-weight:900 !important; font-size:13px !important; }}
#receiptContent td.desccol, #receiptContent td:nth-child(3) {{ color:var(--ah-green) !important; font-weight:800 !important; }}
.grand-total {{ background:linear-gradient(145deg,#063f22,#08703a) !important; border:1px solid rgba(200,155,60,.65) !important; border-radius:18px !important; box-shadow:0 16px 30px rgba(6,79,42,.18) !important; }}
.final-balance-row {{ border-top-color:rgba(255,255,255,.28) !important; }}
.save-img-btn {{ background:linear-gradient(135deg,var(--ah-green),var(--ah-green-2)) !important; border:1px solid var(--ah-gold) !important; border-radius:12px !important; padding:13px 25px !important; box-shadow:0 8px 20px rgba(6,79,42,.18) !important; }}
.save-img-btn:hover {{ transform:translateY(-1px); filter:brightness(1.05); }}
.footer {{ color:#7b8981 !important; }}
#receiptContent > table:first-of-type {{ background:linear-gradient(135deg,#fbfdfb,#fffdf7) !important; border:1px solid #e4eae5 !important; border-radius:16px !important; padding:4px !important; box-shadow:0 8px 20px rgba(6,79,42,.06); }}
#receiptContent > table:first-of-type h1 {{ font-size:28px !important; }}
#receiptContent > table:first-of-type h3 {{ color:var(--ah-green) !important; font-weight:900 !important; }}
#receiptContent table td {{ word-break:normal !important; overflow-wrap:anywhere !important; }}
#receiptContent table:nth-of-type(2) td:first-child {{ color:var(--ah-green) !important; font-weight:800 !important; }}
.task-card {{ background:linear-gradient(145deg,#fff,#f7faf7) !important; border:1px solid #dce6df !important; border-left:6px solid var(--ah-green) !important; border-radius:17px !important; box-shadow:0 10px 24px rgba(6,79,42,.08) !important; }}
.task-date {{ color:var(--ah-green) !important; background:var(--ah-gold-soft) !important; border:1px solid #e6d3a6 !important; }}
.task-name {{ color:var(--ah-green) !important; font-weight:900 !important; }}
.task-status {{ border:1px solid rgba(6,79,42,.12); }}
@media (max-width:700px) {{
  body {{ padding:7px !important; }}
  #receiptContent, .receipt-container, .receipt-card {{ border-radius:16px !important; }}
  #receiptContent > table:first-of-type h1 {{ font-size:21px !important; }}
  .company-info h1, .title h1 {{ font-size:21px !important; }}
  .desccol, #receiptContent td:nth-child(3) {{ font-size:12px !important; }}
  #receiptContent th, #receiptContent td {{ padding:7px 5px !important; }}
}}

/* ================================================================
   AILYN HOUSE — RECEIPT REDESIGN v2 — LOOK ONLY
   No data, calculations, state, or export logic changed.
   ================================================================ */
:root {{ --ahg:#075d2c; --ahg2:#0b7a3b; --ahgold:#c9a34a; --ahink:#17352a; --ahmuted:#68776f; --ahline:#dfe7df; --ahsoft:#f5f8f4; }}
* {{ box-sizing:border-box; }}
html, body {{ width:100%; min-width:0; overflow-x:hidden !important; }}
body {{ margin:0 !important; padding:12px !important; background:#eef3ef !important; color:var(--ahink) !important; font-family:'Inter','Segoe UI',Arial,sans-serif !important; }}
#receiptContent {{ width:100% !important; max-width:980px !important; margin:0 auto !important; padding:28px 30px 22px !important; background:#fff !important; border:1px solid #d8e2da !important; border-top:7px solid var(--ahg) !important; border-radius:20px !important; box-shadow:0 12px 30px rgba(7,93,44,.10) !important; overflow:hidden !important; position:relative !important; }}
#receiptContent::before {{ content:'' !important; display:block !important; position:absolute !important; left:0 !important; top:0 !important; width:125px !important; height:7px !important; background:var(--ahgold) !important; }}
.save-btn-container {{ margin:0 auto 10px !important; max-width:980px !important; }}
.save-img-btn {{ background:var(--ahg) !important; border:1px solid var(--ahgold) !important; border-radius:9px !important; padding:9px 18px !important; font-size:12px !important; box-shadow:0 5px 12px rgba(7,93,44,.14) !important; }}
.header {{ display:flex !important; gap:22px !important; align-items:center !important; justify-content:space-between !important; padding:4px 0 20px !important; margin:0 0 20px !important; border-bottom:1px solid var(--ahline) !important; }}
.company-info {{ position:relative !important; padding-left:64px !important; min-width:0 !important; }}
.company-info::before {{ content:'⌂' !important; position:absolute !important; left:0 !important; top:1px !important; width:48px !important; height:48px !important; display:grid !important; place-items:center !important; border-radius:13px !important; background:var(--ahg) !important; color:white !important; font-size:27px !important; font-weight:800 !important; box-shadow:0 5px 12px rgba(7,93,44,.18) !important; }}
.company-info h1 {{ margin:0 !important; color:var(--ahg) !important; font-size:29px !important; line-height:1 !important; font-weight:900 !important; letter-spacing:.5px !important; }}
.company-info p {{ margin:5px 0 0 !important; color:var(--ahmuted) !important; font-size:11px !important; line-height:1.3 !important; }}
.receipt-meta {{ min-width:190px !important; padding:13px 16px !important; border:1px solid #e8d9b4 !important; border-radius:13px !important; background:#fffaf0 !important; text-align:right !important; }}
.receipt-meta h2 {{ margin:0 0 6px !important; color:var(--ahg) !important; font-size:18px !important; font-weight:900 !important; text-transform:uppercase !important; }}
.receipt-meta p {{ margin:3px 0 !important; color:#43534b !important; font-size:11px !important; }}
#receiptContent > table {{ width:100% !important; table-layout:fixed !important; margin:0 0 18px !important; border-collapse:separate !important; border-spacing:0 !important; }}
#receiptContent > table thead th {{ background:var(--ahg) !important; color:#fff !important; padding:10px 9px !important; border:0 !important; font-size:11px !important; letter-spacing:.45px !important; white-space:normal !important; }}
#receiptContent > table thead th:first-child {{ border-radius:10px 0 0 10px !important; }}
#receiptContent > table thead th:last-child {{ border-radius:0 10px 10px 0 !important; }}
#receiptContent > table tbody td {{ padding:9px 8px !important; border-bottom:1px solid var(--ahline) !important; font-size:11px !important; line-height:1.25 !important; overflow-wrap:anywhere !important; word-break:normal !important; }}
#receiptContent > table tbody tr:nth-child(even) td {{ background:#f8fbf8 !important; }}
#receiptContent > table tbody tr:hover td {{ background:#f2f7f3 !important; }}
#receiptContent > table th:nth-child(1), #receiptContent > table td:nth-child(1) {{ width:14% !important; }}
#receiptContent > table th:nth-child(2), #receiptContent > table td:nth-child(2) {{ width:9% !important; text-align:center !important; }}
#receiptContent > table th:nth-child(3), #receiptContent > table td:nth-child(3) {{ width:30% !important; }}
#receiptContent > table th:nth-child(4), #receiptContent > table td:nth-child(4) {{ width:17% !important; text-align:right !important; }}
#receiptContent > table th:nth-child(5), #receiptContent > table td:nth-child(5) {{ width:14% !important; text-align:right !important; }}
#receiptContent > table th:nth-child(6), #receiptContent > table td:nth-child(6) {{ width:16% !important; text-align:right !important; }}
#receiptContent > table td:nth-child(3) {{ color:var(--ahg) !important; font-weight:800 !important; }}
.summary-container {{ display:flex !important; justify-content:flex-end !important; }}
.summary-table {{ width:410px !important; max-width:100% !important; }}
.grand-total {{ padding:17px 18px !important; border-radius:15px !important; background:linear-gradient(145deg,#064a27,#08733c) !important; border:1px solid rgba(201,163,74,.8) !important; box-shadow:0 10px 22px rgba(7,93,44,.14) !important; }}
.balance-info {{ font-size:12px !important; }}
.material-row {{ font-size:18px !important; }}
.final-balance-row {{ font-size:17px !important; }}
.footer {{ margin-top:18px !important; padding-top:12px !important; font-size:8px !important; color:#819087 !important; letter-spacing:1px !important; }}
@media (max-width:700px) {{
 body {{ padding:5px !important; }}
 #receiptContent {{ padding:17px 12px 14px !important; border-radius:14px !important; border-top-width:5px !important; }}
 #receiptContent::before {{ height:5px !important; width:70px !important; }}
 .header {{ gap:10px !important; padding-bottom:13px !important; margin-bottom:13px !important; align-items:flex-start !important; }}
 .company-info {{ padding-left:45px !important; }}
 .company-info::before {{ width:34px !important; height:34px !important; border-radius:9px !important; font-size:19px !important; }}
 .company-info h1 {{ font-size:20px !important; }}
 .company-info p {{ font-size:8.5px !important; }}
 .receipt-meta {{ min-width:125px !important; padding:8px 9px !important; }}
 .receipt-meta h2 {{ font-size:12px !important; }}
 .receipt-meta p {{ font-size:8px !important; }}
 #receiptContent > table thead th {{ padding:7px 4px !important; font-size:8px !important; }}
 #receiptContent > table tbody td {{ padding:7px 4px !important; font-size:8.5px !important; }}
 .summary-table {{ width:100% !important; }}
 .grand-total {{ padding:13px !important; }}
 .material-row {{ font-size:14px !important; }}
 .final-balance-row {{ font-size:14px !important; }}
 .footer {{ font-size:6.5px !important; }}
 .save-img-btn {{ width:100% !important; }}
}}
@media print {{ body {{ padding:0 !important; background:#fff !important; }} #receiptContent {{ max-width:none !important; box-shadow:none !important; }} }}

</style>
</head>
<body>
<div class="save-btn-container">
<button class="save-img-btn" onclick="saveAsImage()">SAVE RECEIPT IMAGE</button>
</div>
<div class="receipt-container" id="receiptContent">
<div class="header">
<div class="company-info">
<h1>AILYN HOUSE</h1>
<p>Official Materials & Expense Receipt</p>
<p>Management System {APP_VERSION}</p>
<p>Backup Receiver: <i>{RECEIVER_AILYN}</i></p>
</div>
<div class="receipt-meta">
<h2>{custom_title}</h2>
<p>Date: {date_now}</p>
</div>
</div>
<table>
<thead>
<tr>
<th>Date</th>
<th class="qty-col">Qty</th>
<th class="desccol">Description</th>
<th class="pricecol">Unit Price</th>
<th class="deliverycol">Delivery</th>
<th class="totalcol">Total</th>
</tr>
</thead>
<tbody>"""
    
    for r in material_and_expense_records:
        html += f"""
<tr>
<td>{r['date']}</td>
<td class="qty-col">{r['qty']}</td>
<td class="desccol">{r['name']}</td>
<td class="pricecol">{float(r.get('price', r['amount'])):,.2f}</td>
<td class="deliverycol">{float(r['delivery']):,.2f}</td>
<td class="totalcol">PHP {float(r['amount']):,.2f}</td>
</tr>"""
        
    html += f"""
</tbody>
</table>
<div class="summary-container">
<div class="summary-table">
<div class="grand-total">
<div class="balance-info">
<div class="balance-row material-row">
<span>Material/Expense Total:</span>
<span>PHP {material_total:,.2f}</span>
</div>
<div class="balance-row" style="font-size: 13px; margin-top: 4px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 4px;">
<span>Excess Money Total:</span>
<span style="color: #a5d6a7;">PHP {excess_total:,.2f}</span>
</div>
<div class="balance-row" style="font-size: 13px;">
<span>Total Budget:</span>
<span>PHP {budget:,.2f}</span>
</div>
"""
    if sobra_amount > 0:
        html += f"""
<div class="final-balance-row">
<span>EXCESS</span>
<span style="color: #a5d6a7;">PHP {sobra_amount:,.2f}</span>
</div>"""
    if kulang_amount > 0:
        html += f"""
<div class="final-balance-row">
<span>SHORTAGE</span>
<span style="color: #e57373;">PHP {kulang_amount:,.2f}</span>
</div>"""
        
    html += f"""
<div class="final-balance-row">
<span>FINAL BALANCE</span>
<span style="color: {balance_color};">PHP {remaining_balance:,.2f}</span>
</div>
</div>
</div>
</div>
</div>
<div class="footer">
This document was electronically generated and is valid without signature.
</div>
</div>
<script>
function saveAsImage() {{
    const element = document.getElementById('receiptContent');
    html2canvas(element, {{ scale: 2, useCORS: true }}).then(canvas => {{
        const link = document.createElement('a');
        link.download = '{custom_title.replace(" ", "_")}_Receipt.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
    }});
}}
</script>
</body>
</html>"""
    return html

# ================================================================
# V10 RECEIPT REPLACEMENT — GENERATE_PAYROLL_HTML
# EDIT HERE: This receipt design was replaced with the MAIN receipt layout
# and restyled to match the V10 UI/logo system.
# Phone/tablet/desktop use the same responsive receipt.
# ================================================================
def generate_payroll_html(labor_records, expense_records, remaining_money=0.0, custom_title="INVENTORY RECEIPT"):
    date_str = datetime.now().strftime("%B %d, %Y | %I:%M%p")
    total_labor = sum(r['net'] for r in labor_records)
    total_expenses = sum(e['price'] for e in expense_records)
    sub_total = total_labor + total_expenses
    grand_total = sub_total - (remaining_money or 0.0)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
.save-btn-container {{ text-align: center; margin-bottom: 25px; }}
.save-img-btn {{ background-color: #1b5e20; color: white; border: none; padding: 12px 24px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }}
.save-img-btn:hover {{ background-color: #2e7d32; }}
@media print {{ .save-btn-container {{ display: none; }} }}
/* V10 RECEIPT VISUAL REDESIGN — LOOK ONLY */
:root {{ --v10-green:#075d2c; --v10-green-2:#0b7a3b; --v10-gold:#d6a84f; --v10-cream:#f7f5ee; --v10-ink:#17352a; --v10-line:#dfe7df; }}
body {{ background:linear-gradient(180deg,#eef5ef 0%,#f8faf7 100%) !important; color:var(--v10-ink) !important; }}
.receipt-container, .receipt-card, #receiptContent {{ border-top-color:var(--v10-green) !important; border-radius:18px !important; box-shadow:0 16px 45px rgba(7,93,44,.12),0 2px 8px rgba(0,0,0,.05) !important; position:relative; overflow:hidden; }}
.receipt-container::before, .receipt-card::before, #receiptContent::before {{ content:"⌂"; position:absolute; top:22px; left:28px; width:44px; height:44px; border-radius:12px; background:var(--v10-green); color:#fff; display:grid; place-items:center; font-size:25px; font-weight:800; box-shadow:0 5px 14px rgba(7,93,44,.22); }}
.company-info, .title {{ padding-left:62px; }}
.company-info h1, .title h1 {{ color:var(--v10-green) !important; letter-spacing:-.5px !important; font-weight:800 !important; }}
.company-info p, .title p {{ color:#617168 !important; }}
.receipt-meta h2, .meta h3 {{ color:var(--v10-green) !important; }}
.receipt-meta, .meta {{ background:var(--v10-cream); border:1px solid #eadfbe; border-radius:12px; padding:12px 15px; }}
th {{ background:var(--v10-green) !important; }}
thead tr {{ box-shadow:inset 0 -2px 0 var(--v10-gold); }}
td {{ border-bottom-color:var(--v10-line) !important; }}
tr:nth-child(even) td {{ background:#fbfcfa; }}
.desccol, .task-name {{ color:var(--v10-green) !important; }}
.grand-total {{ background:linear-gradient(135deg,var(--v10-green),#064622) !important; border:1px solid rgba(214,168,79,.45); border-radius:14px !important; box-shadow:0 10px 25px rgba(7,93,44,.16); }}
.task-card {{ border-left-color:var(--v10-gold) !important; border-radius:14px !important; box-shadow:0 6px 18px rgba(7,93,44,.07); }}
.task-date {{ color:var(--v10-green) !important; background:#eef7f0 !important; }}
.save-img-btn {{ background:var(--v10-green) !important; border-radius:10px !important; border:1px solid var(--v10-gold) !important; box-shadow:0 6px 16px rgba(7,93,44,.18) !important; }}
.save-img-btn:hover {{ background:var(--v10-green-2) !important; }}
.footer {{ color:#718078 !important; }}
@media (max-width:700px) {{ body {{ padding:8px !important; }} .receipt-container, .receipt-card, #receiptContent {{ padding:18px !important; border-radius:14px !important; }} .receipt-container::before, .receipt-card::before, #receiptContent::before {{ top:15px; left:16px; width:36px; height:36px; font-size:20px; }} .company-info, .title {{ padding-left:48px; }} .company-info h1, .title h1 {{ font-size:20px !important; }} .receipt-meta, .meta {{ padding:9px 10px; }} th, td {{ padding:8px 6px !important; font-size:11px !important; }} .save-img-btn {{ width:100%; }} }}

/* ================================================================
   AILYN HOUSE RECEIPT VISUAL OVERHAUL — LOOK ONLY
   Structure, calculations, records and export logic are unchanged.
   ================================================================ */
:root {{ --ah-green:#064f2a; --ah-green-2:#0b6b38; --ah-gold:#c89b3c; --ah-gold-soft:#f5ecd8; --ah-cream:#fbfaf5; --ah-ink:#17372a; --ah-muted:#68776f; --ah-line:#d9e1da; }}
body {{ background:radial-gradient(circle at 15% 0%,#edf6ef 0,#f7faf7 35%,#eef4ef 100%) !important; color:var(--ah-ink) !important; }}
#receiptContent, .receipt-container, .receipt-card {{ background:#fff !important; border:1px solid #dfe7df !important; border-top:6px solid var(--ah-green) !important; border-radius:22px !important; box-shadow:0 24px 60px rgba(6,79,42,.13),0 4px 14px rgba(20,45,30,.06) !important; overflow:hidden !important; }}
#receiptContent {{ position:relative !important; }}
#receiptContent::after, .receipt-container::after, .receipt-card::after {{ content:""; position:absolute; top:0; right:0; width:180px; height:6px; background:var(--ah-gold); opacity:.95; }}
.company-info h1, .title h1, #receiptContent h1 {{ color:var(--ah-green) !important; font-weight:900 !important; letter-spacing:.4px !important; }}
.company-info p, .title p {{ color:var(--ah-muted) !important; }}
.receipt-meta, .meta {{ background:linear-gradient(135deg,#fffdf8,#f7f4e9) !important; border:1px solid #eadfbe !important; border-radius:14px !important; box-shadow:0 4px 12px rgba(120,92,35,.06); }}
.receipt-meta h2, .meta h3 {{ color:var(--ah-green) !important; font-weight:900 !important; }}
#receiptContent table {{ border-collapse:separate !important; border-spacing:0 !important; overflow:hidden !important; }}
#receiptContent th {{ background:linear-gradient(135deg,var(--ah-green),var(--ah-green-2)) !important; color:#fff !important; font-weight:800 !important; border:0 !important; }}
#receiptContent td {{ color:#263b31 !important; border-bottom:1px solid var(--ah-line) !important; background:#fff !important; }}
#receiptContent tr:nth-child(even) td {{ background:#f8fbf8 !important; }}
#receiptContent tr:hover td {{ background:#f5f8f5 !important; }}
.desccol {{ color:var(--ah-green) !important; font-weight:900 !important; font-size:13px !important; }}
#receiptContent td.desccol, #receiptContent td:nth-child(3) {{ color:var(--ah-green) !important; font-weight:800 !important; }}
.grand-total {{ background:linear-gradient(145deg,#063f22,#08703a) !important; border:1px solid rgba(200,155,60,.65) !important; border-radius:18px !important; box-shadow:0 16px 30px rgba(6,79,42,.18) !important; }}
.final-balance-row {{ border-top-color:rgba(255,255,255,.28) !important; }}
.save-img-btn {{ background:linear-gradient(135deg,var(--ah-green),var(--ah-green-2)) !important; border:1px solid var(--ah-gold) !important; border-radius:12px !important; padding:13px 25px !important; box-shadow:0 8px 20px rgba(6,79,42,.18) !important; }}
.save-img-btn:hover {{ transform:translateY(-1px); filter:brightness(1.05); }}
.footer {{ color:#7b8981 !important; }}
#receiptContent > table:first-of-type {{ background:linear-gradient(135deg,#fbfdfb,#fffdf7) !important; border:1px solid #e4eae5 !important; border-radius:16px !important; padding:4px !important; box-shadow:0 8px 20px rgba(6,79,42,.06); }}
#receiptContent > table:first-of-type h1 {{ font-size:28px !important; }}
#receiptContent > table:first-of-type h3 {{ color:var(--ah-green) !important; font-weight:900 !important; }}
#receiptContent table td {{ word-break:normal !important; overflow-wrap:anywhere !important; }}
#receiptContent table:nth-of-type(2) td:first-child {{ color:var(--ah-green) !important; font-weight:800 !important; }}
.task-card {{ background:linear-gradient(145deg,#fff,#f7faf7) !important; border:1px solid #dce6df !important; border-left:6px solid var(--ah-green) !important; border-radius:17px !important; box-shadow:0 10px 24px rgba(6,79,42,.08) !important; }}
.task-date {{ color:var(--ah-green) !important; background:var(--ah-gold-soft) !important; border:1px solid #e6d3a6 !important; }}
.task-name {{ color:var(--ah-green) !important; font-weight:900 !important; }}
.task-status {{ border:1px solid rgba(6,79,42,.12); }}
@media (max-width:700px) {{
  body {{ padding:7px !important; }}
  #receiptContent, .receipt-container, .receipt-card {{ border-radius:16px !important; }}
  #receiptContent > table:first-of-type h1 {{ font-size:21px !important; }}
  .company-info h1, .title h1 {{ font-size:21px !important; }}
  .desccol, #receiptContent td:nth-child(3) {{ font-size:12px !important; }}
  #receiptContent th, #receiptContent td {{ padding:7px 5px !important; }}
}}

/* ================================================================
   AILYN HOUSE — PAYROLL RECEIPT REDESIGN v2 — LOOK ONLY
   ================================================================ */
:root {{ --ahg:#075d2c; --ahg2:#0b7a3b; --ahgold:#c9a34a; --ahink:#17352a; --ahmuted:#68776f; --ahline:#dfe7df; }}
* {{ box-sizing:border-box; }}
html,body {{ width:100%; min-width:0; overflow-x:hidden !important; }}
body {{ margin:0 !important; padding:12px !important; background:#eef3ef !important; color:var(--ahink) !important; font-family:'Inter','Segoe UI',Arial,sans-serif !important; }}
#receiptContent {{ width:100% !important; max-width:980px !important; margin:0 auto !important; padding:25px 30px 20px !important; background:#fff !important; border:1px solid #d8e2da !important; border-top:7px solid var(--ahg) !important; border-radius:20px !important; box-shadow:0 12px 30px rgba(7,93,44,.10) !important; overflow:hidden !important; position:relative !important; }}
#receiptContent::before {{ content:'' !important; position:absolute !important; left:0 !important; top:0 !important; width:125px !important; height:7px !important; background:var(--ahgold) !important; }}
.save-btn-container {{ margin:0 auto 10px !important; max-width:980px !important; }}
.save-img-btn {{ background:var(--ahg) !important; border:1px solid var(--ahgold) !important; border-radius:9px !important; padding:9px 18px !important; font-size:12px !important; box-shadow:0 5px 12px rgba(7,93,44,.14) !important; }}
#receiptContent > table:first-of-type {{ width:100% !important; margin:0 0 16px !important; border-collapse:separate !important; border-spacing:0 !important; background:#f9fbf9 !important; border:1px solid #dfe8e1 !important; border-radius:14px !important; overflow:hidden !important; }}
#receiptContent > table:first-of-type td:first-child {{ position:relative !important; padding:15px 16px 15px 76px !important; }}
#receiptContent > table:first-of-type td:first-child::before {{ content:'⌂' !important; position:absolute !important; left:16px !important; top:15px !important; width:45px !important; height:45px !important; display:grid !important; place-items:center !important; border-radius:12px !important; background:var(--ahg) !important; color:#fff !important; font-size:25px !important; font-weight:800 !important; }}
#receiptContent > table:first-of-type td:last-child {{ padding:15px 16px !important; }}
#receiptContent > table:first-of-type h1 {{ margin:0 !important; color:var(--ahg) !important; font-size:29px !important; font-weight:900 !important; letter-spacing:.5px !important; }}
#receiptContent > table:first-of-type h3 {{ margin:0 !important; color:var(--ahg) !important; font-size:20px !important; font-weight:900 !important; }}
#receiptContent > table:first-of-type p {{ margin:4px 0 !important; color:#68776f !important; font-size:11px !important; }}
#receiptContent > table:nth-of-type(2) {{ width:100% !important; table-layout:fixed !important; margin:0 0 16px !important; border-collapse:separate !important; border-spacing:0 !important; }}
#receiptContent > table:nth-of-type(2) th {{ background:var(--ahg) !important; color:#fff !important; padding:10px 7px !important; font-size:10px !important; text-transform:uppercase !important; letter-spacing:.35px !important; }}
#receiptContent > table:nth-of-type(2) th:first-child {{ border-radius:10px 0 0 10px !important; }}
#receiptContent > table:nth-of-type(2) th:last-child {{ border-radius:0 10px 10px 0 !important; }}
#receiptContent > table:nth-of-type(2) td {{ padding:8px 7px !important; font-size:10.5px !important; line-height:1.25 !important; border-bottom:1px solid var(--ahline) !important; overflow-wrap:anywhere !important; }}
#receiptContent > table:nth-of-type(2) tr:nth-child(even) td {{ background:#f8fbf8 !important; }}
#receiptContent > table:nth-of-type(2) td:first-child {{ font-weight:800 !important; color:var(--ahink) !important; }}
#receiptContent > table:nth-of-type(2) th:nth-child(1), #receiptContent > table:nth-of-type(2) td:nth-child(1) {{ width:25% !important; }}
#receiptContent > table:nth-of-type(2) th:nth-child(2), #receiptContent > table:nth-of-type(2) td:nth-child(2) {{ width:15% !important; text-align:center !important; }}
#receiptContent > table:nth-of-type(2) th:nth-child(3), #receiptContent > table:nth-of-type(2) td:nth-child(3) {{ width:18% !important; text-align:center !important; }}
#receiptContent > table:nth-of-type(2) th:nth-child(4), #receiptContent > table:nth-of-type(2) td:nth-child(4) {{ width:15% !important; text-align:right !important; }}
#receiptContent > table:nth-of-type(2) th:nth-child(5), #receiptContent > table:nth-of-type(2) td:nth-child(5) {{ width:11% !important; text-align:right !important; }}
#receiptContent > table:nth-of-type(2) th:nth-child(6), #receiptContent > table:nth-of-type(2) td:nth-child(6) {{ width:16% !important; text-align:right !important; }}
#receiptContent > table:nth-of-type(2) tbody tr:last-child td {{ border-bottom:2px solid var(--ahg) !important; }}
#receiptContent > table:nth-of-type(2) tbody tr:nth-last-child(n+1) td {{ }}
#receiptContent > table:nth-of-type(2) tr:has(td[colspan]) td {{ background:#fffaf0 !important; color:var(--ahg) !important; font-weight:800 !important; }}
#receiptContent > table:nth-of-type(3) {{ width:100% !important; margin:0 0 14px !important; border-collapse:collapse !important; }}
#receiptContent > table:nth-of-type(3) td {{ padding:9px 8px !important; border-bottom:1px solid var(--ahline) !important; color:#34483e !important; font-size:11px !important; }}
#receiptContent > table:nth-of-type(4) {{ width:100% !important; margin-top:8px !important; }}
#receiptContent > table:nth-of-type(4) td:last-child {{ width:360px !important; max-width:45% !important; padding:18px 20px !important; background:linear-gradient(145deg,#064a27,#08733c) !important; border:1px solid rgba(201,163,74,.8) !important; border-radius:15px !important; color:#fff !important; text-align:right !important; }}
#receiptContent > table:nth-of-type(4) span:first-child {{ color:#dce8df !important; font-size:11px !important; letter-spacing:1.2px !important; }}
#receiptContent > table:nth-of-type(4) span:last-child {{ color:#fff !important; font-size:30px !important; font-weight:900 !important; }}
#receiptContent > div:last-child {{ margin-top:25px !important; padding-top:12px !important; border-top:1px solid var(--ahline) !important; }}
#receiptContent > div:last-child p {{ margin:0 !important; color:#819087 !important; font-size:8px !important; letter-spacing:1px !important; }}
@media (max-width:700px) {{
 body {{ padding:5px !important; }}
 #receiptContent {{ padding:14px 10px 12px !important; border-radius:14px !important; border-top-width:5px !important; }}
 #receiptContent::before {{ height:5px !important; width:70px !important; }}
 #receiptContent > table:first-of-type td:first-child {{ padding:11px 8px 11px 55px !important; }}
 #receiptContent > table:first-of-type td:first-child::before {{ left:9px !important; top:11px !important; width:34px !important; height:34px !important; border-radius:9px !important; font-size:19px !important; }}
 #receiptContent > table:first-of-type td:last-child {{ padding:11px 8px !important; }}
 #receiptContent > table:first-of-type h1 {{ font-size:20px !important; }}
 #receiptContent > table:first-of-type h3 {{ font-size:13px !important; }}
 #receiptContent > table:first-of-type p {{ font-size:8px !important; }}
 #receiptContent > table:nth-of-type(2) th {{ padding:7px 3px !important; font-size:7.5px !important; }}
 #receiptContent > table:nth-of-type(2) td {{ padding:7px 3px !important; font-size:8px !important; }}
 #receiptContent > table:nth-of-type(3) td {{ padding:7px 4px !important; font-size:8px !important; }}
 #receiptContent > table:nth-of-type(4) td:last-child {{ width:48% !important; max-width:55% !important; padding:12px !important; }}
 #receiptContent > table:nth-of-type(4) span:first-child {{ font-size:7px !important; }}
 #receiptContent > table:nth-of-type(4) span:last-child {{ font-size:20px !important; }}
}}
@media print {{ body {{ padding:0 !important; background:#fff !important; }} #receiptContent {{ max-width:none !important; box-shadow:none !important; }} }}

</style>
</head>
<body style="font-family: 'Segoe UI', sans-serif; background-color: #f4f7f6; padding: 40px;">
<div class="save-btn-container">
<button class="save-img-btn" onclick="saveAsImage()">SAVE RECEIPT IMAGE</button>
</div>
<div id="receiptContent" style="max-width: 900px; margin: auto; background: white; border-top: 10px solid #1b5e20; padding: 40px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
<table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
<tr>
<td>
<h1 style="color: #1b5e20; margin: 0; text-transform: uppercase;">AILYN HOUSE</h1>
<p style="color: #555; margin: 5px 0 0 0;">Official Payroll & Labor Receipt</p>
<p style="color: #777; font-size: 14px; margin: 0;">Management System v3.6 Enterprise</p>
</td>
<td style="text-align: right;">
<h3 style="color: #1b5e20; margin: 0;">{custom_title}</h3>
<p style="color: #555; font-size: 14px; margin: 5px 0 0 0;">Date: {date_str}</p>
<p style="color: #777; font-size: 12px; margin: 5px 0 0 0;">Account: {RECEIVER_EMAIL}</p>
</td>
</tr>
</table>
<div style="border-bottom: 2px solid #eee; margin-bottom: 30px;"></div>
<table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
<thead>
<tr style="background-color: #1b5e20; color: white; text-transform: uppercase; font-size: 14px;">
<th style="padding: 12px; text-align: left;">Worker Name</th>
<th style="padding: 12px; text-align: center;">Role</th>
<th style="padding: 12px; text-align: center;">Days / Point</th>
<th style="padding: 12px; text-align: right;">Gross Pay</th>
<th style="padding: 12px; text-align: right;">C.A.</th>
<th style="padding: 12px; text-align: right;">Net Pay</th>
</tr>
</thead>
<tbody>"""
    
    for r in labor_records:
        role_display = r.get('role', 'Labor')
        gross = r.get('gross_pay', r['days'] * r['rate'])
        html += f"""
<tr>
<td style="padding: 12px; border-bottom: 1px solid #ddd; font-weight: bold;">{r['name']}</td>
<td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: center;">{role_display}</td>
<td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: center;">{r['days']:.1f}</td>
<td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right;">{gross:,.2f}</td>
<td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right; color: #d32f2f;">({r['ca']:,.2f})</td>
<td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right; font-weight: bold; color: #1b5e20;">{r['net']:,.2f}</td>
</tr>"""
        
    if expense_records:
        html += f"""
<tr>
<td colspan="6" style="padding: 12px 0;"></td>
</tr>
<tr style="background-color: #388e3c; color: white; text-transform: uppercase; font-size: 14px;">
<th colspan="5" style="padding: 10px; text-align: left;">Expense Description</th>
<th style="padding: 10px; text-align: right;">Amount</th>
</tr>"""
        for e in expense_records:
            html += f"""
<tr>
<td colspan="5" style="padding: 10px; border-bottom: 1px solid #ddd;">{e['item']}</td>
<td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right; font-weight: bold;">{e['price']:,.2f}</td>
</tr>"""
            
    html += f"""
</tbody>
</table>
<table style="width: 100%; border-collapse: collapse; margin-top: 20px; margin-bottom: 30px;">
<tr style="border-top: 2px solid #bbb;">
<td style="padding: 12px; font-weight: bold; text-align: right; font-size: 15px;">Subtotal Expenses:</td>
<td style="padding: 12px; width: 180px; text-align: right; font-weight: bold; font-size: 15px; color: #333;">PHP {sub_total:,.2f}</td>
</tr>"""
    
    if remaining_money and remaining_money > 0:
        html += f"""
<tr style="border-bottom: 2px solid #bbb;">
<td style="padding: 12px; font-weight: bold; text-align: right; color: #d32f2f; font-size: 15px;">Remaining/Leftover Money:</td>
<td style="padding: 12px; width: 180px; text-align: right; font-weight: bold; color: #d32f2f; font-size: 15px;">-PHP {remaining_money:,.2f}</td>
</tr>"""
        
    html += f"""
</table>
<table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
<tr>
<td></td>
<td style="width: 350px; background: #1b5e20; color: white; padding: 20px; border-radius: 8px; text-align: right;">
<span style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Final Output Amount</span><br>
<span style="font-size: 32px; font-weight: bold; margin-top: 5px; display: inline-block;">PHP {grand_total:,.2f}</span>
</td>
</tr>
</table>
<div style="text-align: center; margin-top: 60px; border-top: 1px solid #eee; padding-top: 20px;">
<p style="color: #999; font-size: 11px; letter-spacing: 1px; text-transform: uppercase;">
THIS DOCUMENT WAS ELECTRONICALLY GENERATED AND IS VALID WITHOUT SIGNATURE.
</p>
</div>
</div>
<script>
function saveAsImage() {{
    const element = document.getElementById('receiptContent');
    html2canvas(element, {{ scale: 2, useCORS: true }}).then(canvas => {{
        const link = document.createElement('a');
        link.download = '{custom_title.replace(" ", "_")}_Receipt.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
    }});
}}
</script>
</body>
</html>"""
    return html, grand_total

# ================================================================
# EDIT HERE #2 — UNIVERSAL RECEIPT DESIGN: SCHEDULE / PLANNER
# Same V10 header, table, summary, green/gold system, and phone behavior.
# ================================================================
# ================================================================
# V10 RECEIPT REPLACEMENT — GENERATE_PLANNER_HTML
# EDIT HERE: This receipt design was replaced with the MAIN receipt layout
# and restyled to match the V10 UI/logo system.
# Phone/tablet/desktop use the same responsive receipt.
# ================================================================
def generate_planner_html(planner_tasks, custom_title="WORK SCHEDULE & CALENDAR RECEIPT"):
    # ================================================================
    # EDIT HERE - MAIN SCHEDULE RECEIPT (FULL MAIN DESIGN)
    # This function is copied from the MAIN receipt and applied fully to V10.
    # ================================================================
    date_now = datetime.now().strftime("%B %d, %Y")
    sorted_tasks = sorted(planner_tasks, key=lambda x: x.get('date_obj', ''))
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&display=swap');
body {{ font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f0f4f0; margin: 0; padding: 30px; color: #1e293b; }}
.receipt-card {{ max-width: 900px; margin: auto; background: #ffffff; border-radius: 12px; padding: 35px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); border-top: 10px solid #1b5e20; }}
.header {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: flex-start; }}
.title h1 {{ color: #1b5e20; margin: 0; font-size: 24px; font-weight: 800; text-transform: uppercase; }}
.title p {{ color: #64748b; margin: 4px 0 0 0; font-size: 13px; font-weight: 600; }}
.meta {{ text-align: right; font-size: 12px; color: #475569; }}
.meta h3 {{ margin: 0; color: #1b5e20; font-size: 16px; text-transform: uppercase; }}
.task-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-top: 20px; }}
.task-card {{ background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 8px; border-left: 5px solid #22c55e; }}
.task-date {{ font-size: 12px; font-weight: 800; color: #1b5e20; text-transform: uppercase; letter-spacing: 0.5px; background: #dcfce7; padding: 4px 8px; border-radius: 6px; width: fit-content; }}
.task-name {{ font-size: 15px; font-weight: 700; color: #0f172a; margin: 4px 0; }}
.task-phase {{ font-size: 12px; color: #64748b; font-weight: 600; }}
.task-status {{ font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 20px; width: fit-content; text-transform: uppercase; letter-spacing: 0.5px; margin-top: auto; }}
.status-completed {{ background: #dcfce7; color: #15803d; }}
.status-inprogress {{ background: #fef3c7; color: #b45309; }}
.status-notstarted {{ background: #f1f5f9; color: #475569; }}
.photo-gallery {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; border-top: 1px dashed #e2e8f0; padding-top: 10px; }}
.photo-img {{ width: 80px; height: 80px; object-fit: cover; border-radius: 6px; border: 1px solid #cbd5e1; }}
.footer {{ margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 15px; text-align: center; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }}
.save-btn-container {{ text-align: center; margin-bottom: 25px; }}
.save-img-btn {{ background-color: #1b5e20; color: white; border: none; padding: 12px 24px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }}
.save-img-btn:hover {{ background-color: #2e7d32; }}
@media print {{ .save-btn-container {{ display: none; }} }}
/* V10 RECEIPT VISUAL REDESIGN — LOOK ONLY */
:root {{ --v10-green:#075d2c; --v10-green-2:#0b7a3b; --v10-gold:#d6a84f; --v10-cream:#f7f5ee; --v10-ink:#17352a; --v10-line:#dfe7df; }}
body {{ background:linear-gradient(180deg,#eef5ef 0%,#f8faf7 100%) !important; color:var(--v10-ink) !important; }}
.receipt-container, .receipt-card, #receiptContent {{ border-top-color:var(--v10-green) !important; border-radius:18px !important; box-shadow:0 16px 45px rgba(7,93,44,.12),0 2px 8px rgba(0,0,0,.05) !important; position:relative; overflow:hidden; }}
.receipt-container::before, .receipt-card::before, #receiptContent::before {{ content:"⌂"; position:absolute; top:22px; left:28px; width:44px; height:44px; border-radius:12px; background:var(--v10-green); color:#fff; display:grid; place-items:center; font-size:25px; font-weight:800; box-shadow:0 5px 14px rgba(7,93,44,.22); }}
.company-info, .title {{ padding-left:62px; }}
.company-info h1, .title h1 {{ color:var(--v10-green) !important; letter-spacing:-.5px !important; font-weight:800 !important; }}
.company-info p, .title p {{ color:#617168 !important; }}
.receipt-meta h2, .meta h3 {{ color:var(--v10-green) !important; }}
.receipt-meta, .meta {{ background:var(--v10-cream); border:1px solid #eadfbe; border-radius:12px; padding:12px 15px; }}
th {{ background:var(--v10-green) !important; }}
thead tr {{ box-shadow:inset 0 -2px 0 var(--v10-gold); }}
td {{ border-bottom-color:var(--v10-line) !important; }}
tr:nth-child(even) td {{ background:#fbfcfa; }}
.desccol, .task-name {{ color:var(--v10-green) !important; }}
.grand-total {{ background:linear-gradient(135deg,var(--v10-green),#064622) !important; border:1px solid rgba(214,168,79,.45); border-radius:14px !important; box-shadow:0 10px 25px rgba(7,93,44,.16); }}
.task-card {{ border-left-color:var(--v10-gold) !important; border-radius:14px !important; box-shadow:0 6px 18px rgba(7,93,44,.07); }}
.task-date {{ color:var(--v10-green) !important; background:#eef7f0 !important; }}
.save-img-btn {{ background:var(--v10-green) !important; border-radius:10px !important; border:1px solid var(--v10-gold) !important; box-shadow:0 6px 16px rgba(7,93,44,.18) !important; }}
.save-img-btn:hover {{ background:var(--v10-green-2) !important; }}
.footer {{ color:#718078 !important; }}
@media (max-width:700px) {{ body {{ padding:8px !important; }} .receipt-container, .receipt-card, #receiptContent {{ padding:18px !important; border-radius:14px !important; }} .receipt-container::before, .receipt-card::before, #receiptContent::before {{ top:15px; left:16px; width:36px; height:36px; font-size:20px; }} .company-info, .title {{ padding-left:48px; }} .company-info h1, .title h1 {{ font-size:20px !important; }} .receipt-meta, .meta {{ padding:9px 10px; }} th, td {{ padding:8px 6px !important; font-size:11px !important; }} .save-img-btn {{ width:100%; }} }}

/* ================================================================
   AILYN HOUSE RECEIPT VISUAL OVERHAUL — LOOK ONLY
   Structure, calculations, records and export logic are unchanged.
   ================================================================ */
:root {{ --ah-green:#064f2a; --ah-green-2:#0b6b38; --ah-gold:#c89b3c; --ah-gold-soft:#f5ecd8; --ah-cream:#fbfaf5; --ah-ink:#17372a; --ah-muted:#68776f; --ah-line:#d9e1da; }}
body {{ background:radial-gradient(circle at 15% 0%,#edf6ef 0,#f7faf7 35%,#eef4ef 100%) !important; color:var(--ah-ink) !important; }}
#receiptContent, .receipt-container, .receipt-card {{ background:#fff !important; border:1px solid #dfe7df !important; border-top:6px solid var(--ah-green) !important; border-radius:22px !important; box-shadow:0 24px 60px rgba(6,79,42,.13),0 4px 14px rgba(20,45,30,.06) !important; overflow:hidden !important; }}
#receiptContent {{ position:relative !important; }}
#receiptContent::after, .receipt-container::after, .receipt-card::after {{ content:""; position:absolute; top:0; right:0; width:180px; height:6px; background:var(--ah-gold); opacity:.95; }}
.company-info h1, .title h1, #receiptContent h1 {{ color:var(--ah-green) !important; font-weight:900 !important; letter-spacing:.4px !important; }}
.company-info p, .title p {{ color:var(--ah-muted) !important; }}
.receipt-meta, .meta {{ background:linear-gradient(135deg,#fffdf8,#f7f4e9) !important; border:1px solid #eadfbe !important; border-radius:14px !important; box-shadow:0 4px 12px rgba(120,92,35,.06); }}
.receipt-meta h2, .meta h3 {{ color:var(--ah-green) !important; font-weight:900 !important; }}
#receiptContent table {{ border-collapse:separate !important; border-spacing:0 !important; overflow:hidden !important; }}
#receiptContent th {{ background:linear-gradient(135deg,var(--ah-green),var(--ah-green-2)) !important; color:#fff !important; font-weight:800 !important; border:0 !important; }}
#receiptContent td {{ color:#263b31 !important; border-bottom:1px solid var(--ah-line) !important; background:#fff !important; }}
#receiptContent tr:nth-child(even) td {{ background:#f8fbf8 !important; }}
#receiptContent tr:hover td {{ background:#f5f8f5 !important; }}
.desccol {{ color:var(--ah-green) !important; font-weight:900 !important; font-size:13px !important; }}
#receiptContent td.desccol, #receiptContent td:nth-child(3) {{ color:var(--ah-green) !important; font-weight:800 !important; }}
.grand-total {{ background:linear-gradient(145deg,#063f22,#08703a) !important; border:1px solid rgba(200,155,60,.65) !important; border-radius:18px !important; box-shadow:0 16px 30px rgba(6,79,42,.18) !important; }}
.final-balance-row {{ border-top-color:rgba(255,255,255,.28) !important; }}
.save-img-btn {{ background:linear-gradient(135deg,var(--ah-green),var(--ah-green-2)) !important; border:1px solid var(--ah-gold) !important; border-radius:12px !important; padding:13px 25px !important; box-shadow:0 8px 20px rgba(6,79,42,.18) !important; }}
.save-img-btn:hover {{ transform:translateY(-1px); filter:brightness(1.05); }}
.footer {{ color:#7b8981 !important; }}
#receiptContent > table:first-of-type {{ background:linear-gradient(135deg,#fbfdfb,#fffdf7) !important; border:1px solid #e4eae5 !important; border-radius:16px !important; padding:4px !important; box-shadow:0 8px 20px rgba(6,79,42,.06); }}
#receiptContent > table:first-of-type h1 {{ font-size:28px !important; }}
#receiptContent > table:first-of-type h3 {{ color:var(--ah-green) !important; font-weight:900 !important; }}
#receiptContent table td {{ word-break:normal !important; overflow-wrap:anywhere !important; }}
#receiptContent table:nth-of-type(2) td:first-child {{ color:var(--ah-green) !important; font-weight:800 !important; }}
.task-card {{ background:linear-gradient(145deg,#fff,#f7faf7) !important; border:1px solid #dce6df !important; border-left:6px solid var(--ah-green) !important; border-radius:17px !important; box-shadow:0 10px 24px rgba(6,79,42,.08) !important; }}
.task-date {{ color:var(--ah-green) !important; background:var(--ah-gold-soft) !important; border:1px solid #e6d3a6 !important; }}
.task-name {{ color:var(--ah-green) !important; font-weight:900 !important; }}
.task-status {{ border:1px solid rgba(6,79,42,.12); }}
@media (max-width:700px) {{
  body {{ padding:7px !important; }}
  #receiptContent, .receipt-container, .receipt-card {{ border-radius:16px !important; }}
  #receiptContent > table:first-of-type h1 {{ font-size:21px !important; }}
  .company-info h1, .title h1 {{ font-size:21px !important; }}
  .desccol, #receiptContent td:nth-child(3) {{ font-size:12px !important; }}
  #receiptContent th, #receiptContent td {{ padding:7px 5px !important; }}
}}

/* ================================================================
   AILYN HOUSE — SCHEDULE RECEIPT REDESIGN v2 — LOOK ONLY
   ================================================================ */
:root {{ --ahg:#075d2c; --ahg2:#0b7a3b; --ahgold:#c9a34a; --ahink:#17352a; --ahmuted:#68776f; --ahline:#dfe7df; }}
* {{ box-sizing:border-box; }}
html,body {{ width:100%; min-width:0; overflow-x:hidden !important; }}
body {{ margin:0 !important; padding:12px !important; background:#eef3ef !important; color:var(--ahink) !important; font-family:'Plus Jakarta Sans','Segoe UI',Arial,sans-serif !important; }}
.receipt-card {{ width:100% !important; max-width:980px !important; margin:0 auto !important; padding:24px 28px 20px !important; background:#fff !important; border:1px solid #d8e2da !important; border-top:7px solid var(--ahg) !important; border-radius:20px !important; box-shadow:0 12px 30px rgba(7,93,44,.10) !important; position:relative !important; overflow:hidden !important; }}
.receipt-card::before {{ content:'' !important; position:absolute !important; left:0 !important; top:0 !important; width:125px !important; height:7px !important; background:var(--ahgold) !important; }}
.header {{ display:flex !important; gap:20px !important; justify-content:space-between !important; align-items:center !important; padding:4px 0 17px !important; margin-bottom:17px !important; border-bottom:1px solid var(--ahline) !important; }}
.title {{ position:relative !important; padding-left:64px !important; }}
.title::before {{ content:'⌂' !important; position:absolute !important; left:0 !important; top:0 !important; width:48px !important; height:48px !important; display:grid !important; place-items:center !important; border-radius:13px !important; background:var(--ahg) !important; color:#fff !important; font-size:27px !important; font-weight:800 !important; }}
.title h1 {{ margin:0 !important; color:var(--ahg) !important; font-size:27px !important; font-weight:900 !important; letter-spacing:.4px !important; }}
.title p {{ margin:5px 0 0 !important; color:var(--ahmuted) !important; font-size:10px !important; }}
.meta {{ min-width:180px !important; padding:12px 14px !important; background:#fffaf0 !important; border:1px solid #e8d9b4 !important; border-radius:13px !important; }}
.meta h3 {{ margin:0 !important; color:var(--ahg) !important; font-size:16px !important; font-weight:900 !important; }}
.meta p {{ margin:4px 0 0 !important; color:#4d5e55 !important; font-size:10px !important; }}
.task-grid {{ grid-template-columns:repeat(auto-fit,minmax(240px,1fr)) !important; gap:12px !important; margin-top:0 !important; }}
.task-card {{ background:#fff !important; border:1px solid var(--ahline) !important; border-left:5px solid var(--ahg) !important; border-radius:13px !important; padding:14px !important; box-shadow:0 7px 16px rgba(7,93,44,.07) !important; }}
.task-date {{ color:var(--ahg) !important; background:#fff8e9 !important; border:1px solid #ead9ad !important; padding:5px 8px !important; border-radius:7px !important; font-size:9px !important; }}
.task-name {{ color:var(--ahink) !important; font-size:14px !important; font-weight:900 !important; line-height:1.3 !important; }}
.task-phase {{ color:var(--ahmuted) !important; font-size:10px !important; }}
.task-status {{ font-size:9px !important; }}
.photo-gallery {{ border-top:1px dashed #dbe4dd !important; }}
.photo-img {{ width:72px !important; height:72px !important; border-radius:8px !important; }}
.footer {{ margin-top:20px !important; padding-top:12px !important; border-top:1px solid var(--ahline) !important; color:#819087 !important; font-size:8px !important; }}
.save-btn-container {{ margin:0 auto 10px !important; max-width:980px !important; }}
.save-img-btn {{ background:var(--ahg) !important; border:1px solid var(--ahgold) !important; border-radius:9px !important; padding:9px 18px !important; font-size:12px !important; }}
@media (max-width:700px) {{
 body {{ padding:5px !important; }}
 .receipt-card {{ padding:15px 10px 12px !important; border-radius:14px !important; border-top-width:5px !important; }}
 .receipt-card::before {{ height:5px !important; width:70px !important; }}
 .header {{ gap:9px !important; align-items:flex-start !important; padding-bottom:12px !important; margin-bottom:12px !important; }}
 .title {{ padding-left:43px !important; }}
 .title::before {{ width:33px !important; height:33px !important; border-radius:8px !important; font-size:18px !important; }}
 .title h1 {{ font-size:19px !important; }}
 .title p {{ font-size:8px !important; }}
 .meta {{ min-width:120px !important; padding:7px 8px !important; }}
 .meta h3 {{ font-size:11px !important; }}
 .meta p {{ font-size:7px !important; }}
 .task-grid {{ grid-template-columns:1fr !important; gap:9px !important; }}
 .task-card {{ padding:11px !important; }}
 .task-name {{ font-size:12px !important; }}
 .task-phase {{ font-size:9px !important; }}
 .photo-img {{ width:58px !important; height:58px !important; }}
 .save-img-btn {{ width:100% !important; }}
}}
@media print {{ body {{ padding:0 !important; background:#fff !important; }} .receipt-card {{ max-width:none !important; box-shadow:none !important; }} }}

</style>
</head>
<body>
<div class="save-btn-container">
<button class="save-img-btn" onclick="saveAsImage()">SAVE RECEIPT IMAGE</button>
</div>
<div class="receipt-card" id="receiptContent">
<div class="header">
<div class="title">
<h1>{custom_title}</h1>
<p>AILYN HOUSE PROJECT MANAGEMENT SYSTEM</p>
</div>
<div class="meta">
<h3>OFFICIAL SCHEDULE</h3>
<p><b>Generated:</b> {date_now}</p>
</div>
</div>
<div class="task-grid">"""
    
    for t in sorted_tasks:
        st_class = "status-completed" if t['status'] == "Completed" else "status-inprogress" if t['status'] == "In Progress" else "status-notstarted"
        photos_html = ""
        if t.get("photos"):
            photos_html = '<div class="photo-gallery">'
            for p in t["photos"]:
                photos_html += f'<img src="{p}" class="photo-img" />'
            photos_html += '</div>'
        html += f"""
<div class="task-card">
<div class="task-date">{t.get('month', '')} {t.get('day', '')}, {t.get('year', '')}</div>
<div class="task-name">{t['name']}</div>
<div class="task-phase">Phase: {t['phase']}</div>
<div class="task-status {st_class}">{t['status']}</div>
{photos_html}
</div>"""
        
    html += f"""
</div>
<div class="footer">
Official Construction Task Schedule Document Electronically Generated
</div>
</div>
<script>
function saveAsImage() {{
    const element = document.getElementById('receiptContent');
    html2canvas(element, {{ scale: 2, useCORS: true }}).then(canvas => {{
        const link = document.createElement('a');
        link.download = 'Schedule_Receipt.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
    }});
}}
</script>
</body>
</html>"""
    return html

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Outfit:wght@500;600;700;800;900&display=swap');
:root{
  --mint:#72f7b0; --mint2:#c8ffe0; --deep:#06170f;
  --panel:rgba(6,27,18,.68); --panel2:rgba(10,42,26,.76);
  --edge:rgba(191,255,216,.20); --white:#f5fff8; --muted:#a9c9b5;
  --green:#0b6b2d; --glass:rgba(6,27,18,.58);
}
*{box-sizing:border-box}
html,body,[class*="css"]{font-family:'Manrope',sans-serif}
.stApp{
  background:url("https://images.unsplash.com/photo-1600585154340-be6161a56a0c") no-repeat center center fixed;
  background-size:cover;background-position:center;
}
.stApp:before{
  content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
  background:
    radial-gradient(circle at 12% 10%,rgba(74,222,128,.10),transparent 30%),
    radial-gradient(circle at 88% 78%,rgba(20,184,166,.10),transparent 32%),
    linear-gradient(115deg,rgba(1,8,5,.38),rgba(3,25,15,.58));
}
.stApp:after{
  content:"";position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.055;
  background-image:linear-gradient(rgba(255,255,255,.4) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.4) 1px,transparent 1px);
  background-size:46px 46px;mask-image:linear-gradient(to bottom,black,transparent 82%);
}
.block-container{
  position:relative;z-index:1;max-width:1500px!important;
  padding:28px 34px 42px!important;margin:18px auto 28px!important;
  background:rgba(3,18,11,.58)!important;
  border:1px solid rgba(210,255,225,.13);border-radius:34px;
  backdrop-filter:blur(30px) saturate(145%);-webkit-backdrop-filter:blur(30px) saturate(145%);
  box-shadow:0 35px 90px rgba(0,0,0,.48),inset 0 1px 0 rgba(255,255,255,.10);
}
/* premium glass header */
.headbar-container{display:flex;justify-content:center;margin:0 auto 28px}
.headbar-card{
  width:100%;position:relative;overflow:hidden;padding:20px 24px 18px;
  display:flex;align-items:center;justify-content:space-between;gap:20px;
  border-radius:26px;background:linear-gradient(105deg,rgba(10,55,32,.90),rgba(4,25,16,.78));
  border:1px solid rgba(166,255,197,.25);
  box-shadow:0 18px 42px rgba(0,0,0,.38),inset 0 1px 0 rgba(255,255,255,.15);
  backdrop-filter:blur(18px) saturate(135%);-webkit-backdrop-filter:blur(18px) saturate(135%);
}
.headbar-card:before{content:"";position:absolute;inset:0;background:linear-gradient(110deg,transparent 0%,rgba(255,255,255,.08) 42%,transparent 54%);transform:translateX(-120%);animation:scan 8s linear infinite}
.headbar-card:after{content:"";position:absolute;right:-90px;top:-100px;width:260px;height:260px;border-radius:50%;background:radial-gradient(circle,rgba(114,247,176,.13),transparent 68%);pointer-events:none}
.headbar-title{position:relative;z-index:1;display:flex;align-items:center;gap:16px;color:#fff!important;font-family:'Outfit';font-size:28px!important;font-weight:900;letter-spacing:.055em;line-height:1}
.headbar-title img{width:76px;height:76px;object-fit:contain;filter:drop-shadow(0 8px 16px rgba(0,0,0,.28));transition:transform .25s ease,filter .25s ease}
.headbar-title:hover img{transform:translateY(-3px) scale(1.04);filter:drop-shadow(0 12px 20px rgba(114,247,176,.28))}
.headbar-subtitle{position:relative;z-index:1;color:#aeeec3;font-size:10px;letter-spacing:.16em;text-transform:uppercase;font-weight:800;margin-left:92px;margin-top:4px}
.headbar-time{position:relative;z-index:1;color:#c8ffe0!important;font-size:11px!important;font-weight:800!important;background:rgba(255,255,255,.06);border:1px solid rgba(173,255,201,.15);padding:10px 13px;border-radius:13px;box-shadow:inset 0 1px 0 rgba(255,255,255,.08)}
/* glass sidebar */
section[data-testid="stSidebar"]{background:linear-gradient(180deg,rgba(1,13,8,.92),rgba(3,24,14,.88))!important;border-right:1px solid rgba(114,247,176,.12)!important;box-shadow:18px 0 70px rgba(0,0,0,.52)!important;backdrop-filter:blur(22px) saturate(140%)!important;-webkit-backdrop-filter:blur(22px) saturate(140%)!important}
section[data-testid="stSidebar"]>div{padding:22px 14px 30px!important} section[data-testid="stSidebar"] *{color:#edfff3!important}
.sidebar-brand{position:relative;overflow:hidden;padding:18px 16px;border-radius:26px;margin-bottom:12px;background:linear-gradient(145deg,rgba(12,65,39,.54),rgba(2,23,14,.38));border:1px solid rgba(114,247,176,.20);box-shadow:0 20px 44px rgba(0,0,0,.38),inset 0 1px 0 rgba(255,255,255,.12),0 0 32px rgba(52,211,125,.06);backdrop-filter:blur(22px) saturate(145%);-webkit-backdrop-filter:blur(22px) saturate(145%);transition:.25s cubic-bezier(.2,.8,.2,1)} .sidebar-brand:hover{transform:translateY(-3px);border-color:rgba(114,247,176,.40);box-shadow:0 26px 52px rgba(0,0,0,.44),0 0 34px rgba(114,247,176,.12),inset 0 1px 0 rgba(255,255,255,.16)}
.sidebar-brand:after{content:"";position:absolute;inset:-80% 35%;background:rgba(255,255,255,.09);transform:rotate(25deg);animation:scan 7s linear infinite}
.brand-row{position:relative;z-index:1;display:flex;align-items:center;gap:14px}.brand-logo{width:62px;height:62px;object-fit:contain;filter:drop-shadow(0 8px 16px rgba(0,0,0,.32));transition:.25s ease}.sidebar-brand:hover .brand-logo{transform:translateY(-4px) scale(1.06);filter:drop-shadow(0 14px 26px rgba(114,247,176,.30))}.brand-copy{min-width:0}.brand-title{font-family:'Outfit';font-size:17px;font-weight:900;letter-spacing:.06em;line-height:1.02;color:#fff!important}.brand-title span{display:block}.brand-sub{font-size:9px;color:#8ff1b4!important;letter-spacing:.16em;text-transform:uppercase;margin-top:7px;font-weight:800}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3{font-family:'Outfit';font-size:10px!important;letter-spacing:.18em;text-transform:uppercase;color:#72f7b0!important;margin:20px 5px 9px!important;display:flex;align-items:center;gap:9px} section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3:before{content:'•';font-size:20px;line-height:0;color:#45f39a;text-shadow:0 0 12px rgba(69,243,154,.8)} section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3:after{content:'';height:1px;flex:1;background:linear-gradient(90deg,rgba(114,247,176,.35),transparent)}section[data-testid="stSidebar"] hr{border-color:rgba(170,255,198,.10)!important;margin:10px 4px!important}.sidebar-gap{height:8px}.sidebar-live{font-size:9px;letter-spacing:.14em;color:#7feeb0!important;font-weight:800;text-align:center;margin:-4px 0 10px;text-shadow:0 0 12px rgba(114,247,176,.18)}
section[data-testid="stSidebar"] button{min-height:52px!important;margin:7px 0!important;padding:0 16px!important;border-radius:18px!important;text-align:left!important;background:linear-gradient(145deg,rgba(18,82,48,.48),rgba(2,31,18,.42))!important;border:1px solid rgba(114,247,176,.15)!important;box-shadow:0 7px 0 rgba(1,12,7,.55),0 14px 28px rgba(0,0,0,.24),inset 0 1px 0 rgba(255,255,255,.10)!important;transition:transform .18s cubic-bezier(.2,.8,.2,1),box-shadow .18s,border-color .18s,background .18s!important;backdrop-filter:blur(14px) saturate(135%)!important;-webkit-backdrop-filter:blur(14px) saturate(135%)!important}
section[data-testid="stSidebar"] button:hover{transform:translate3d(5px,-3px,0)!important;background:linear-gradient(145deg,rgba(28,116,67,.72),rgba(5,47,27,.56))!important;border-color:rgba(114,247,176,.58)!important;box-shadow:0 10px 0 rgba(1,12,7,.70),0 20px 36px rgba(0,0,0,.34),0 0 28px rgba(70,230,132,.16),inset 0 1px 0 rgba(255,255,255,.18)!important}
section[data-testid="stSidebar"] button:active{transform:translate3d(2px,4px,0)!important;box-shadow:0 2px 0 rgba(1,12,7,.9),0 6px 12px rgba(0,0,0,.3)!important}
section[data-testid="stSidebar"] button p{font-family:'Manrope'!important;font-weight:800!important;font-size:12px!important;letter-spacing:.01em}
/* glass controls */
button,.stDownloadButton>button,.stFormSubmitButton>button{position:relative!important;overflow:hidden!important;min-height:46px!important;border-radius:16px!important;color:#f5fff8!important;font-weight:800!important;background:linear-gradient(145deg,rgba(25,92,54,.88),rgba(5,33,19,.94))!important;border:1px solid rgba(173,255,201,.22)!important;box-shadow:0 6px 0 rgba(2,17,10,.78),0 13px 27px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.13)!important;transition:all .17s ease!important}
button:hover,.stDownloadButton>button:hover,.stFormSubmitButton>button:hover{transform:translateY(-3px)!important;border-color:rgba(114,247,176,.58)!important;box-shadow:0 9px 0 rgba(2,17,10,.78),0 20px 34px rgba(0,0,0,.35),0 0 25px rgba(114,247,176,.13),inset 0 1px 0 rgba(255,255,255,.2)!important}
button:active,.stDownloadButton>button:active,.stFormSubmitButton>button:active{transform:translateY(3px)!important;box-shadow:0 2px 0 rgba(2,17,10,.8),0 5px 10px rgba(0,0,0,.28)!important}
/* glass input fields */
div[data-baseweb="input"],div[data-baseweb="base-input"],textarea,div[data-baseweb="select"]>div{background:rgba(3,25,15,.78)!important;border:1px solid rgba(163,255,194,.18)!important;border-radius:15px!important;color:#fff!important;min-height:48px!important;box-shadow:inset 0 4px 15px rgba(0,0,0,.23),0 4px 12px rgba(0,0,0,.12)!important}
input,textarea{color:#fff!important;-webkit-text-fill-color:#fff!important}input:focus,textarea:focus,div[data-baseweb="input"]:focus-within,div[data-baseweb="select"]>div:focus-within{border-color:#72f7b0!important;box-shadow:0 0 0 3px rgba(114,247,176,.08),0 0 24px rgba(114,247,176,.14),inset 0 4px 15px rgba(0,0,0,.2)!important}label{font-weight:700!important;color:#c8e8d2!important}
/* executive glass metrics */
[data-testid="stMetric"]{position:relative;overflow:hidden;min-height:118px;padding:20px!important;background:linear-gradient(145deg,rgba(17,76,44,.78),rgba(4,28,17,.82))!important;border:1px solid rgba(173,255,201,.20);border-radius:24px;box-shadow:0 16px 34px rgba(0,0,0,.30),inset 0 1px 0 rgba(255,255,255,.13);transition:.2s ease;backdrop-filter:blur(14px)}
[data-testid="stMetric"]:before,.dash-section:before,.dash-hero:before{content:"";position:absolute;inset:0;background:linear-gradient(110deg,transparent 0%,rgba(255,255,255,.06) 42%,transparent 54%);transform:translateX(-130%);animation:scan 9s linear infinite;pointer-events:none}
[data-testid="stMetric"]:hover{transform:translateY(-5px) scale(1.01);box-shadow:0 23px 44px rgba(0,0,0,.38),0 0 28px rgba(114,247,176,.11)}
[data-testid="stMetric"] label{font-size:10px!important;letter-spacing:.14em;text-transform:uppercase;color:#91d9ab!important}[data-testid="stMetricValue"]{font-family:'Outfit';font-size:30px!important;font-weight:900!important;color:#fff!important}
/* dashboard hero */
.dash-hero{position:relative;overflow:hidden;background:linear-gradient(145deg,rgba(16,69,40,.80),rgba(4,27,16,.72));border:1px solid rgba(165,255,195,.18);border-radius:28px;padding:25px 28px;margin-bottom:18px;box-shadow:0 18px 42px rgba(0,0,0,.32),inset 0 1px 0 rgba(255,255,255,.10);backdrop-filter:blur(18px) saturate(135%);-webkit-backdrop-filter:blur(18px) saturate(135%)}
.dash-hero:after{content:"";position:absolute;right:-70px;top:-100px;width:280px;height:280px;border-radius:50%;background:radial-gradient(circle,rgba(114,247,176,.12),transparent 68%);pointer-events:none}.hero-row{position:relative;z-index:1;display:flex;align-items:center;gap:20px}.hero-logo{width:82px;height:82px;object-fit:contain;filter:drop-shadow(0 9px 17px rgba(0,0,0,.28));transition:.25s ease}.dash-hero:hover .hero-logo{transform:translateY(-3px) scale(1.04);filter:drop-shadow(0 13px 23px rgba(114,247,176,.24))}.hero-title{font-family:'Outfit';font-size:42px;line-height:.95;font-weight:900;color:#fff;letter-spacing:.015em}.hero-sub{font-size:11px;letter-spacing:.24em;color:#aeeec3;text-transform:uppercase;margin-top:9px;font-weight:800}.hero-rule{height:1px;background:rgba(191,255,216,.18);margin:18px 0}.welcome{font-size:14px;color:#c8e8d2}.welcome b{color:#72f7b0}
/* glass content cards */
.dash-section{position:relative;overflow:hidden;background:linear-gradient(145deg,rgba(10,42,26,.76),rgba(4,25,16,.68));border:1px solid rgba(165,255,195,.18);border-radius:24px;padding:20px 22px;box-shadow:0 16px 34px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.08);height:100%;backdrop-filter:blur(18px) saturate(130%);-webkit-backdrop-filter:blur(18px) saturate(130%);transition:.22s ease}.dash-section:hover{transform:translateY(-4px);border-color:rgba(114,247,176,.38);box-shadow:0 24px 46px rgba(0,0,0,.38),0 0 26px rgba(114,247,176,.08),inset 0 1px 0 rgba(255,255,255,.12)}
.section-title{font-family:'Outfit';font-size:17px;font-weight:900;color:#fff;letter-spacing:.02em;margin-bottom:16px}.section-head{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(191,255,216,.14);padding-bottom:12px;margin-bottom:12px}.section-head span{color:#91d9ab!important}
.tx-row{display:flex;align-items:center;justify-content:space-between;padding:13px 0;border-bottom:1px solid rgba(191,255,216,.10);transition:.18s ease}.tx-row:hover{padding-left:7px;background:linear-gradient(90deg,rgba(114,247,176,.05),transparent);border-radius:10px}.tx-left{display:flex;gap:12px;align-items:center}.tx-icon{width:38px;height:38px;border-radius:50%;display:grid;place-items:center;background:rgba(114,247,176,.10);border:1px solid rgba(114,247,176,.20);color:#72f7b0;font-weight:900;box-shadow:inset 0 1px 0 rgba(255,255,255,.12)}.tx-name{font-weight:800;font-size:13px;color:#f5fff8}.tx-type{font-size:10px;color:#91b8a0;margin-top:3px}.tx-right{text-align:right;font-weight:900;color:#f5fff8}.tx-date{font-size:10px;color:#91b8a0;font-weight:500;margin-top:3px}
.donut-wrap{display:flex;align-items:center;gap:25px}.donut{width:190px;height:190px;border-radius:50%;background:conic-gradient(#72f7b0 0deg var(--p1),#55b978 var(--p1) var(--p2),#d8b64c var(--p2) var(--p3),#e46f5c var(--p3) 360deg);position:relative;flex:0 0 190px;box-shadow:0 14px 32px rgba(0,0,0,.28),inset 0 2px 4px rgba(255,255,255,.15)}.donut:before{content:"";position:absolute;inset:0;border-radius:50%;box-shadow:inset 0 0 0 8px rgba(255,255,255,.035),inset 0 -8px 18px rgba(0,0,0,.20)}.donut:after{content:"";position:absolute;inset:47px;background:rgba(4,27,16,.92);border:1px solid rgba(191,255,216,.14);border-radius:50%;box-shadow:inset 0 4px 15px rgba(0,0,0,.28),0 2px 10px rgba(0,0,0,.20)}.donut-center{position:absolute;z-index:2;inset:0;display:grid;place-content:center;text-align:center;font-family:'Outfit';font-weight:900;color:#fff}.donut-center small{font:500 11px Manrope;color:#91b8a0}.legend{flex:1}.legend-row{display:flex;justify-content:space-between;gap:12px;padding:8px 0;font-size:12px;color:#d7eee0}.legend-row b{color:#fff}.dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:8px;box-shadow:0 0 9px rgba(114,247,176,.25)}
.schedule{display:flex;align-items:center;gap:20px}.schedule-icon{width:64px;height:64px;border-radius:18px;background:rgba(114,247,176,.10);border:1px solid rgba(114,247,176,.22);display:grid;place-items:center;color:#72f7b0;font-size:28px;box-shadow:inset 0 1px 0 rgba(255,255,255,.10),0 9px 20px rgba(0,0,0,.20)}.schedule-title{font-family:'Outfit';font-size:17px;color:#fff;font-weight:900}.schedule-muted{font-size:12px;color:#91b8a0;margin-top:4px}.open-planner{margin-left:auto;background:linear-gradient(145deg,rgba(25,92,54,.88),rgba(5,33,19,.94));color:#fff;padding:12px 20px;border-radius:14px;font-weight:800;border:1px solid rgba(173,255,201,.22);box-shadow:0 6px 0 rgba(2,17,10,.65),0 12px 24px rgba(0,0,0,.25);transition:.18s ease}.open-planner:hover{transform:translateY(-3px);box-shadow:0 9px 0 rgba(2,17,10,.65),0 18px 30px rgba(0,0,0,.34);border-color:rgba(114,247,176,.55)}
/* planner cards keep the same glass language */
.cal-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px;margin-top:18px}.cal-card{position:relative;overflow:hidden;background:linear-gradient(145deg,rgba(16,69,40,.80),rgba(4,27,16,.85));border:1px solid rgba(165,255,195,.18);border-radius:24px;padding:20px;box-shadow:0 14px 34px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.08);transition:.22s cubic-bezier(.2,.8,.2,1);backdrop-filter:blur(14px)}.cal-card:hover{transform:translateY(-7px) scale(1.012);border-color:rgba(114,247,176,.45);box-shadow:0 24px 50px rgba(0,0,0,.40),0 0 30px rgba(114,247,176,.11)}.cal-date-badge{background:rgba(114,247,176,.10);color:#72f7b0;border:1px solid rgba(114,247,176,.28);padding:5px 11px;border-radius:999px;font-size:10px;font-weight:900}.cal-task-title{color:#fff;font-family:'Outfit';font-size:17px;font-weight:800}.cal-phase{color:#a8dcb8;font-size:12px}.cal-status-tag{font-size:9px;font-weight:900;padding:5px 10px;border-radius:999px;text-transform:uppercase}.badge-notstarted{background:rgba(255,255,255,.07);color:#d1d5db}.badge-inprogress{background:rgba(245,158,11,.14);color:#fbbf24}.badge-completed{background:rgba(34,197,94,.14);color:#65f394}
[data-testid="stExpander"]{background:rgba(5,29,17,.58)!important;border:1px solid rgba(163,255,194,.15)!important;border-radius:20px!important;box-shadow:0 10px 25px rgba(0,0,0,.18)!important}.stAlert{border-radius:17px!important;background:rgba(8,42,24,.65)!important;border:1px solid rgba(163,255,194,.18)!important}
@keyframes scan{0%,55%{transform:translateX(-130%)}80%,100%{transform:translateX(180%)}}
@media(max-width:900px){.block-container{padding:18px 14px 30px!important;margin:10px!important}.headbar-card{padding:16px}.headbar-title{font-size:24px!important}.headbar-subtitle{margin-left:92px}.hero-title{font-size:32px}.donut-wrap{flex-direction:column;align-items:flex-start}.donut{width:170px;height:170px;flex-basis:170px}.donut:after{inset:42px}.schedule{align-items:flex-start;flex-wrap:wrap}.open-planner{margin-left:0}}
@media(max-width:600px){.headbar-card{display:block}.headbar-title{font-size:21px!important;gap:10px}.headbar-title img{width:52px;height:52px}.headbar-subtitle{margin-left:62px;font-size:8px}.headbar-time{margin-top:12px;display:inline-block}.hero-row{align-items:flex-start}.hero-logo{width:60px;height:60px}.hero-title{font-size:25px}.hero-sub{font-size:9px;letter-spacing:.14em}.dash-section{padding:16px}.tx-row{gap:8px}.tx-right{font-size:11px}.open-planner{width:100%;text-align:center}.sidebar-brand{padding:14px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}
/* UHD 4K rendering helpers */
img{image-rendering:auto;-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}
html,body,[class*="css"],button,input,textarea,select{ -webkit-font-smoothing:antialiased!important; -moz-osx-font-smoothing:grayscale!important; text-rendering:geometricPrecision!important; }
.stApp,.block-container,section[data-testid="stSidebar"],section[data-testid="stSidebar"] *{ text-rendering:geometricPrecision!important; }
section[data-testid="stSidebar"]{width:330px!important;min-width:330px!important;}
section[data-testid="stSidebar"]>div{padding:18px 12px 28px!important;}
.sidebar-budget-card{margin-top:2px;padding:15px 14px 8px;border:1px solid rgba(114,247,176,.12);border-radius:20px 20px 0 0;background:linear-gradient(145deg,rgba(6,38,23,.72),rgba(2,20,12,.55));box-shadow:inset 0 1px 0 rgba(255,255,255,.08);}
.budget-title{font-family:'Outfit';font-size:12px;font-weight:900;color:#f5fff8;letter-spacing:.02em;}
.sidebar-budget-card + div{margin-top:-1px;}
.sidebar-budget-card + div div[data-baseweb="input"]{border-radius:0 0 15px 15px!important;border-top-color:rgba(114,247,176,.08)!important;}
section[data-testid="stSidebar"] button{font-size:13px!important;letter-spacing:.01em!important;}
section[data-testid="stSidebar"] button p{font-size:13px!important;white-space:nowrap!important;}
@media (min-width:1920px){
  .block-container{max-width:1700px!important;}
  section[data-testid="stSidebar"]{width:350px!important;min-width:350px!important;}
  .headbar-title{font-size:31px!important;}
  section[data-testid="stSidebar"] button{min-height:58px!important;}
  section[data-testid="stSidebar"] button p{font-size:14px!important;}
}
.save-img-btn{font-weight:900!important;letter-spacing:.02em!important}

/* FINAL SIDEBAR + DASHBOARD MATCH OVERRIDES */
section[data-testid="stSidebar"]{width:322px!important;min-width:322px!important;}
section[data-testid="stSidebar"]>div{padding:22px 22px 30px!important;}
section[data-testid="stSidebar"] button{
  min-height:54px!important; height:54px!important; margin:7px 0!important;
  padding:0 18px!important; border-radius:18px!important;
  display:flex!important; align-items:center!important; justify-content:flex-start!important;
  text-align:left!important;
  background:linear-gradient(145deg,rgba(9,59,35,.72),rgba(2,30,18,.68))!important;
  border:1px solid rgba(83,236,151,.22)!important;
  box-shadow:0 10px 24px rgba(0,0,0,.20),inset 0 1px 0 rgba(255,255,255,.07)!important;
}
section[data-testid="stSidebar"] button p{
  width:100%!important; font-family:'Manrope',sans-serif!important;
  font-size:12px!important; font-weight:800!important; letter-spacing:.01em!important;
  white-space:nowrap!important; text-align:left!important;
}
section[data-testid="stSidebar"] button:hover{
  transform:translateY(-2px)!important;
  background:linear-gradient(145deg,rgba(13,87,50,.86),rgba(3,38,22,.76))!important;
  border-color:rgba(114,247,176,.55)!important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3{
  margin:24px 5px 10px!important; font-size:10px!important;
  letter-spacing:.18em!important;
}
.sidebar-brand{margin-bottom:12px!important;}
.sidebar-live{margin:0 0 10px!important;}
.sidebar-budget-card{border-radius:18px 18px 0 0!important;}
.sidebar-budget-card + div div[data-baseweb="input"]{border-radius:0 0 15px 15px!important;}

/* Remove the old duplicate title-bar language. */
.headbar-container,.headbar-card,.dash-hero{display:none!important;}

/* Single compact centered dashboard heading: no large title bar. */
.dashboard-heading{
  width:100%; display:flex; justify-content:center; align-items:center;
  gap:14px; margin:4px auto 5px; text-align:left;
}
.dashboard-heading img{width:58px;height:58px;object-fit:contain;filter:drop-shadow(0 7px 14px rgba(0,0,0,.28));}
.dashboard-heading-title{font-family:'Outfit',sans-serif;color:#fff;font-size:29px;font-weight:900;letter-spacing:.025em;line-height:1.05;text-align:center;}
.dashboard-heading-sub{margin-top:5px;color:#9fe5b8;font-size:9px;font-weight:800;letter-spacing:.20em;text-align:center;text-transform:uppercase;}
.dashboard-welcome{max-width:920px;margin:0 auto 18px;text-align:center;color:#b9d9c5;font-size:12px;font-weight:600;}
.dashboard-welcome b{color:#72f7b0;}

/* Re-center the dashboard content after removing both title bars. */
.block-container{max-width:1500px!important;padding-top:18px!important;}
@media (min-width:1920px){
  section[data-testid="stSidebar"]{width:322px!important;min-width:322px!important;}
  .block-container{max-width:1500px!important;padding-top:20px!important;}
  .dashboard-heading-title{font-size:32px;}
}
@media(max-width:900px){
  section[data-testid="stSidebar"]{width:300px!important;min-width:300px!important;}
  .dashboard-heading-title{font-size:25px;}
  .dashboard-heading img{width:50px;height:50px;}
}
@media(max-width:600px){
  .dashboard-heading{gap:9px;}
  .dashboard-heading-title{font-size:21px;}
  .dashboard-heading-sub{font-size:8px;}
  .dashboard-heading img{width:44px;height:44px;}
}
/* V10 RECEIPT VISUAL REDESIGN — LOOK ONLY */
:root {{ --v10-green:#075d2c; --v10-green-2:#0b7a3b; --v10-gold:#d6a84f; --v10-cream:#f7f5ee; --v10-ink:#17352a; --v10-line:#dfe7df; }}
body {{ background:linear-gradient(180deg,#eef5ef 0%,#f8faf7 100%) !important; color:var(--v10-ink) !important; }}
.receipt-container, .receipt-card, #receiptContent {{ border-top-color:var(--v10-green) !important; border-radius:18px !important; box-shadow:0 16px 45px rgba(7,93,44,.12),0 2px 8px rgba(0,0,0,.05) !important; position:relative; overflow:hidden; }}
.receipt-container::before, .receipt-card::before, #receiptContent::before {{ content:"⌂"; position:absolute; top:22px; left:28px; width:44px; height:44px; border-radius:12px; background:var(--v10-green); color:#fff; display:grid; place-items:center; font-size:25px; font-weight:800; box-shadow:0 5px 14px rgba(7,93,44,.22); }}
.company-info, .title {{ padding-left:62px; }}
.company-info h1, .title h1 {{ color:var(--v10-green) !important; letter-spacing:-.5px !important; font-weight:800 !important; }}
.company-info p, .title p {{ color:#617168 !important; }}
.receipt-meta h2, .meta h3 {{ color:var(--v10-green) !important; }}
.receipt-meta, .meta {{ background:var(--v10-cream); border:1px solid #eadfbe; border-radius:12px; padding:12px 15px; }}
th {{ background:var(--v10-green) !important; }}
thead tr {{ box-shadow:inset 0 -2px 0 var(--v10-gold); }}
td {{ border-bottom-color:var(--v10-line) !important; }}
tr:nth-child(even) td {{ background:#fbfcfa; }}
.desccol, .task-name {{ color:var(--v10-green) !important; }}
.grand-total {{ background:linear-gradient(135deg,var(--v10-green),#064622) !important; border:1px solid rgba(214,168,79,.45); border-radius:14px !important; box-shadow:0 10px 25px rgba(7,93,44,.16); }}
.task-card {{ border-left-color:var(--v10-gold) !important; border-radius:14px !important; box-shadow:0 6px 18px rgba(7,93,44,.07); }}
.task-date {{ color:var(--v10-green) !important; background:#eef7f0 !important; }}
.save-img-btn {{ background:var(--v10-green) !important; border-radius:10px !important; border:1px solid var(--v10-gold) !important; box-shadow:0 6px 16px rgba(7,93,44,.18) !important; }}
.save-img-btn:hover {{ background:var(--v10-green-2) !important; }}
.footer {{ color:#718078 !important; }}
@media (max-width:700px) {{ body {{ padding:8px !important; }} .receipt-container, .receipt-card, #receiptContent {{ padding:18px !important; border-radius:14px !important; }} .receipt-container::before, .receipt-card::before, #receiptContent::before {{ top:15px; left:16px; width:36px; height:36px; font-size:20px; }} .company-info, .title {{ padding-left:48px; }} .company-info h1, .title h1 {{ font-size:20px !important; }} .receipt-meta, .meta {{ padding:9px 10px; }} th, td {{ padding:8px 6px !important; font-size:11px !important; }} .save-img-btn {{ width:100%; }} }}
</style>
""", unsafe_allow_html=True)


# === FINAL SIDEBAR CLEANUP / NO CLIPPING / NO HORIZONTAL SCROLL ===
st.markdown("""
<style>
/* Keep Streamlit's sidebar stable and readable. */
section[data-testid="stSidebar"] {
  width: clamp(280px, 22vw, 340px) !important;
  min-width: 280px !important;
  max-width: 340px !important;
  box-sizing: border-box !important;
  overflow: hidden !important;
}
section[data-testid="stSidebar"] > div {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
  padding: 20px 16px 32px !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
section[data-testid="stSidebar"] .block-container,
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
}
/* Never allow a child to create a wider sidebar. */
section[data-testid="stSidebar"] * {
  box-sizing: border-box !important;
  max-width: 100% !important;
}
section[data-testid="stSidebar"] img,
section[data-testid="stSidebar"] iframe,
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] select {
  max-width: 100% !important;
}
/* Brand: clean, contained and never clipped. */
.sidebar-brand {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 0 16px !important;
  padding: 18px 16px !important;
  overflow: hidden !important;
}
.brand-row { width:100% !important; min-width:0 !important; }
.brand-logo { flex:0 0 54px !important; width:54px !important; height:54px !important; }
.brand-copy { flex:1 1 auto !important; min-width:0 !important; overflow:hidden !important; }
.brand-title { font-size:16px !important; line-height:1.05 !important; white-space:normal !important; overflow-wrap:anywhere !important; }
.brand-sub { white-space:normal !important; overflow-wrap:anywhere !important; }
.sidebar-live { width:100% !important; white-space:normal !important; overflow-wrap:anywhere !important; text-align:center !important; }
/* Navigation buttons: no forced nowrap, no negative/overflow positioning. */
section[data-testid="stSidebar"] .stButton,
section[data-testid="stSidebar"] .stButton > div { width:100% !important; max-width:100% !important; min-width:0 !important; }
section[data-testid="stSidebar"] .stButton > button:not([data-testid="stSidebarCollapseButton"]):not([aria-label*="Collapse"]):not([aria-label*="Close"]) {
  width:100% !important;
  min-width:0 !important;
  max-width:100% !important;
  min-height:48px !important;
  height:auto !important;
  margin:5px 0 !important;
  padding:12px 14px !important;
  overflow:hidden !important;
  transform:none !important;
}
section[data-testid="stSidebar"] .stButton > button p,
section[data-testid="stSidebar"] .stButton > button span {
  width:auto !important;
  min-width:0 !important;
  max-width:100% !important;
  white-space:normal !important;
  overflow-wrap:anywhere !important;
  text-overflow:clip !important;
  overflow:hidden !important;
  line-height:1.25 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover { transform:translateX(3px) !important; }
/* Budget controls and columns stay inside the sidebar. */
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
  width:100% !important; max-width:100% !important; min-width:0 !important;
}
section[data-testid="stSidebar"] [data-baseweb="input"],
section[data-testid="stSidebar"] [data-baseweb="select"],
section[data-testid="stSidebar"] .stNumberInput,
section[data-testid="stSidebar"] .stTextInput {
  width:100% !important; max-width:100% !important; min-width:0 !important;
}
/* Native collapse control is independent from navigation styling. */
button[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] button {
  width:42px !important; min-width:42px !important; height:42px !important; min-height:42px !important;
  padding:0 !important; margin:10px !important; border-radius:50% !important;
}
/* Desktop: comfortable sidebar. */
@media (min-width: 1400px) {
  section[data-testid="stSidebar"] { width:320px !important; min-width:320px !important; max-width:320px !important; }
}
/* Tablet / small laptop. */
@media (min-width: 701px) and (max-width: 1399px) {
  section[data-testid="stSidebar"] { width:300px !important; min-width:300px !important; max-width:300px !important; }
}
/* Phone: sidebar may open, but it must remain inside the viewport. */
@media (max-width: 700px) {
  section[data-testid="stSidebar"] { width:min(88vw, 300px) !important; min-width:min(88vw, 300px) !important; max-width:min(88vw, 300px) !important; }
  section[data-testid="stSidebar"] > div { padding:16px 12px 28px !important; }
  .sidebar-brand { padding:15px 13px !important; }
  .brand-logo { flex-basis:46px !important; width:46px !important; height:46px !important; }
  .brand-title { font-size:14px !important; }
  section[data-testid="stSidebar"] .stButton > button { min-height:46px !important; padding:10px 12px !important; }
}
/* V10 RECEIPT VISUAL REDESIGN — LOOK ONLY */
:root {{ --v10-green:#075d2c; --v10-green-2:#0b7a3b; --v10-gold:#d6a84f; --v10-cream:#f7f5ee; --v10-ink:#17352a; --v10-line:#dfe7df; }}
body {{ background:linear-gradient(180deg,#eef5ef 0%,#f8faf7 100%) !important; color:var(--v10-ink) !important; }}
.receipt-container, .receipt-card, #receiptContent {{ border-top-color:var(--v10-green) !important; border-radius:18px !important; box-shadow:0 16px 45px rgba(7,93,44,.12),0 2px 8px rgba(0,0,0,.05) !important; position:relative; overflow:hidden; }}
.receipt-container::before, .receipt-card::before, #receiptContent::before {{ content:"⌂"; position:absolute; top:22px; left:28px; width:44px; height:44px; border-radius:12px; background:var(--v10-green); color:#fff; display:grid; place-items:center; font-size:25px; font-weight:800; box-shadow:0 5px 14px rgba(7,93,44,.22); }}
.company-info, .title {{ padding-left:62px; }}
.company-info h1, .title h1 {{ color:var(--v10-green) !important; letter-spacing:-.5px !important; font-weight:800 !important; }}
.company-info p, .title p {{ color:#617168 !important; }}
.receipt-meta h2, .meta h3 {{ color:var(--v10-green) !important; }}
.receipt-meta, .meta {{ background:var(--v10-cream); border:1px solid #eadfbe; border-radius:12px; padding:12px 15px; }}
th {{ background:var(--v10-green) !important; }}
thead tr {{ box-shadow:inset 0 -2px 0 var(--v10-gold); }}
td {{ border-bottom-color:var(--v10-line) !important; }}
tr:nth-child(even) td {{ background:#fbfcfa; }}
.desccol, .task-name {{ color:var(--v10-green) !important; }}
.grand-total {{ background:linear-gradient(135deg,var(--v10-green),#064622) !important; border:1px solid rgba(214,168,79,.45); border-radius:14px !important; box-shadow:0 10px 25px rgba(7,93,44,.16); }}
.task-card {{ border-left-color:var(--v10-gold) !important; border-radius:14px !important; box-shadow:0 6px 18px rgba(7,93,44,.07); }}
.task-date {{ color:var(--v10-green) !important; background:#eef7f0 !important; }}
.save-img-btn {{ background:var(--v10-green) !important; border-radius:10px !important; border:1px solid var(--v10-gold) !important; box-shadow:0 6px 16px rgba(7,93,44,.18) !important; }}
.save-img-btn:hover {{ background:var(--v10-green-2) !important; }}
.footer {{ color:#718078 !important; }}
@media (max-width:700px) {{ body {{ padding:8px !important; }} .receipt-container, .receipt-card, #receiptContent {{ padding:18px !important; border-radius:14px !important; }} .receipt-container::before, .receipt-card::before, #receiptContent::before {{ top:15px; left:16px; width:36px; height:36px; font-size:20px; }} .company-info, .title {{ padding-left:48px; }} .company-info h1, .title h1 {{ font-size:20px !important; }} .receipt-meta, .meta {{ padding:9px 10px; }} th, td {{ padding:8px 6px !important; font-size:11px !important; }} .save-img-btn {{ width:100%; }} }}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-brand">
      <div class="brand-row">
        <img class="brand-logo" src="{AILYN_LOGO_DATA}" alt="Ailyn Construction Logo">
        <div class="brand-copy">
          <div class="brand-title"><span>AILYN</span><span>CONSTRUCTION</span></div>
          <div class="brand-sub">Official Project Control</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        f"<div class='sidebar-live'><span>●</span> &nbsp; LIVE SYSTEM &nbsp; • &nbsp; "
        f"{datetime.now().strftime('%I:%M %p  |  %b %d')}</div>",
        unsafe_allow_html=True
    )

    st.subheader("Executive Overview")
    if st.button("▣   Dashboard   ›", use_container_width=True, key="side_dashboard"):
        set_view("home")

    st.markdown("<div class='sidebar-budget-card'><div class='budget-title'>Set Account Budget</div></div>", unsafe_allow_html=True)
    budget_input = st.number_input(
        "Set Account Budget",
        min_value=0.0,
        key="budget_input_sidebar",
        value=None,
        placeholder="Enter budget...",
        label_visibility="collapsed",
    )
    if st.button("＋   Apply Budget", use_container_width=True, key="side_apply_budget"):
        if budget_input is not None:
            st.session_state.budget = float(budget_input)
            persist_state()
            st.success("Budget applied!")
            st.rerun()
        else:
            st.warning("Please enter a budget amount.")

    if st.button("⚙   Restart System   ›", use_container_width=True, key="side_restart"):
        clear_all()
        set_view("home")

    st.subheader("Project Control")
    if st.button("▣   New Work Entry   ›", use_container_width=True, key="side_new_work"):
        set_view("planner_input")
    if st.button("☷   Schedule & Progress   ›", use_container_width=True, key="side_schedule"):
        set_view("planner_output")

    st.subheader("Financial Operations")
    if st.button("◇   Material Entry   ›", use_container_width=True, key="side_material"):
        set_view("material")
    if st.button("▤   Expense Entry   ›", use_container_width=True, key="side_expense"):
        set_view("expense")
    if st.button("♨   Encash Deposit   ›", use_container_width=True, key="side_excess"):
        set_view("excess")
    if st.button("▣   Financial Ledger   ›", use_container_width=True, key="side_ledger"):
        set_view("ledger")
    if st.button("▥   Financial Report   ›", use_container_width=True, key="side_financial_report"):
        set_view("export")

    st.subheader("Payroll Operations")
    if st.button("●   Labor Account   ›", use_container_width=True, key="side_labor"):
        set_view("add_labor")
    if st.button("▣   Payroll Expense   ›", use_container_width=True, key="side_payroll_expense"):
        set_view("add_payroll_expense")
    if st.button("♟   Account Remainder   ›", use_container_width=True, key="side_payroll_remaining"):
        set_view("payroll_remaining")
    if st.button("♟   Labor Accounts   ›", use_container_width=True, key="side_payroll_ledger"):
        set_view("payroll_ledger")
    if st.button("▤   Payroll Report   ›", use_container_width=True, key="side_payroll_report"):
        set_view("payroll_export")
    if st.button("▣   Receipts Archive   ›", use_container_width=True, key="side_archive"):
        set_view("receipt_archive")

view = st.session_state.view

if view == "home":
    budget = float(st.session_state.budget or 0)
    used = float(get_total() or 0)
    balance = float(get_balance() or 0)
    workers = len(st.session_state.labor_records)
    material = float(total_materials() or 0)
    labor = float(sum(r.get("net", 0) for r in st.session_state.labor_records))
    expenses = float(total_expenses() or 0)
    excess = float(total_excess() or 0)
    chart_total = max(material + labor + expenses + excess, 1.0)
    p1 = material / chart_total * 360
    p2 = p1 + labor / chart_total * 360
    p3 = p2 + expenses / chart_total * 360
    today_key = datetime.now().strftime("%Y-%m-%d")
    today_tasks = [t for t in st.session_state.planner_tasks if t.get("date_obj") == today_key]
    upcoming_tasks = [t for t in st.session_state.planner_tasks if t.get("date_obj", "") >= today_key]

    st.markdown(f"""
    <div class="dashboard-heading">
      <img src="{AILYN_LOGO_DATA}" alt="Ailyn Construction Logo">
      <div>
        <div class="dashboard-heading-title">AILYN CONSTRUCTION</div>
        <div class="dashboard-heading-sub">PROJECT MANAGEMENT SYSTEM</div>
      </div>
    </div>
    <div class="dashboard-welcome">🛡️ &nbsp; Welcome back, <b>Ailyn Project!</b> &nbsp;|&nbsp; Manage your construction project efficiently.</div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("TOTAL BUDGET", f"₱{budget:,.2f}")
    with m2: st.metric("TOTAL EXPENSES", f"₱{used:,.2f}")
    with m3: st.metric("REMAINING BALANCE", f"₱{balance:,.2f}")
    with m4: st.metric("TOTAL WORKERS", workers)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.05, 1])
    with left:
        st.markdown(f"""
        <div class="dash-section">
          <div class="section-head"><div class="section-title" style="margin:0">EXPENSES OVERVIEW</div><span style="font-size:11px;color:#7b867f;font-weight:700">THIS PROJECT</span></div>
          <div class="donut-wrap">
            <div class="donut" style="--p1:{p1}deg;--p2:{p2}deg;--p3:{p3}deg"><div class="donut-center">₱{used:,.0f}<small>Total Expenses</small></div></div>
            <div class="legend">
              <div class="legend-row"><span><i class="dot" style="background:#075c28"></i>Materials</span><b>₱{material:,.2f}</b></div>
              <div class="legend-row"><span><i class="dot" style="background:#8fc77d"></i>Labor</span><b>₱{labor:,.2f}</b></div>
              <div class="legend-row"><span><i class="dot" style="background:#e0aa25"></i>Expenses</span><b>₱{expenses:,.2f}</b></div>
              <div class="legend-row"><span><i class="dot" style="background:#e85d4a"></i>Excess</span><b>₱{excess:,.2f}</b></div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with right:
        tx = list(reversed(st.session_state.records))[:5]
        tx_html = ""
        if tx:
            for r in tx:
                icon = "🛒" if r.get("type") == "material" else "▣" if r.get("type") == "expense" else "+"
                tx_html += f'''<div class="tx-row"><div class="tx-left"><div class="tx-icon">{icon}</div><div><div class="tx-name">{r.get("name", "Transaction")}</div><div class="tx-type">{str(r.get("type", "")).title()}</div></div></div><div class="tx-right">₱{float(r.get("amount", 0)):,.2f}<div class="tx-date">{r.get("date", "")}</div></div></div>'''
        else:
            tx_html = '<div style="padding:30px 0;color:#7a857e;text-align:center">No transactions yet.</div>'
        st.markdown(f'''<div class="dash-section"><div class="section-head"><div class="section-title" style="margin:0">RECENT TRANSACTIONS</div><span style="font-size:11px;color:#7b867f">LATEST 5</span></div>{tx_html}</div>''', unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="dash-section">
      <div class="schedule">
        <div class="schedule-icon">▦</div>
        <div><div class="schedule-title">TODAY'S SCHEDULE</div><div style="font-weight:800;font-size:13px;margin-top:4px">{datetime.now().strftime('%B %d, %Y (%A)')}</div><div class="schedule-muted">{len(today_tasks)} task(s) scheduled for today.</div></div>
        <div style="width:1px;height:58px;background:#dfe8e1;margin:0 12px"></div>
        <div><div class="schedule-title">UPCOMING TASKS</div><div style="font-weight:800;font-size:13px;margin-top:4px">{len(upcoming_tasks)} task(s) planned</div><div class="schedule-muted">Stay on track and manage your construction tasks.</div></div>
        <div style="margin-left:auto"><div class="open-planner">▣ &nbsp; Open Planner</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("OPEN CONSTRUCTION PLANNER", use_container_width=True):
        set_view("planner_output")

elif view == "planner_input":
    st.subheader("📅 PLANNER INPUT - ADD NEW WORK TASK")
    st.caption("Select date details, work description, and optional photo proofs.")
    with st.form(key="planner_input_form", clear_on_submit=True):
        selected_date = st.date_input("Select Day, Month, and Year", value=datetime.now())
        work_description = st.text_area("Work Description / Task Details", placeholder="Describe construction work...")
        phase = st.selectbox("Construction Phase", ["Site Prep", "Foundation", "Framing & Masonry", "Roofing", "Plumbing & Electrical", "Finishing", "Inspection"])
        uploaded_files = st.file_uploader("Upload Work Proof Photos (Optional)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        submitted = st.form_submit_button("💾 SAVE TASK TO PERMANENT STORAGE")
        
        if submitted:
            if work_description.strip():
                photos_base64 = []
                if uploaded_files:
                    for file in uploaded_files:
                        bytes_data = file.read()
                        b64_str = base64.b64encode(bytes_data).decode('utf-8')
                        mime_type = file.type or "image/png"
                        photos_base64.append(f"data:{mime_type};base64,{b64_str}")
                st.session_state.planner_tasks.append({
                    "id": str(time.time()),
                    "day": selected_date.strftime("%d"),
                    "month": selected_date.strftime("%B"),
                    "year": selected_date.strftime("%Y"),
                    "date_obj": selected_date.strftime("%Y-%m-%d"),
                    "name": work_description.upper(),
                    "phase": phase,
                    "status": "Not Started",
                    "photos": photos_base64
                })
                persist_state()
                st.success("Task & photos permanently saved!")
                st.rerun()
            else:
                st.warning("Please fill in the work description.")
    st.divider()
    if st.button("🏠 RETURN TO HOME", use_container_width=True):
        set_view("home")

elif view == "planner_output":
    st.subheader("📋 PLANNER OUTPUT - WORK SCHEDULE CALENDAR")
    tasks = st.session_state.planner_tasks
    if not tasks:
        st.info("No work scheduled yet.")
    else:
        sorted_tasks = sorted(tasks, key=lambda x: x.get('date_obj', ''))
        cards_html = '<div class="cal-grid">'
        for t in sorted_tasks:
            badge_class = "badge-completed" if t['status'] == "Completed" else "badge-inprogress" if t['status'] == "In Progress" else "badge-notstarted"
            photos_thumbs = ""
            if t.get("photos"):
                photos_thumbs = '<div class="card-photos">'
                for p in t["photos"]:
                    photos_thumbs += f'<img src="{p}" class="card-photo-thumb" />'
                photos_thumbs += '</div>'
            cards_html += f"""
            <div class="cal-card">
              <div class="cal-date-badge">📅 {t.get("month", "")} {t.get("day", "")}, {t.get("year", "")}</div>
              <div class="cal-task-title">{t["name"]}</div>
              <div class="cal-phase">🛠️ Phase: {t["phase"]}</div>
              <div class="cal-status-tag {badge_class}">{t["status"]}</div>
              {photos_thumbs}
            </div>
            """
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)
        st.markdown("<div class='sidebar-gap'></div>", unsafe_allow_html=True)
        st.subheader("⚙️ Task Management & Photo Inspector")
        
        for t in list(sorted_tasks):
            with st.expander(f"📌 {t.get('month')} {t.get('day')}, {t.get('year')} - {t['name']} ({t['status']})", expanded=False):
                col1, col2 = st.columns([2, 1])
                with col1:
                    new_status = st.selectbox("Update Status", ["Not Started", "In Progress", "Completed"], index=["Not Started", "In Progress", "Completed"].index(t["status"]), key=f"st_{t['id']}")
                    if new_status != t["status"]:
                        t["status"] = new_status
                        persist_state()
                        st.rerun()
                with col2:
                    if st.button("❌ Delete Task", key=f"del_{t['id']}", use_container_width=True):
                        st.session_state.planner_tasks = [x for x in st.session_state.planner_tasks if x["id"] != t["id"]]
                        persist_state()
                        st.rerun()
                        
                st.markdown("#### 📸 Work Gallery for this Day")
                if t.get("photos"):
                    img_cols = st.columns(4)
                    for idx, photo_b64 in enumerate(list(t["photos"])):
                        with img_cols[idx % 4]:
                            st.image(photo_b64, use_container_width=True)
                            if st.button("🗑️ Remove Photo", key=f"del_img_{t['id']}_{idx}", use_container_width=True):
                                t["photos"].pop(idx)
                                persist_state()
                                st.rerun()
                else:
                    st.info("No photo proof attached for this work day yet.")
                    
                st.markdown("##### Add More Photos")
                with st.form(key=f"upload_form_{t['id']}", clear_on_submit=True):
                    new_photos = st.file_uploader("Upload Additional Photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=f"up_{t['id']}")
                    add_photos_btn = st.form_submit_button("📤 UPLOAD PHOTOS")
                    if add_photos_btn and new_photos:
                        if "photos" not in t or t["photos"] is None:
                            t["photos"] = []
                        for f in new_photos:
                            bytes_data = f.read()
                            b64_str = base64.b64encode(bytes_data).decode('utf-8')
                            mime_type = f.type or "image/png"
                            t["photos"].append(f"data:{mime_type};base64,{b64_str}")
                        persist_state()
                        st.success("Photos added successfully!")
                        st.rerun()
                        
    st.markdown("<div class='sidebar-gap'></div>", unsafe_allow_html=True)
    custom_receipt_title = st.text_input("Receipt Title", value="Construction Schedule Receipt", placeholder="Enter a custom title...")
    html_report = generate_planner_html(sorted_tasks, custom_title=custom_receipt_title)
    st.markdown("### 🖼️ SEE PHOTO & DOWNLOAD SCHEDULE RECEIPT")
    st.components.v1.html(html_report, height=620, scrolling=False)
    st.download_button(
        label="📥 DOWNLOAD SCHEDULE RECEIPT HTML",
        data=html_report,
        file_name="construction_schedule_receipt.html",
        mime="text/html",
        use_container_width=True
    )
    st.divider()
    if st.button("🏠 RETURN TO HOME", use_container_width=True):
        set_view("home")

elif view == "material":
    st.subheader("➕ ADD MATERIAL")
    with st.form(key="material_form", clear_on_submit=True):
        name = st.text_input("Material Name")
        price = st.number_input("Price", min_value=0.01, value=None, placeholder="0.00")
        qty = st.number_input("Qty", min_value=1, value=None, placeholder="1")
        delivery = st.number_input("Delivery", min_value=0.0, value=None, placeholder="0.00")
        sender = st.selectbox("Sender", ["Garr", "Aily"])
        submitted = st.form_submit_button(label="SAVE MATERIAL")
        if submitted:
            ok = add_tx(name, price, qty, delivery or 0.0, "material", sender)
            if ok:
                st.success("Saved! Ready for next order.")
                st.rerun()
            else:
                st.warning("Invalid data, please fill out Price and Qty.")
    st.divider()
    if st.button("🏠 RETURN TO HOME", use_container_width=True):
        set_view("home")

elif view == "expense":
    st.subheader("➕ ADD CONSTRUCTION EXPENSE")
    with st.form(key="expense_form", clear_on_submit=True):
        name = st.text_input("Expense Name")
        amount = st.number_input("Amount", min_value=0.01, value=None, placeholder="0.00")
        sender = st.selectbox("Sender", ["Garr", "Aily"])
        submitted = st.form_submit_button(label="SAVE EXPENSE")
        if submitted:
            if amount and amount > 0:
                add_tx(name, amount, 1, 0, "expense", sender)
                st.success("Expense Added → Ledger Updated")
                st.rerun()
            else:
                st.warning("Please enter an amount greater than zero.")
    st.divider()
    if st.button("🏠 RETURN TO HOME", use_container_width=True):
        set_view("home")

elif view == "excess":
    st.subheader("➕ ADD EXCESS MONEY")
    with st.form(key="excess_form", clear_on_submit=True):
        name = st.text_input("Reason")
        amount = st.number_input("Amount", min_value=0.01, value=None, placeholder="0.00")
        sender = st.selectbox("Sender", ["Garr", "Aily"])
        submitted = st.form_submit_button(label="ADD EXCESS")
        if submitted:
            if amount and amount > 0:
                st.session_state.records.append({
                    "id": str(time.time()),
                    "date": datetime.now().strftime("%b %d, %Y"),
                    "name": name.upper(),
                    "price": float(amount),
                    "qty": 1,
                    "delivery": 0.0,
                    "amount": float(amount),
                    "type": "excess",
                    "sender": sender
                })
                persist_state()
                st.success("Excess Added")
                st.rerun()
            else:
                st.warning("Please enter a valid amount.")
    st.divider()
    if st.button("🏠 RETURN TO HOME", use_container_width=True):
        set_view("home")

elif view == "ledger":
    st.subheader("📖 CONSTRUCTION LEDGER")
    if not st.session_state.records:
        st.info("No transaction records found in ledger.")
    else:
        for r in list(st.session_state.records):
            st.markdown(f"""
            ---
            **{r['name']}** • PHP {float(r['amount']):,.2f}  
            👤 {r['sender']} | 🏷️ {r['type']} | 📅 {r['date']}
            """)
            if st.button("❌ DELETE ENTRY", key=f"del_{r['id']}", use_container_width=True):
                st.session_state.records = [x for x in st.session_state.records if x["id"] != r["id"]]
                persist_state()
                st.rerun()

elif view == "export":
    st.subheader("📄 EXPORT CONSTRUCTION REPORT")
    receipt_title = st.text_input("Receipt Title", value="Construction Receipt", placeholder="Enter a title for this receipt")
    html = build_html_report(st.session_state.records, st.session_state.budget, custom_title=receipt_title)
    st.components.v1.html(html, height=620, scrolling=False)
    if st.button("💾 SAVE RECEIPT TO ARCHIVE", use_container_width=True):
        if receipt_title.strip():
            archive_path = save_report_html("construction", html, title=receipt_title)
            st.success(f"Saved to archive: {archive_path}")
        else:
            st.warning("Please enter a title before saving.")
    st.download_button(
        label="📥 DOWNLOAD CONSTRUCTION REPORT HTML",
        data=html,
        file_name="construction_report.html",
        mime="text/html",
        use_container_width=True
    )
    if st.button("📂 OPEN RECEIPT ARCHIVE", use_container_width=True):
        set_view("receipt_archive")

elif view == "add_labor":
    st.subheader("👷 ADD LABOR ACCOUNT")
    st.caption("Click a role button below (Cashier POS Style) to select the work role quickly:")
    
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        if st.button("LABOR\n₱500 / day", use_container_width=True):
            st.session_state.selected_role = "Labor"
    with col_r2:
        if st.button("SKILL\n₱650 / day", use_container_width=True):
            st.session_state.selected_role = "Skill"
    with col_r3:
        if st.button("FORMAN\n₱800 / day", use_container_width=True):
            st.session_state.selected_role = "Forman"
            
    active_role = st.session_state.selected_role
    st.markdown(f"""
    <div class="pos-role-box">
      CURRENTLY SELECTED ROLE: <span style="color:#4ade80; font-size:20px;">{active_role.upper()}</span> (₱{FULL_DAY_RATES[active_role]:,.2f}/day)
    </div>
    """, unsafe_allow_html=True)
    
    with st.form(key="labor_input_form", clear_on_submit=True):
        name = st.text_input("Worker Name")
        days = st.number_input("Worked Days / Point", min_value=0.1, value=1.0, step=0.1, placeholder="1.0")
        ca = st.number_input("Cash Advance (C.A.)", min_value=0.0, value=None, placeholder="0.00")
        submitted = st.form_submit_button("💾 SAVE LABOR ACCOUNT")
        
        if submitted:
            d = float(days or 0.0)
            c = float(ca or 0.0)
            if d > 0 and name.strip():
                gross_pay, full_pay, partial_pay = calculate_labor_pay(d, active_role)
                net = gross_pay - c
                rate = FULL_DAY_RATES.get(active_role, 0.0)
                st.session_state.labor_records.append({
                    "name": name.upper(),
                    "role": active_role,
                    "days": d,
                    "rate": rate,
                    "gross_pay": gross_pay,
                    "ca": c,
                    "net": net
                })
                persist_state()
                st.success(f"Record for {name.upper()} ({active_role}, {d:.1f} day) added. Net: PHP {net:,.2f}")
                st.rerun()
            else:
                st.warning("Please enter a worker name and valid worked days/points.")

elif view == "add_payroll_expense":
    st.subheader("➕ ADD PAYROLL EXPENSE")
    with st.form(key="payroll_expense_form", clear_on_submit=True):
        desc = st.text_input("Expense Description")
        amt = st.number_input("Amount", min_value=0.01, value=None, placeholder="0.00")
        submitted = st.form_submit_button("💾 SAVE EXPENSE")
        if submitted:
            if amt and amt > 0:
                st.session_state.payroll_expenses.append({
                    "item": desc.upper(),
                    "price": float(amt)
                })
                persist_state()
                st.success(f"Expense {desc.upper()} added.")
                st.rerun()
            else:
                st.warning("Please enter a valid amount.")

elif view == "payroll_remaining":
    st.subheader("⚙️ SET REMAINING MONEY")
    res = st.number_input("Leftover/Remaining money to subtract from total", min_value=0.0, value=None, placeholder="0.00")
    if st.button("APPLY REMAINING MONEY", use_container_width=True):
        if res is not None:
            st.session_state.remaining_money = float(res)
            persist_state()
            st.success("Remaining money applied.")
            st.rerun()
        else:
            st.warning("Please enter an amount.")

elif view == "payroll_ledger":
    st.subheader("📋 LABOR & PAYROLL LEDGER")
    st.markdown("### Labor Records")
    if not st.session_state.labor_records:
        st.info("No labor records.")
    else:
        for i, r in enumerate(list(st.session_state.labor_records)):
            role_disp = r.get('role', 'Labor')
            gross_disp = r.get('gross_pay', r['days'] * r['rate'])
            st.markdown(f"""
            ---
            **{r['name']}** ({role_disp}) • Worked: {r['days']:.1f} Day(s)  
            • Gross Pay: PHP {gross_disp:,.2f}  
            • C.A.: PHP {r['ca']:,.2f}  
            • **Net Pay: PHP {r['net']:,.2f}**
            """)
            if st.button("❌ DELETE LABOR ENTRY", key=f"del_lab_{i}", use_container_width=True):
                st.session_state.labor_records.pop(i)
                persist_state()
                st.rerun()
                
    st.markdown("<div class='sidebar-gap'></div>", unsafe_allow_html=True)
    st.markdown("### Payroll Expenses")
    if not st.session_state.payroll_expenses:
        st.info("No payroll expenses.")
    else:
        for i, e in enumerate(list(st.session_state.payroll_expenses)):
            st.markdown(f"- **{e['item']}**: PHP {e['price']:,.2f}")
            if st.button("❌ DELETE PAYROLL EXPENSE", key=f"del_pay_exp_{i}", use_container_width=True):
                st.session_state.payroll_expenses.pop(i)
                persist_state()
                st.rerun()

elif view == "payroll_export":
    st.subheader("📄 EXPORT PAYROLL REPORT")
    receipt_title = st.text_input("Receipt Title", value="Payroll Receipt", placeholder="Enter a title for this receipt")
    html, total = generate_payroll_html(
        st.session_state.labor_records,
        st.session_state.payroll_expenses,
        st.session_state.remaining_money,
        custom_title=receipt_title
    )
    st.components.v1.html(html, height=620, scrolling=False)
    if st.button("💾 SAVE RECEIPT TO ARCHIVE", use_container_width=True):
        if receipt_title.strip():
            archive_path = save_report_html("payroll", html, title=receipt_title)
            st.success(f"Saved to archive: {archive_path}")
        else:
            st.warning("Please enter a title before saving.")
    st.download_button(
        label="📥 DOWNLOAD PAYROLL REPORT HTML",
        data=html,
        file_name="payroll_report.html",
        mime="text/html",
        use_container_width=True
    )
    if st.button("📂 OPEN RECEIPT ARCHIVE", use_container_width=True):
        set_view("receipt_archive")
    if st.button("📧 EMAIL PAYROLL REPORT", use_container_width=True):
        try:
            msg = EmailMessage()
            msg['Subject'] = f"Construction Report: PHP {total:,.2f} - {datetime.now().strftime('%Y-%m-%d')}"
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECEIVER_EMAIL
            msg.add_alternative(html, subtype='html')
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
                smtp.send_message(msg)
            st.success("✅ SUCCESS! Emailed report.")
        except Exception as e:
            st.error(f"❌ EMAIL FAILED: {e}")

elif view == "receipt_archive":
    st.subheader("📂 RECEIPT ARCHIVE")
    st.caption("Browse saved receipts in neat construction and payroll folders.")
    if st.button("⬅️ BACK TO CONSTRUCTION EXPORT", use_container_width=True):
        set_view("export")
    if st.button("⬅️ BACK TO PAYROLL EXPORT", use_container_width=True):
        set_view("payroll_export")
        
    for title, report_type in [("🏗️ Construction Receipts", "construction"), ("👷 Payroll Receipts", "payroll")]:
        with st.expander(title, expanded=True):
            saved_reports = list_saved_reports(report_type)
            if not saved_reports:
                st.info(f"No saved {report_type} receipts yet.")
                continue
            for report_path in saved_reports:
                st.markdown(f"- **{report_path.name}**")
                with open(report_path, "r", encoding="utf-8") as handle:
                    report_html = handle.read()
                st.components.v1.html(report_html, height=620, scrolling=False)
                st.download_button(
                    label="📥 DOWNLOAD THIS RECEIPT HTML",
                    data=report_html,
                    file_name=report_path.name,
                    mime="text/html",
                    use_container_width=True,
                    key=f"download_{report_type}_{report_path.name}"
                )
                if st.button("❌ DELETE THIS RECEIPT", key=f"delete_{report_type}_{report_path.name}", use_container_width=True):
                    delete_report_file(report_path)
                    st.success(f"Deleted: {report_path.name}")
                    st.rerun()

else:
    st.info("Welcome to Ailyn Project Management System. Use the command sidebar to navigate.")