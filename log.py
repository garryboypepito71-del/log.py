import os
import time
import base64
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

APP_VERSION = "AILYHOUSEPROJECT — Ailyn Project Management System"
RECEIVER_EMAIL = "garryboypepito2004@gmail.com"
RECEIVER_AILYN = "ailyn_peps0678@yahoo.com"
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
</style>
</head>
<body>
<div class="save-btn-container">
<button class="save-img-btn" onclick="saveAsImage()">SEE PHOTO & DOWNLOAD IMAGE (Phone & Laptop)</button>
</div>
<div class="receipt-container" id="receiptContent">
<div class="header">
<div class="company-info">
<h1>AILYNHOUSEPROJECT</h1>
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
<p>AILYNHOUSEPROJECT MANAGEMENT</p>
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

/* top command deck */
.headbar-container{display:flex;justify-content:center;margin:0 auto 28px}
.headbar-card{
 width:100%;position:relative;overflow:hidden;padding:18px 22px 17px;
 display:flex;align-items:center;justify-content:space-between;gap:20px;
 border-radius:26px;background:linear-gradient(105deg,rgba(10,55,32,.90),rgba(4,25,16,.78));
 border:1px solid rgba(166,255,197,.25);
 box-shadow:0 18px 42px rgba(0,0,0,.38),inset 0 1px 0 rgba(255,255,255,.15);
}
.headbar-card:before{content:"";position:absolute;inset:0;background:linear-gradient(110deg,transparent 0%,rgba(255,255,255,.08) 42%,transparent 54%);transform:translateX(-120%);animation:scan 8s linear infinite}
.headbar-title{position:relative;display:flex;align-items:center;gap:13px;color:#fff!important;font-family:'Outfit';font-size:20px!important;font-weight:900;letter-spacing:.055em}
.headbar-subtitle{position:relative;color:#aeeec3;font-size:10px;letter-spacing:.16em;text-transform:uppercase;font-weight:800;text-align:right}
.logo-mark,.brand-icon{
 display:grid;place-items:center;font-family:'Outfit';font-weight:900;
 color:#062613!important;background:linear-gradient(145deg,#d6ffe5 0%,#65efa0 45%,#20a963 100%);
 border:1px solid rgba(255,255,255,.65);
 box-shadow:0 5px 0 #0b4a2b,0 13px 28px rgba(58,220,125,.30),inset 0 2px 0 rgba(255,255,255,.8);
}
.logo-mark{width:40px;height:40px;border-radius:13px;font-size:16px}

/* sidebar: floating command rail */
section[data-testid="stSidebar"]{
 background:linear-gradient(180deg,rgba(2,14,9,.97),rgba(4,24,14,.96))!important;
 border-right:1px solid rgba(170,255,198,.17)!important;
 box-shadow:18px 0 60px rgba(0,0,0,.48)!important;
}
section[data-testid="stSidebar"]>div{padding:16px 13px 24px!important}
section[data-testid="stSidebar"] *{color:#edfff3!important}
.sidebar-brand{
 position:relative;overflow:hidden;padding:15px;border-radius:24px;margin-bottom:12px;
 background:linear-gradient(145deg,rgba(24,89,52,.92),rgba(5,30,18,.82));
 border:1px solid rgba(163,255,194,.25);
 box-shadow:0 16px 34px rgba(0,0,0,.40),inset 0 1px 0 rgba(255,255,255,.16);
}
.sidebar-brand:after{content:"";position:absolute;inset:-80% 35%;background:rgba(255,255,255,.09);transform:rotate(25deg);animation:scan 7s linear infinite}
.brand-row{position:relative;z-index:1;display:flex;align-items:center;gap:12px}
.brand-icon{width:48px;height:48px;border-radius:16px;font-size:18px}
.brand-title{font-family:'Outfit';font-size:14px;font-weight:900;letter-spacing:.075em}
.brand-sub{font-size:9px;color:#a8eac0!important;letter-spacing:.13em;text-transform:uppercase;margin-top:4px}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3{
 font-family:'Outfit';font-size:9px!important;letter-spacing:.20em;text-transform:uppercase;
 color:#76e9a3!important;margin:18px 5px 7px!important;
}
section[data-testid="stSidebar"] hr{border-color:rgba(170,255,198,.10)!important;margin:10px 4px!important}

/* every navigation button becomes a floating glass tile */
section[data-testid="stSidebar"] button{
 min-height:48px!important;margin:5px 0!important;padding:0 14px!important;
 border-radius:17px!important;text-align:left!important;
 background:linear-gradient(145deg,rgba(22,78,47,.76),rgba(5,28,17,.92))!important;
 border:1px solid rgba(173,255,201,.16)!important;
 box-shadow:
   0 5px 0 rgba(1,12,7,.88),
   0 11px 22px rgba(0,0,0,.30),
   inset 0 1px 0 rgba(255,255,255,.12)!important;
 transition:transform .18s cubic-bezier(.2,.8,.2,1),box-shadow .18s,border-color .18s,background .18s!important;
}
section[data-testid="stSidebar"] button:hover{
 transform:translate3d(5px,-3px,0)!important;
 background:linear-gradient(145deg,rgba(34,111,65,.94),rgba(7,45,25,.96))!important;
 border-color:rgba(114,247,176,.55)!important;
 box-shadow:0 8px 0 rgba(1,12,7,.92),0 18px 32px rgba(0,0,0,.40),0 0 25px rgba(70,230,132,.14),inset 0 1px 0 rgba(255,255,255,.20)!important;
}
section[data-testid="stSidebar"] button:active{transform:translate3d(2px,4px,0)!important;box-shadow:0 2px 0 rgba(1,12,7,.9),0 6px 12px rgba(0,0,0,.3)!important}
section[data-testid="stSidebar"] button p{font-family:'Manrope'!important;font-weight:800!important;font-size:12px!important;letter-spacing:.01em}

/* general controls */
button,.stDownloadButton>button,.stFormSubmitButton>button{
 position:relative!important;overflow:hidden!important;min-height:46px!important;
 border-radius:16px!important;color:#f5fff8!important;font-weight:800!important;
 background:linear-gradient(145deg,rgba(25,92,54,.88),rgba(5,33,19,.94))!important;
 border:1px solid rgba(173,255,201,.22)!important;
 box-shadow:0 6px 0 rgba(2,17,10,.78),0 13px 27px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.13)!important;
 transition:all .17s ease!important;
}
button:hover,.stDownloadButton>button:hover,.stFormSubmitButton>button:hover{
 transform:translateY(-3px)!important;border-color:rgba(114,247,176,.58)!important;
 box-shadow:0 9px 0 rgba(2,17,10,.78),0 20px 34px rgba(0,0,0,.35),0 0 25px rgba(114,247,176,.13),inset 0 1px 0 rgba(255,255,255,.2)!important;
}
button:active,.stDownloadButton>button:active,.stFormSubmitButton>button:active{transform:translateY(3px)!important;box-shadow:0 2px 0 rgba(2,17,10,.8),0 5px 10px rgba(0,0,0,.28)!important}

/* fields */
div[data-baseweb="input"],div[data-baseweb="base-input"],textarea,
div[data-baseweb="select"]>div{
 background:rgba(3,25,15,.78)!important;border:1px solid rgba(163,255,194,.18)!important;
 border-radius:15px!important;color:#fff!important;min-height:48px!important;
 box-shadow:inset 0 4px 15px rgba(0,0,0,.23),0 4px 12px rgba(0,0,0,.12)!important;
}
input,textarea{color:#fff!important;-webkit-text-fill-color:#fff!important}
input:focus,textarea:focus,div[data-baseweb="input"]:focus-within,div[data-baseweb="select"]>div:focus-within{
 border-color:#72f7b0!important;box-shadow:0 0 0 3px rgba(114,247,176,.08),0 0 24px rgba(114,247,176,.14),inset 0 4px 15px rgba(0,0,0,.2)!important;
}
label{font-weight:700!important;color:#c8e8d2!important}

/* metrics become executive tiles */
[data-testid="stMetric"]{
 position:relative;overflow:hidden;min-height:118px;padding:20px!important;
 background:linear-gradient(145deg,rgba(17,76,44,.78),rgba(4,28,17,.82))!important;
 border:1px solid rgba(173,255,201,.20);border-radius:24px;
 box-shadow:0 16px 34px rgba(0,0,0,.30),inset 0 1px 0 rgba(255,255,255,.13);
 transition:.2s ease;
}
[data-testid="stMetric"]:hover{transform:translateY(-5px);box-shadow:0 23px 44px rgba(0,0,0,.38),0 0 28px rgba(114,247,176,.11)}
[data-testid="stMetric"] label{font-size:10px!important;letter-spacing:.14em;text-transform:uppercase;color:#91d9ab!important}
[data-testid="stMetricValue"]{font-family:'Outfit';font-size:30px!important;font-weight:900!important;color:#fff!important}

/* planner / content cards */
.cal-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px;margin-top:18px}
.cal-card{
 background:linear-gradient(145deg,rgba(16,69,40,.80),rgba(4,27,16,.85));
 border:1px solid rgba(165,255,195,.18);border-radius:24px;padding:20px;
 box-shadow:0 14px 34px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.08);
 transition:.22s cubic-bezier(.2,.8,.2,1);
}
.cal-card:hover{transform:translateY(-7px) scale(1.012);border-color:rgba(114,247,176,.45);box-shadow:0 24px 50px rgba(0,0,0,.40),0 0 30px rgba(114,247,176,.11)}
.cal-date-badge{background:rgba(114,247,176,.10);color:#72f7b0;border:1px solid rgba(114,247,176,.28);padding:5px 11px;border-radius:999px;font-size:10px;font-weight:900}
.cal-task-title{color:#fff;font-family:'Outfit';font-size:17px;font-weight:800}.cal-phase{color:#a8dcb8;font-size:12px}
.cal-status-tag{font-size:9px;font-weight:900;padding:5px 10px;border-radius:999px;text-transform:uppercase}
.badge-notstarted{background:rgba(255,255,255,.07);color:#d1d5db}.badge-inprogress{background:rgba(245,158,11,.14);color:#fbbf24}.badge-completed{background:rgba(34,197,94,.14);color:#65f394}
.pos-role-box{background:linear-gradient(145deg,rgba(21,90,52,.82),rgba(4,29,17,.86));border:1px solid rgba(114,247,176,.35);border-radius:20px;padding:15px;text-align:center;box-shadow:0 13px 28px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.12)}
[data-testid="stExpander"]{background:rgba(5,29,17,.58)!important;border:1px solid rgba(163,255,194,.15)!important;border-radius:20px!important;box-shadow:0 10px 25px rgba(0,0,0,.18)!important}
.stAlert{border-radius:17px!important;background:rgba(8,42,24,.65)!important;border:1px solid rgba(163,255,194,.18)!important}

@keyframes scan{0%,55%{transform:translateX(-130%)}80%,100%{transform:translateX(180%)}}
@media(max-width:768px){
 .block-container{padding:18px 12px 24px!important;margin:8px!important;border-radius:24px}
 .headbar-card{display:block;text-align:center}.headbar-title{justify-content:center;font-size:16px!important}.headbar-subtitle{text-align:center;margin-top:7px}
 .cal-grid{grid-template-columns:1fr}
}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="headbar-container">
  <div class="headbar-card">
    <div class="headbar-title"><span class="logo-mark">AH</span> Ailyn Project Management System</div>
    <div class="headbar-subtitle">AILYNHOUSEPROJECT • PROJECT CONTROL CENTER</div>
  </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="brand-row">
        <div class="brand-icon">AH</div>
        <div>
          <div class="brand-title">AILYNHOUSEPROJECT</div>
          <div class="brand-sub">Ailyn Project Management System</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"● LIVE SYSTEM  •  {datetime.now().strftime('%I:%M %p  |  %b %d')}")
    st.divider()

    st.subheader("Executive Overview")
    if st.button("◉  Dashboard", use_container_width=True):
        set_view("home")
    budget_input = st.number_input("Set Account Budget", min_value=0.0, key="budget_input_sidebar", value=None, placeholder="Enter budget...")
    if st.button("◆  Apply Budget", use_container_width=True):
        if budget_input is not None:
            st.session_state.budget = float(budget_input)
            persist_state()
            st.success("Budget applied!")
            st.rerun()
        else:
            st.warning("Please enter a budget amount.")
    if st.button("↻  Reset System", use_container_width=True):
        clear_all()
        set_view("home")

    st.markdown("---")
    st.subheader("Project Control")
    if st.button("＋  New Work Entry", use_container_width=True):
        set_view("planner_input")
    if st.button("▦  Schedule & Progress", use_container_width=True):
        set_view("planner_output")

    st.markdown("---")
    st.subheader("Financial Operations")
    if st.button("＋  Material Entry", use_container_width=True):
        set_view("material")
    if st.button("＋  Expense Entry", use_container_width=True):
        set_view("expense")
    if st.button("＋  Excess Deposit", use_container_width=True):
        set_view("excess")
    if st.button("▤  Financial Ledger", use_container_width=True):
        set_view("ledger")
    if st.button("⇩  Financial Report", use_container_width=True):
        set_view("export")

    st.markdown("---")
    st.subheader("Payroll Operations")
    if st.button("＋  Labor Account", use_container_width=True):
        set_view("add_labor")
    if st.button("＋  Payroll Expense", use_container_width=True):
        set_view("add_payroll_expense")
    if st.button("◈  Account Remainder", use_container_width=True):
        set_view("payroll_remaining")
    if st.button("▤  Labor Accounts", use_container_width=True):
        set_view("payroll_ledger")
    if st.button("⇩  Payroll Report", use_container_width=True):
        set_view("payroll_export")
    if st.button("▣  Receipt Archive", use_container_width=True):
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
    st.info("Welcome to Ailyn Project Management System. Use the command sidebar to navigate.")