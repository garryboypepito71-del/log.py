import os
import time
import base64
import html as html_lib
from datetime import datetime
import streamlit as st
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

APP_VERSION = "AILYHOUSEPROJECT — Construction Management System"
RECEIVER_EMAIL = "garryboypepito2004@gmail.com"
RECEIVER_AILYN = "ailyn_peps0678@yahoo.com"
SENDER_EMAIL = "garryboypepito71@gmail.com"
SENDER_PASSWORD = "fhyv cimp gync wjmj"

st.set_page_config(
    page_title="AILYHOUSEPROJECT",
    page_icon="🏠",
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
.desccol {{ font-weight: 800; color: #0f7a45; letter-spacing: 0.2px; }}
.word-material {{ color: #087f5b; font-weight: 800; }}
.word-expense {{ color: #b45309; font-weight: 800; }}
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
</style>
</head>
<body>
<div class="save-btn-container">
<button class="save-img-btn" onclick="saveAsImage()">SEE PHOTO & DOWNLOAD IMAGE (Phone & Laptop)</button>
</div>
<div class="receipt-container" id="receiptContent">
<div class="header">
<div class="company-info">
<h1>AILYN HOUSE PROJECT</h1>
<p>Official Material & Expense Inventory</p>
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
        description_class = "word-expense" if r.get("type") == "expense" else "word-material"
        safe_description = html_lib.escape(str(r.get("name", "")))
        description_words = " ".join(
            f'<span class="{description_class}">{word}</span>'
            for word in safe_description.split()
        )
        html += f"""
<tr>
<td>{r['date']}</td>
<td class="qty-col">{r['qty']}</td>
<td class="desccol">{description_words}</td>
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
</style>
</head>
<body style="font-family: 'Segoe UI', sans-serif; background-color: #f4f7f6; padding: 40px;">
<div class="save-btn-container">
<button class="save-img-btn" onclick="saveAsImage()">SEE PHOTO & DOWNLOAD IMAGE (Phone & Laptop)</button>
</div>
<div id="receiptContent" style="max-width: 900px; margin: auto; background: white; border-top: 10px solid #1b5e20; padding: 40px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
<table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
<tr>
<td>
<h1 style="color: #1b5e20; margin: 0; text-transform: uppercase;">Ailyn Construction</h1>
<p style="color: #555; margin: 5px 0 0 0;">Official Labor & Payroll Inventory</p>
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

def generate_planner_html(planner_tasks, custom_title="WORK SCHEDULE & CALENDAR RECEIPT"):
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
</style>
</head>
<body>
<div class="save-btn-container">
<button class="save-img-btn" onclick="saveAsImage()">SEE PHOTO & DOWNLOAD IMAGE (Phone & Laptop)</button>
</div>
<div class="receipt-card" id="receiptContent">
<div class="header">
<div class="title">
<h1>{custom_title}</h1>
<p>AILYN HOUSE PROJECT MANAGEMENT</p>
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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --glass: rgba(9, 28, 18, 0.72);
  --glass-2: rgba(17, 52, 31, 0.62);
  --line: rgba(190, 255, 215, 0.22);
  --line-strong: rgba(147, 255, 186, 0.52);
  --green: #65f59a;
  --green-2: #29c96a;
  --mint: #caffdd;
  --ink: #f5fff8;
  --muted: #9bc8aa;
  --deep: #03150b;
}

/* ---------- KEEP THE ORIGINAL SYSTEM BACKGROUND ---------- */
.stApp {
  background: url("https://images.unsplash.com/photo-1600585154340-be6161a56a0c") no-repeat center center fixed;
  background-size: cover;
  background-position: center;
  min-height: 100vh;
  font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Subtle glass atmosphere over the SAME background — no replacement image. */
.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 15% 10%, rgba(91,255,151,.10), transparent 28%),
    radial-gradient(circle at 85% 80%, rgba(35,196,106,.08), transparent 30%),
    linear-gradient(120deg, rgba(2,15,8,.22), rgba(2,15,8,.08));
  z-index: 0;
}

.block-container {
  position: relative;
  z-index: 1;
  background: linear-gradient(145deg, rgba(9,31,18,.79), rgba(5,20,12,.67)) !important;
  backdrop-filter: blur(24px) saturate(130%);
  -webkit-backdrop-filter: blur(24px) saturate(130%);
  border: 1px solid rgba(191,255,215,.16);
  border-radius: 30px;
  box-shadow: 0 30px 90px rgba(0,0,0,.48), inset 0 1px 0 rgba(255,255,255,.07);
  padding: 34px 28px 30px !important;
  margin-top: 14px !important;
}

/* ---------- PREMIUM SIDEBAR ---------- */
section[data-testid="stSidebar"] {
  background:
    radial-gradient(circle at 20% 0%, rgba(102,255,166,.13), transparent 25%),
    linear-gradient(180deg, rgba(7,31,18,.96) 0%, rgba(2,16,9,.985) 100%) !important;
  backdrop-filter: blur(26px) saturate(140%);
  -webkit-backdrop-filter: blur(26px) saturate(140%);
  border-right: 1px solid rgba(176,255,204,.18);
  box-shadow: 16px 0 55px rgba(0,0,0,.38), inset -1px 0 0 rgba(255,255,255,.03);
}
section[data-testid="stSidebar"] * { color: #eafff0 !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding: 18px 13px 32px; }
section[data-testid="stSidebar"] hr { border-color: rgba(147,255,186,.12) !important; margin: 15px 0 !important; }
section[data-testid="stSidebar"] .stCaption { color: #86b99a !important; }

.sidebar-brand {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 14px;
  min-height: 72px;
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(45,127,77,.45), rgba(4,24,13,.72)),
    radial-gradient(circle at 15% 10%, rgba(199,255,218,.18), transparent 38%);
  border: 1px solid rgba(191,255,215,.27);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.18),
    inset 0 -1px 0 rgba(0,0,0,.25),
    0 10px 0 rgba(0,10,5,.45),
    0 24px 40px rgba(0,0,0,.30);
  backdrop-filter: blur(22px) saturate(150%);
  -webkit-backdrop-filter: blur(22px) saturate(150%);
}
.sidebar-brand::before {
  content: "";
  position: absolute;
  width: 150px; height: 150px;
  right: -65px; top: -90px;
  border-radius: 50%;
  background: rgba(102,255,166,.13);
  filter: blur(5px);
}
.sidebar-brand::after {
  content: "AILY";
  position: absolute;
  right: 12px; bottom: 8px;
  font: 800 7px/1 'Space Grotesk', sans-serif;
  letter-spacing: .28em;
  color: rgba(201,255,220,.27) !important;
}
.brand-icon {
  position: relative;
  z-index: 2;
  width: 47px; height: 47px;
  flex: 0 0 47px;
  display: grid; place-items: center;
  border-radius: 15px;
  background:
    linear-gradient(145deg, #9affbd 0%, #35d875 46%, #0a6737 100%);
  color: #03200f !important;
  border: 1px solid rgba(234,255,241,.58);
  box-shadow:
    inset 0 2px 0 rgba(255,255,255,.55),
    0 7px 0 rgba(2,28,14,.55),
    0 14px 25px rgba(39,213,109,.20);
  transform: perspective(500px) rotateX(7deg) rotateY(-7deg);
}
.brand-icon span { color: #03200f !important; font: 900 14px/1 'Space Grotesk', sans-serif; letter-spacing: -.05em; }
.brand-copy { position: relative; z-index: 2; min-width: 0; }
.sidebar-brand h3 {
  margin: 0 0 3px !important;
  font: 800 15px/1.1 'Space Grotesk', sans-serif !important;
  letter-spacing: .12em;
  color: #ffffff !important;
}
.sidebar-brand p {
  margin: 0 !important;
  color: #a9dfbb !important;
  font: 600 9px/1.4 'Plus Jakarta Sans', sans-serif;
  letter-spacing: .08em;
  text-transform: uppercase;
}

section[data-testid="stSidebar"] .stSubheader,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 700 !important;
  letter-spacing: .07em;
  color: #d9ffe6 !important;
}
section[data-testid="stSidebar"] .stSubheader { font-size: 11px !important; text-transform: uppercase; margin: 11px 3px 7px; }

/* Every sidebar action gets real layered 3D glass depth. */
section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] .stDownloadButton > button {
  position: relative;
  overflow: hidden;
  width: 100%;
  min-height: 48px;
  margin: 6px 0;
  padding: 10px 14px;
  border-radius: 17px !important;
  color: #f5fff8 !important;
  border: 1px solid rgba(203,255,221,.20) !important;
  background:
    linear-gradient(105deg, transparent 0%, rgba(255,255,255,.035) 36%, rgba(255,255,255,.20) 50%, rgba(255,255,255,.035) 64%, transparent 100%),
    linear-gradient(145deg, rgba(39,105,65,.68), rgba(5,27,15,.84)) !important;
  background-size: 240% 100%, 100% 100%;
  background-position: 125% 0, 0 0;
  box-shadow:
    inset 0 2px 0 rgba(255,255,255,.15),
    inset 0 -1px 0 rgba(0,0,0,.34),
    0 6px 0 rgba(0,10,5,.70),
    0 13px 24px rgba(0,0,0,.27);
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
  transform: perspective(900px) translateZ(0);
  transform-style: preserve-3d;
  transition: transform .16s cubic-bezier(.2,.8,.2,1), box-shadow .16s ease, border-color .16s ease, background-position .55s ease !important;
}
section[data-testid="stSidebar"] .stButton > button::before,
section[data-testid="stSidebar"] .stDownloadButton > button::before {
  content: "";
  position: absolute; left: 9px; right: 9px; top: 5px; height: 1px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.62), transparent);
  opacity: .68;
  pointer-events: none;
}
section[data-testid="stSidebar"] .stButton > button::after,
section[data-testid="stSidebar"] .stDownloadButton > button::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 0%, rgba(115,255,166,.16), transparent 52%);
  opacity: 0;
  transition: opacity .18s ease;
  pointer-events: none;
}
section[data-testid="stSidebar"] .stButton > button:hover,
section[data-testid="stSidebar"] .stDownloadButton > button:hover {
  transform: perspective(900px) translateY(-5px) rotateX(1.2deg) scale(1.012);
  border-color: rgba(158,255,194,.65) !important;
  background-position: -25% 0, 0 0;
  box-shadow:
    inset 0 2px 0 rgba(255,255,255,.22),
    inset 0 -1px 0 rgba(0,0,0,.32),
    0 10px 0 rgba(0,10,5,.60),
    0 23px 38px rgba(33,211,105,.19),
    0 0 24px rgba(110,255,161,.12);
}
section[data-testid="stSidebar"] .stButton > button:hover::after,
section[data-testid="stSidebar"] .stDownloadButton > button:hover::after { opacity: 1; }
section[data-testid="stSidebar"] .stButton > button:active,
section[data-testid="stSidebar"] .stDownloadButton > button:active {
  transform: perspective(900px) translateY(4px) scale(.992);
  box-shadow: inset 0 5px 11px rgba(0,0,0,.25), 0 2px 0 rgba(0,10,5,.82) !important;
}
section[data-testid="stSidebar"] .stButton > button p,
section[data-testid="stSidebar"] .stDownloadButton > button p {
  position: relative; z-index: 3;
  font: 700 11px/1.25 'Space Grotesk', sans-serif !important;
  letter-spacing: .045em;
  text-shadow: 0 1px 8px rgba(0,0,0,.38);
}

/* Budget input becomes a recessed glass control. */
section[data-testid="stSidebar"] [data-baseweb="input"],
section[data-testid="stSidebar"] input {
  border-radius: 15px !important;
  box-shadow: inset 0 3px 10px rgba(0,0,0,.24), 0 5px 15px rgba(0,0,0,.16) !important;
}

/* ---------- TOP COMMAND BAR ---------- */
.headbar-container { display:flex; justify-content:center; width:100%; margin: 0 auto 25px; }
.headbar-card {
  position: relative; overflow:hidden;
  min-width: min(760px, 95%);
  padding: 17px 32px;
  text-align:center;
  border-radius: 23px;
  border:1px solid rgba(201,255,220,.22);
  background: linear-gradient(135deg, rgba(22,68,40,.72), rgba(5,24,14,.70));
  backdrop-filter: blur(24px) saturate(145%);
  -webkit-backdrop-filter: blur(24px) saturate(145%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.14), 0 12px 0 rgba(1,11,6,.36), 0 24px 45px rgba(0,0,0,.30);
}
.headbar-card::before {
  content:""; position:absolute; left:8%; right:8%; top:5px; height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.48),transparent);
}
.headbar-title {
  display:flex; align-items:center; justify-content:center; gap:10px;
  font: 800 20px/1 'Space Grotesk', sans-serif !important;
  letter-spacing:.16em; color:#f7fff9 !important;
}
.headbar-subtitle { margin-top:8px; font-size:9px; font-weight:700; letter-spacing:.22em; color:#9bd8af !important; text-transform:uppercase; }
.title-mark {
  width:34px; height:34px; display:grid; place-items:center; border-radius:11px;
  background:linear-gradient(145deg,#a1ffc2,#32d875 48%,#0c6638);
  color:#03200f !important;
  border:1px solid rgba(235,255,242,.58);
  box-shadow: inset 0 2px 0 rgba(255,255,255,.48), 0 6px 0 rgba(2,25,13,.52), 0 13px 22px rgba(44,214,110,.18);
}
.title-mark span { color:#03200f !important; font:900 10px/1 'Space Grotesk',sans-serif; }

/* ---------- UNIVERSAL 3D GLASS BUTTONS ---------- */
button, .stDownloadButton > button, .stFormSubmitButton > button {
  position:relative; overflow:hidden;
  background: linear-gradient(145deg, rgba(35,103,63,.66), rgba(6,30,17,.82)) !important;
  color:#f7fff9 !important;
  border-radius:17px !important;
  border:1px solid rgba(192,255,214,.22) !important;
  font-weight:800;
  min-height:46px;
  box-shadow: inset 0 2px 0 rgba(255,255,255,.14), 0 5px 0 rgba(0,11,6,.58), 0 12px 24px rgba(0,0,0,.22);
  backdrop-filter:blur(16px) saturate(145%);
  -webkit-backdrop-filter:blur(16px) saturate(145%);
  transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease !important;
}
button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  transform:translateY(-3px) scale(1.008);
  border-color:rgba(151,255,187,.62) !important;
  box-shadow:inset 0 2px 0 rgba(255,255,255,.20), 0 8px 0 rgba(0,11,6,.50), 0 18px 31px rgba(47,210,110,.18) !important;
}
button:active, .stDownloadButton > button:active, .stFormSubmitButton > button:active { transform:translateY(2px) scale(.996); box-shadow:inset 0 4px 9px rgba(0,0,0,.18), 0 2px 0 rgba(0,11,6,.7) !important; }

/* ---------- INPUTS / FORMS ---------- */
div[data-baseweb="input"], div[data-baseweb="base-input"], input, textarea, select {
  background:rgba(9,39,23,.78) !important;
  border:1px solid rgba(151,255,187,.25) !important;
  border-radius:14px !important;
  color:#ffffff !important;
  -webkit-text-fill-color:#ffffff !important;
  font-size:15px !important;
  min-height:46px !important;
  box-shadow:inset 0 2px 8px rgba(0,0,0,.18), 0 4px 12px rgba(0,0,0,.10) !important;
}
input::placeholder, textarea::placeholder { color:#91caa3 !important; -webkit-text-fill-color:#91caa3 !important; opacity:.78; }
div[data-baseweb="input"]:focus-within, input:focus, textarea:focus { border-color:#65f59a !important; box-shadow:0 0 0 2px rgba(101,245,154,.10), 0 0 20px rgba(101,245,154,.18), inset 0 2px 8px rgba(0,0,0,.18) !important; }
input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance:none !important; margin:0 !important; }
input[type=number] { -moz-appearance:textfield !important; }
div[data-testid="stNumberInput"] button { display:none !important; }

/* ---------- DATA CARDS / METRICS ---------- */
[data-testid="stMetric"] {
  position:relative; overflow:hidden;
  background:linear-gradient(145deg, rgba(16,57,33,.78), rgba(5,25,14,.72));
  border-radius:22px; padding:17px 20px;
  border:1px solid rgba(157,255,190,.20);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.10), 0 8px 0 rgba(0,10,5,.32), 0 18px 28px rgba(0,0,0,.24);
}
[data-testid="stMetric"] label { color:#9bd8af !important; font-weight:700; letter-spacing:.05em; }
[data-testid="stMetric"] div[data-testid="stMetricValue"] { color:#ffffff !important; font-weight:800; font-family:'Space Grotesk',sans-serif; }

/* Existing planner cards get a premium lift without changing their content. */
.cal-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:20px; margin-top:16px; }
.cal-card {
  background:linear-gradient(145deg,rgba(16,54,32,.76),rgba(5,25,14,.74));
  border:1px solid rgba(151,255,187,.20); border-radius:22px; padding:19px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.08), 0 8px 0 rgba(0,10,5,.30), 0 20px 34px rgba(0,0,0,.25);
  transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
}
.cal-card:hover { transform:translateY(-5px); border-color:rgba(151,255,187,.42); box-shadow:inset 0 1px 0 rgba(255,255,255,.12),0 10px 0 rgba(0,10,5,.26),0 28px 45px rgba(29,205,100,.15); }
.cal-date-badge { background:rgba(74,222,128,.12); color:#65f59a; border:1px solid rgba(74,222,128,.32); padding:5px 12px; border-radius:999px; font-size:11px; font-weight:800; width:fit-content; }
.cal-task-title { color:#fff; font-size:16px; font-weight:800; margin:2px 0; }
.cal-phase { color:#a7dbb7; font-size:12px; font-weight:600; }
.cal-status-tag { font-size:10px; font-weight:800; padding:5px 10px; border-radius:999px; width:fit-content; text-transform:uppercase; }
.badge-notstarted { background:rgba(255,255,255,.08); color:#cbd5e1; }
.badge-inprogress { background:rgba(245,158,11,.14); color:#fbbf24; border:1px solid rgba(245,158,11,.34); }
.badge-completed { background:rgba(34,197,94,.14); color:#65f59a; border:1px solid rgba(34,197,94,.34); }
.card-photos { display:flex; gap:7px; margin-top:6px; flex-wrap:wrap; }
.card-photo-thumb { width:50px; height:50px; border-radius:10px; object-fit:cover; border:1px solid rgba(151,255,187,.34); box-shadow:0 5px 12px rgba(0,0,0,.22); }
.pos-role-box { background:linear-gradient(145deg,rgba(18,66,37,.74),rgba(5,26,15,.72)); border:1px solid rgba(101,245,154,.38); border-radius:18px; padding:13px; text-align:center; color:#fff; font-weight:800; margin-bottom:13px; box-shadow:inset 0 1px 0 rgba(255,255,255,.10),0 7px 0 rgba(0,10,5,.3),0 15px 25px rgba(0,0,0,.20); }

/* Mobile remains usable; only presentation changes. */
@media (max-width:768px) {
  .block-container { padding:16px 12px 22px !important; border-radius:22px; }
  .headbar-card { min-width:0; width:100%; padding:15px 16px; }
  .headbar-title { font-size:16px !important; letter-spacing:.10em; }
  .headbar-subtitle { font-size:7px; letter-spacing:.15em; }
  h1,h2,h3 { font-size:18px !important; }
  button { width:100% !important; margin-bottom:7px !important; }
  .stColumns { flex-direction:column !important; }
}

/* ================================================================
   AILYHOUSEPROJECT — SIGNATURE UI
   Presentation layer only. Existing business logic/navigation stays intact.
   ================================================================ */
:root {
  --v10-green: #72ffad;
  --v10-green2: #22d66f;
  --v10-cyan: #8affea;
  --v10-panel: rgba(4, 20, 12, .78);
  --v10-line: rgba(174, 255, 211, .25);
}

/* Keep the original background; intensify only the glass atmosphere. */
.stApp::after {
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  z-index:0;
  opacity:.22;
  background-image:
    linear-gradient(rgba(126,255,172,.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(126,255,172,.045) 1px, transparent 1px);
  background-size:44px 44px;
  mask-image:linear-gradient(to bottom, rgba(0,0,0,.8), transparent 92%);
  animation:v10Grid 22s linear infinite;
}
@keyframes v10Grid { from { transform:translate3d(0,0,0); } to { transform:translate3d(44px,44px,0); } }

.block-container {
  background:
    radial-gradient(circle at 12% 0%, rgba(113,255,169,.10), transparent 24%),
    radial-gradient(circle at 95% 20%, rgba(101,255,219,.06), transparent 22%),
    linear-gradient(145deg, rgba(7,29,17,.82), rgba(2,15,9,.72)) !important;
  border:1px solid rgba(186,255,214,.22);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.09),
    inset 0 -1px 0 rgba(0,0,0,.35),
    0 1px 0 rgba(150,255,188,.10),
    0 34px 100px rgba(0,0,0,.58),
    0 0 70px rgba(54,220,119,.05);
}

/* Sidebar = floating command deck */
section[data-testid="stSidebar"] {
  position:relative;
  background:
    radial-gradient(circle at 10% 0%, rgba(103,255,170,.15), transparent 22%),
    radial-gradient(circle at 100% 55%, rgba(52,220,137,.07), transparent 28%),
    linear-gradient(180deg, rgba(3,25,14,.975), rgba(1,12,7,.99)) !important;
  border-right:1px solid rgba(183,255,212,.24);
  box-shadow:20px 0 70px rgba(0,0,0,.48), inset -1px 0 0 rgba(255,255,255,.035);
}
section[data-testid="stSidebar"]::before {
  content:"";
  position:absolute;
  left:10px; right:10px; top:7px;
  height:2px;
  border-radius:999px;
  background:linear-gradient(90deg, transparent, rgba(114,255,173,.75), rgba(138,255,234,.32), transparent);
  filter:blur(.3px);
  animation:v10Pulse 3.4s ease-in-out infinite;
  pointer-events:none;
}
@keyframes v10Pulse { 0%,100%{opacity:.35} 50%{opacity:1} }

/* Sidebar brand becomes a floating hardware module. */
.sidebar-brand {
  min-height:86px;
  padding:14px 13px;
  border-radius:25px;
  background:
    linear-gradient(145deg, rgba(41,113,68,.46), rgba(3,21,12,.80)),
    linear-gradient(110deg, rgba(255,255,255,.05), transparent 42%);
  border:1px solid rgba(197,255,219,.32);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.20),
    inset 0 -1px 0 rgba(0,0,0,.5),
    0 8px 0 rgba(0,8,4,.75),
    0 20px 38px rgba(0,0,0,.38),
    0 0 35px rgba(68,240,127,.07);
  transform:perspective(1100px) rotateX(1deg);
}
.sidebar-brand::before {
  width:220px; height:220px; right:-120px; top:-150px;
  background:radial-gradient(circle, rgba(106,255,169,.23), transparent 62%);
  animation:v10Orb 7s ease-in-out infinite;
}
@keyframes v10Orb { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-15px,12px)} }
.brand-icon {
  width:51px; height:51px; flex-basis:51px;
  border-radius:16px;
  background:
    linear-gradient(145deg, #d7ffe4 0%, #72ffad 25%, #24d36e 58%, #07562f 100%);
  box-shadow:
    inset 0 2px 0 rgba(255,255,255,.72),
    inset 0 -5px 8px rgba(0,0,0,.17),
    0 7px 0 #052d18,
    0 14px 28px rgba(32,221,107,.25),
    0 0 26px rgba(114,255,173,.12);
  transform:perspective(600px) rotateX(8deg) rotateY(-8deg) translateZ(0);
}
.brand-icon span { font-size:15px !important; }
.brand-icon i {
  position:absolute;
  width:8px; height:8px;
  right:5px; top:5px;
  border-radius:50%;
  background:#effff4;
  box-shadow:0 0 0 3px rgba(4,66,34,.35), 0 0 12px #72ffad;
  animation:v10Live 1.8s ease-in-out infinite;
}
@keyframes v10Live { 50%{opacity:.35; transform:scale(.75)} }
.brand-kicker {
  color:#75ffae !important;
  font:800 7px/1 'Space Grotesk',sans-serif;
  letter-spacing:.28em;
  margin-bottom:4px;
}
.brand-copy { padding-right:30px; }
.sidebar-brand h3 { font-size:16px !important; letter-spacing:.10em; }
.sidebar-brand p { font-size:8px; letter-spacing:.13em; }
.brand-live {
  position:absolute; right:11px; top:11px;
  font:800 7px/1 'Space Grotesk',sans-serif;
  letter-spacing:.16em;
  color:#baffd2 !important;
  padding:5px 7px;
  border:1px solid rgba(114,255,173,.23);
  border-radius:999px;
  background:rgba(99,255,163,.06);
}
.brand-live span { display:inline-block; width:5px; height:5px; border-radius:50%; background:#72ffad; margin-right:4px; box-shadow:0 0 8px #72ffad; }

/* Section headers get a HUD-like treatment. */
section[data-testid="stSidebar"] .stSubheader {
  position:relative;
  padding:8px 9px 8px 12px !important;
  margin:13px 0 7px !important;
  border-left:2px solid rgba(114,255,173,.75);
  border-radius:0 10px 10px 0;
  background:linear-gradient(90deg, rgba(114,255,173,.09), transparent 80%);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
  letter-spacing:.13em;
}
section[data-testid="stSidebar"] .stSubheader::after {
  content:"// ACTIVE MODULE";
  float:right;
  font:700 6px/1 'Space Grotesk',sans-serif;
  letter-spacing:.16em;
  color:rgba(151,255,191,.38) !important;
  margin-top:3px;
}

/* Buttons: multilayer glass, extrusion, specular sweep, magnetic hover. */
section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] .stDownloadButton > button {
  min-height:50px;
  border-radius:18px !important;
  margin:7px 0;
  border:1px solid rgba(202,255,221,.24) !important;
  background:
    linear-gradient(115deg, transparent 0%, transparent 35%, rgba(255,255,255,.13) 47%, rgba(255,255,255,.03) 54%, transparent 68%),
    linear-gradient(145deg, rgba(35,103,62,.72), rgba(4,25,14,.88)) !important;
  background-size:250% 100%,100% 100%;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.18),
    inset 0 -1px 0 rgba(0,0,0,.5),
    0 7px 0 rgba(0,8,4,.82),
    0 15px 26px rgba(0,0,0,.28);
  transition:all .20s cubic-bezier(.2,.85,.25,1) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover,
section[data-testid="stSidebar"] .stDownloadButton > button:hover {
  transform:translateY(-6px) perspective(1000px) rotateX(2deg) scale(1.015);
  background-position:-65% 0,0 0;
  border-color:rgba(132,255,177,.76) !important;
  box-shadow:
    inset 0 2px 0 rgba(255,255,255,.25),
    0 10px 0 rgba(0,8,4,.70),
    0 25px 42px rgba(39,225,113,.20),
    0 0 26px rgba(114,255,173,.10);
}
section[data-testid="stSidebar"] .stButton > button:active,
section[data-testid="stSidebar"] .stDownloadButton > button:active {
  transform:translateY(5px) scale(.988) !important;
  box-shadow:inset 0 6px 14px rgba(0,0,0,.28),0 2px 0 rgba(0,8,4,.9) !important;
}

/* Main buttons also get a stronger physical feel. */
.stApp button, .stApp .stDownloadButton > button, .stApp .stFormSubmitButton > button {
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.17),
    inset 0 -1px 0 rgba(0,0,0,.45),
    0 6px 0 rgba(0,10,5,.60),
    0 14px 26px rgba(0,0,0,.22);
}
.stApp button:hover, .stApp .stDownloadButton > button:hover, .stApp .stFormSubmitButton > button:hover {
  transform:translateY(-4px) scale(1.012) !important;
  box-shadow:
    inset 0 2px 0 rgba(255,255,255,.22),
    0 9px 0 rgba(0,10,5,.50),
    0 22px 34px rgba(45,216,110,.18),
    0 0 20px rgba(114,255,173,.08) !important;
}

/* Headbar = premium command display. */
.headbar-card {
  min-width:min(880px,95%);
  padding:19px 34px;
  border-radius:27px;
  background:
    radial-gradient(circle at 18% 0%, rgba(116,255,173,.13), transparent 28%),
    linear-gradient(145deg, rgba(20,70,41,.78), rgba(3,20,11,.82));
  border:1px solid rgba(205,255,222,.27);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.17),
    inset 0 -1px 0 rgba(0,0,0,.45),
    0 8px 0 rgba(0,9,4,.60),
    0 25px 55px rgba(0,0,0,.32),
    0 0 35px rgba(74,229,124,.06);
}
.headbar-card::after {
  content:"SYSTEM ONLINE   •   SECURE LOCAL STATE   •   PROCORE ENGINE";
  display:block;
  margin-top:11px;
  color:rgba(177,255,205,.34);
  font:700 6px/1 'Space Grotesk',sans-serif;
  letter-spacing:.25em;
}
.title-mark {
  width:38px; height:38px; border-radius:13px;
  box-shadow:inset 0 2px 0 rgba(255,255,255,.60),0 7px 0 #062d18,0 15px 28px rgba(42,220,108,.23),0 0 20px rgba(114,255,173,.10);
}

/* Cards, expanders, alerts, tables and select controls. */
[data-testid="stMetric"], .cal-card, .pos-role-box {
  border-color:rgba(177,255,207,.24) !important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.11),0 8px 0 rgba(0,10,5,.34),0 22px 38px rgba(0,0,0,.26) !important;
}
[data-testid="stMetric"]:hover { transform:translateY(-4px); transition:transform .18s ease; border-color:rgba(114,255,173,.42) !important; }
[data-testid="stExpander"] {
  border:1px solid rgba(165,255,197,.17) !important;
  border-radius:18px !important;
  background:rgba(5,25,14,.48) !important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 8px 25px rgba(0,0,0,.15);
}
[data-testid="stAlert"] {
  border-radius:16px !important;
  border:1px solid rgba(157,255,190,.20) !important;
  box-shadow:0 10px 25px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.07);
}
[data-baseweb="select"] > div {
  background:rgba(5,31,17,.82) !important;
  border-color:rgba(151,255,187,.24) !important;
  border-radius:14px !important;
  box-shadow:inset 0 2px 8px rgba(0,0,0,.20),0 5px 13px rgba(0,0,0,.10) !important;
}

/* Section dividers become luminous rails. */
.stApp hr {
  border:0 !important;
  height:1px !important;
  background:linear-gradient(90deg,transparent,rgba(114,255,173,.35),rgba(138,255,234,.16),transparent) !important;
  box-shadow:0 0 12px rgba(114,255,173,.06);
}

/* Make ordinary headings feel like an enterprise dashboard. */
.stApp h1, .stApp h2, .stApp h3 {
  font-family:'Space Grotesk',sans-serif !important;
  letter-spacing:.03em;
}
.stApp h1 { text-shadow:0 4px 25px rgba(73,220,119,.10); }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.001ms !important; animation-iteration-count:1 !important; transition-duration:.001ms !important; }
}

/* ================================================================
   AILYHOUSEPROJECT — SIGNATURE UI LAYER
   UI/presentation only. Original background + system logic preserved.
   ================================================================ */
:root {
  --ah-lime:#8dffb7;
  --ah-green:#35d978;
  --ah-deep:#04170c;
  --ah-glass:rgba(7,28,16,.72);
  --ah-border:rgba(185,255,211,.20);
  --ah-text:#f3fff7;
  --ah-muted:#93c9a6;
}

/* Keep the original background untouched; add only a very subtle readability veil. */
.stApp::before {
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  z-index:0;
  background:radial-gradient(circle at 50% -10%, rgba(120,255,170,.08), transparent 34%);
}

/* Clean Streamlit chrome without changing application behavior. */
#MainMenu { visibility:hidden; }
footer { visibility:hidden; }
header[data-testid="stHeader"] { background:transparent !important; }

/* Main workspace: cleaner glass sheet. */
.block-container {
  position:relative;
  z-index:1;
  max-width:1500px !important;
  background:linear-gradient(145deg,rgba(8,30,18,.78),rgba(3,17,10,.68)) !important;
  border:1px solid rgba(191,255,215,.18) !important;
  border-radius:30px !important;
  box-shadow:0 30px 90px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.08) !important;
}

/* Signature top identity bar. */
.headbar-card {
  min-width:min(900px,96%) !important;
  padding:19px 34px !important;
  border-radius:26px !important;
  background:
    linear-gradient(135deg,rgba(26,82,48,.74),rgba(3,20,11,.76)),
    radial-gradient(circle at 12% 0%,rgba(255,255,255,.10),transparent 34%) !important;
  border:1px solid rgba(193,255,216,.27) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.20),
    0 7px 0 rgba(0,8,4,.60),
    0 24px 50px rgba(0,0,0,.34),
    0 0 34px rgba(71,232,123,.07) !important;
}
.headbar-title { letter-spacing:.18em !important; font-size:22px !important; }
.headbar-subtitle { color:#a8e6ba !important; letter-spacing:.20em !important; }
.title-mark {
  width:42px !important; height:42px !important; border-radius:14px !important;
  background:linear-gradient(145deg,#e2ffea 0%,#82ffb0 30%,#27d66f 62%,#07522e 100%) !important;
  box-shadow:inset 0 2px 0 rgba(255,255,255,.75),0 7px 0 #052b17,0 15px 28px rgba(38,216,108,.22) !important;
}
.title-mark span { font-size:13px !important; }

/* Sidebar: premium command panel, not a flat list. */
section[data-testid="stSidebar"] {
  border-right:1px solid rgba(180,255,205,.22) !important;
  box-shadow:18px 0 60px rgba(0,0,0,.42),inset -1px 0 rgba(255,255,255,.035) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding:16px 12px 28px !important; }
section[data-testid="stSidebar"] .stSubheader,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  position:relative;
  margin-top:17px !important;
  padding:9px 10px 8px !important;
  border-radius:12px;
  background:linear-gradient(90deg,rgba(101,255,158,.08),transparent 80%);
  border-left:2px solid rgba(117,255,170,.65);
  font-size:10px !important;
  letter-spacing:.16em !important;
  color:#dfffea !important;
}

.sidebar-brand {
  min-height:94px !important;
  padding:15px !important;
  border-radius:26px !important;
  background:
    linear-gradient(145deg,rgba(38,110,66,.48),rgba(2,19,10,.84)),
    radial-gradient(circle at 10% 0%,rgba(255,255,255,.12),transparent 32%) !important;
  border:1px solid rgba(203,255,220,.30) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.22),
    inset 0 -1px 0 rgba(0,0,0,.5),
    0 8px 0 rgba(0,7,3,.78),
    0 22px 42px rgba(0,0,0,.36),
    0 0 28px rgba(91,245,137,.08) !important;
}
.sidebar-brand::after { content:"AILYHOUSEPROJECT" !important; letter-spacing:.18em !important; }
.brand-icon {
  width:54px !important; height:54px !important; flex-basis:54px !important;
  border-radius:17px !important;
  background:linear-gradient(145deg,#effff3,#8bffb5 28%,#31d977 62%,#07532f) !important;
  box-shadow:inset 0 2px 0 rgba(255,255,255,.78),0 7px 0 #042a16,0 16px 30px rgba(44,220,111,.24) !important;
}
.brand-icon span { font-size:16px !important; letter-spacing:-.10em !important; }
.sidebar-brand h3 { font-size:15px !important; letter-spacing:.11em !important; }
.sidebar-brand p { font-size:8px !important; letter-spacing:.12em !important; }
.brand-kicker { color:#7dffad !important; letter-spacing:.24em !important; }

/* More physical button geometry. */
section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] .stDownloadButton > button,
button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius:16px !important;
  min-height:48px !important;
  border:1px solid rgba(200,255,218,.22) !important;
  background:
    linear-gradient(180deg,rgba(255,255,255,.07),transparent 34%),
    linear-gradient(145deg,rgba(31,102,59,.72),rgba(3,23,12,.88)) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.18),
    inset 0 -1px 0 rgba(0,0,0,.42),
    0 5px 0 rgba(0,8,4,.72),
    0 12px 22px rgba(0,0,0,.24) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover,
section[data-testid="stSidebar"] .stDownloadButton > button:hover,
button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  transform:translateY(-4px) perspective(900px) rotateX(1deg) !important;
  border-color:rgba(139,255,181,.68) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.28),
    0 9px 0 rgba(0,8,4,.58),
    0 22px 34px rgba(46,219,111,.18),
    0 0 22px rgba(115,255,170,.10) !important;
}
section[data-testid="stSidebar"] .stButton > button:active,
button:active, .stDownloadButton > button:active, .stFormSubmitButton > button:active {
  transform:translateY(4px) scale(.992) !important;
  box-shadow:inset 0 5px 12px rgba(0,0,0,.30),0 1px 0 rgba(0,8,4,.82) !important;
}

/* Cleaner forms: labels become small professional field captions. */
label, [data-testid="stWidgetLabel"] p {
  color:#b9e8c8 !important;
  font-weight:700 !important;
  letter-spacing:.04em !important;
}
div[data-baseweb="input"], div[data-baseweb="select"], textarea {
  border-radius:15px !important;
}

/* Cards / expanders get consistent visual language. */
[data-testid="stExpander"] {
  border:1px solid rgba(178,255,204,.17) !important;
  border-radius:18px !important;
  background:rgba(5,25,14,.48) !important;
  box-shadow:0 10px 24px rgba(0,0,0,.16) !important;
}
[data-testid="stExpander"] summary:hover { background:rgba(110,255,164,.05) !important; }
[data-testid="stAlert"] {
  border-radius:16px !important;
  border:1px solid rgba(180,255,207,.18) !important;
  backdrop-filter:blur(14px) !important;
}
.stCaption, [data-testid="stCaptionContainer"] { color:#8fc7a2 !important; }

/* Tables / dataframe surfaces. */
[data-testid="stDataFrame"] {
  border-radius:18px !important;
  overflow:hidden !important;
  border:1px solid rgba(178,255,204,.18) !important;
  box-shadow:0 14px 30px rgba(0,0,0,.20) !important;
}

/* Section headings become cleaner and less bulky. */
.stApp h1, .stApp h2, .stApp h3 {
  letter-spacing:.035em;
}
.stApp h2::after, .stApp h3::after {
  content:"";
  display:block;
  width:48px;
  height:2px;
  margin-top:7px;
  border-radius:99px;
  background:linear-gradient(90deg,#75ffad,transparent);
  opacity:.7;
}

/* Scrollbar refinement. */
::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-track { background:rgba(0,0,0,.18); }
::-webkit-scrollbar-thumb { background:rgba(112,255,169,.24); border-radius:99px; }
::-webkit-scrollbar-thumb:hover { background:rgba(112,255,169,.44); }

@media (max-width:768px) {
  .headbar-title { font-size:16px !important; letter-spacing:.10em !important; }
  .headbar-subtitle { font-size:7px !important; }
  .sidebar-brand { min-height:84px !important; }
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="headbar-container">
<div class="headbar-card">
<div class="headbar-title"><span class="title-mark"><span>AH</span></span><span>AILYHOUSEPROJECT</span></div>
<div class="headbar-subtitle">Construction  •  Finance  •  Payroll  •  Project Control  •  Command UI</div>
</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="brand-icon"><span>AH</span><i></i></div>
      <div class="brand-copy"><div class="brand-kicker">PROJECT COMMAND</div><h3>AILYHOUSEPROJECT</h3><p>CONSTRUCTION • FINANCE • PAYROLL</p></div>
      <div class="brand-live"><span></span>LIVE</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"{datetime.now().strftime('%I:%M%p | %b %d')}")
    st.divider()
    
    st.subheader("◈ EXECUTIVE OVERVIEW")
    if st.button("📈 Financial Dashboard", use_container_width=True):
        set_view("home")
        
    budget_input = st.number_input("Set Balance Account Budget", min_value=0.0, key="budget_input_sidebar", value=None, placeholder="Enter budget...")
    if st.button("◆  COMMIT BUDGET", use_container_width=True):
        if budget_input is not None:
            st.session_state.budget = float(budget_input)
            persist_state()
            st.success("Budget applied!")
            st.rerun()
        else:
            st.warning("Please enter a budget amount.")
            
    if st.button("↻  RESET WORKSPACE", use_container_width=True):
        clear_all()
        set_view("home")
        
    st.markdown("---")
    st.subheader("◇ PROJECT CONTROL")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("＋  NEW ENTRY", use_container_width=True):
            set_view("planner_input")
    with col_p2:
        if st.button("▦  SCHEDULE LOG", use_container_width=True):
            set_view("planner_output")
            
    st.markdown("---")
    st.subheader("◇ FINANCIAL OPERATIONS")
    if st.button("＋  MATERIAL POSTING", use_container_width=True):
        set_view("material")
    if st.button("＋  EXPENSE POSTING", use_container_width=True):
        set_view("expense")
    if st.button("＋  EXCESS DEPOSIT", use_container_width=True):
        set_view("excess")
    if st.button("▤  ACCOUNT LEDGER", use_container_width=True):
        set_view("ledger")
    if st.button("⇩  FINANCIAL EXPORT", use_container_width=True):
        set_view("export")
        
    st.markdown("---")
    st.subheader("◇ PAYROLL OPERATIONS")
    if st.button("＋  LABOR ACCOUNT", use_container_width=True):
        set_view("add_labor")
    if st.button("＋  PAYROLL EXPENSE", use_container_width=True):
        set_view("add_payroll_expense")
    if st.button("◌  ACCOUNT REMAINDER", use_container_width=True):
        set_view("payroll_remaining")
    if st.button("▦  LABOR ACCOUNTS", use_container_width=True):
        set_view("payroll_ledger")
    if st.button("⇩  PAYROLL EXPORT", use_container_width=True):
        set_view("payroll_export")
    if st.button("▣  RECEIPT ARCHIVE", use_container_width=True):
        set_view("receipt_archive")

view = st.session_state.view

if view == "home":
    st.subheader("📊 QUICK STATS")
    col1, col2, col3 = st.columns(3)
    col1.metric("BUDGET", f"PHP {st.session_state.budget:,.2f}")
    col2.metric("USED", f"PHP {get_total():,.2f}")
    col3.metric("BALANCE", f"PHP {get_balance():,.2f}")
    st.markdown("---")
    st.subheader("🧱 MATERIALS LEDGER PREVIEW")
    if not st.session_state.records:
        st.info("No materials yet.")
    else:
        materials = [r for r in st.session_state.records if r["type"] == "material"]
        for r in materials[-5:]:
            st.markdown(f"""
            ---
            **{r['name']}** • PHP {float(r['amount']):,.2f}  
            👤 {r['sender']}  
            📅 {r['date']}
            """)

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
        st.markdown("---")
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
                        
    st.markdown("---")
    custom_receipt_title = st.text_input("Receipt Title", value="Construction Schedule Receipt", placeholder="Enter a custom title...")
    html_report = generate_planner_html(sorted_tasks, custom_title=custom_receipt_title)
    st.markdown("### 🖼️ SEE PHOTO & DOWNLOAD SCHEDULE RECEIPT")
    st.components.v1.html(html_report, height=650, scrolling=True)
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
    st.components.v1.html(html, height=650, scrolling=True)
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
    st.caption("Select the worker role, then enter the worked days normally.")
    
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
        days = st.number_input("Worked Days", min_value=0.1, value=1.0, step=0.1, format="%.1f", help="Enter the number of days worked. Decimal values use the existing point schedule.")
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
                
    st.markdown("---")
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
    st.components.v1.html(html, height=650, scrolling=True)
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
                st.components.v1.html(report_html, height=400, scrolling=True)
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
    st.info("Welcome to AILYHOUSEPROJECT. Use the sidebar to navigate.")