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
    "budget_entries",
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
AILYN_LOGO_DATA = "data:image/png;base64,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"
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
if "budget_entries" not in st.session_state:
    # Backward-compatible migration: preserve an existing single budget as the first entry.
    old_budget = float(st.session_state.get("budget", 0.0) or 0.0)
    st.session_state.budget_entries = [old_budget] if old_budget > 0 else []
    st.session_state.budget = sum(st.session_state.budget_entries)
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
    return float(sum(st.session_state.get("budget_entries", []) or [0.0])) + total_excess() - get_total()

def clear_all():
    st.session_state.records = []
    st.session_state.labor_records = []
    st.session_state.payroll_expenses = []
    st.session_state.planner_tasks = []
    st.session_state.budget = 0.0
    st.session_state.budget_entries = []
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


def update_material_record(index, name, price, qty, delivery, sender):
    """Edit a construction material/expense ledger record without creating a duplicate."""
    if index < 0 or index >= len(st.session_state.records):
        return False
    r = st.session_state.records[index]
    p = float(price or 0.0)
    q = int(qty or 0)
    d = float(delivery or 0.0)
    if not str(name).strip() or p <= 0 or q <= 0:
        return False
    r["name"] = str(name).strip().upper()
    r["price"] = p
    r["qty"] = q
    r["delivery"] = d
    r["sender"] = sender
    r["amount"] = (p * q) + d if r.get("type") == "material" else p
    persist_state()
    return True


def update_labor_record(index, name, role, days, ca):
    """Edit a labor ledger record and recalculate gross/net pay from the selected role and days."""
    if index < 0 or index >= len(st.session_state.labor_records):
        return False
    d = float(days or 0.0)
    c = float(ca or 0.0)
    if not str(name).strip() or d <= 0 or role not in FULL_DAY_RATES:
        return False
    gross_pay, full_pay, partial_pay = calculate_labor_pay(d, role)
    rate = FULL_DAY_RATES[role]
    r = st.session_state.labor_records[index]
    r.update({
        "name": str(name).strip().upper(),
        "role": role,
        "days": d,
        "rate": rate,
        "gross_pay": gross_pay,
        "ca": c,
        "net": gross_pay - c,
    })
    persist_state()
    return True


def update_payroll_expense(index, item, price):
    """Edit a payroll expense ledger record."""
    if index < 0 or index >= len(st.session_state.payroll_expenses):
        return False
    p = float(price or 0.0)
    if not str(item).strip() or p <= 0:
        return False
    st.session_state.payroll_expenses[index].update({
        "item": str(item).strip().upper(),
        "price": p,
    })
    persist_state()
    return True

def build_html_report(records, budget, custom_title="INVENTORY RECEIPT"):
    """Build a responsive construction receipt matching the supplied Ailyn House design."""
    material_and_expense_records = [
        r for r in records if r["type"] in ["material", "expense"]
    ]
    excess_records = [r for r in records if r["type"] == "excess"]

    material_total = sum(float(r.get("amount", 0)) for r in material_and_expense_records)
    excess_total = sum(float(r.get("amount", 0)) for r in excess_records)
    remaining_balance = float(get_balance())

    date_now = datetime.now().strftime("%B %d, %Y")
    sobra_amount = max(remaining_balance, 0.0)
    kulang_amount = abs(min(remaining_balance, 0.0))

    if budget <= 0:
        balance_color = "#ffffff"
    elif remaining_balance < 0:
        balance_color = "#ffb4a8"
    else:
        balance_color = "#d7ffe4"

    # Inline SVG keeps the receipt self-contained and works on phones/laptops
    # without requiring a separate logo image file.
    logo_svg = """
    <svg class="house-logo" viewBox="0 0 120 120" role="img" aria-label="Ailyn House Project logo">
      <path d="M18 58 L60 20 L102 58 V101 H72 V72 H48 V101 H18 Z"
            fill="none" stroke="#0b6b2d" stroke-width="7"
            stroke-linejoin="round"/>
      <path d="M31 52 L60 29 L89 52" fill="none"
            stroke="#4b9b3b" stroke-width="7" stroke-linecap="round"/>
      <path d="M52 50 H68 V69 H52 Z" fill="#0b6b2d"/>
      <path d="M60 50 V69 M52 59.5 H68" stroke="#ffffff" stroke-width="3"/>
      <path d="M22 92 C11 88 7 77 9 67 C20 68 30 76 34 88"
            fill="#4b9b3b"/>
      <path d="M88 92 C99 88 106 77 103 67 C92 68 82 76 78 88"
            fill="#4b9b3b"/>
      <path d="M60 83 C48 90 43 102 45 111 C56 109 63 101 60 83 Z"
            fill="#0b6b2d"/>
      <path d="M60 83 C72 90 77 102 75 111 C64 109 57 101 60 83 Z"
            fill="#4b9b3b"/>
    </svg>
    """

    rows_html = ""
    if material_and_expense_records:
        for r in material_and_expense_records:
            qty = r.get("qty", 1)
            price = float(r.get("price", r.get("amount", 0)))
            delivery = float(r.get("delivery", 0))
            amount = float(r.get("amount", 0))
            rows_html += f"""
            <tr>
              <td data-label="DATE">{r.get('date', '')}</td>
              <td data-label="QTY" class="center">{qty}</td>
              <td data-label="ITEM / DESCRIPTION" class="description">{r.get('name', '')}</td>
              <td data-label="UNIT PRICE" class="money">PHP {price:,.2f}</td>
              <td data-label="DELIVERY" class="money">PHP {delivery:,.2f}</td>
              <td data-label="TOTAL" class="money total-cell">PHP {amount:,.2f}</td>
            </tr>
            """
    else:
        rows_html = """
        <tr class="empty-row">
          <td colspan="6">No materials or expenses recorded.</td>
        </tr>
        """

    excess_html = ""
    if excess_total > 0:
        excess_html = f"""
        <div class="summary-row">
          <span>Excess Money Total:</span>
          <strong>PHP {excess_total:,.2f}</strong>
        </div>
        """

    balance_status_html = ""
    if kulang_amount > 0:
        balance_status_html = f"""
        <div class="summary-row status-row shortage">
          <span>SHORTAGE</span>
          <strong>PHP {kulang_amount:,.2f}</strong>
        </div>
        """
    elif sobra_amount > 0:
        balance_status_html = f"""
        <div class="summary-row status-row excess">
          <span>EXCESS</span>
          <strong>PHP {sobra_amount:,.2f}</strong>
        </div>
        """
    else:
        balance_status_html = """
        <div class="summary-row status-row balanced">
          <span>STATUS</span>
          <strong>BALANCED</strong>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<meta name="theme-color" content="#0b5f2a">
<meta name="description" content="Ailyn Construction official receipt — UHD 4K export">
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>

<style>
* {{
  box-sizing: border-box;
}}

:root {{
  --green: #075c28;
  --green-dark: #03471f;
  --green-mid: #0b6b2d;
  --green-light: #e8f4e8;
  --gold: #b58b24;
  --gold-light: #d8b64c;
  --line: #dfe6df;
  --text: #27332b;
  --muted: #667169;
  --danger: #df6a55;
}}

html, body {{
  margin: 0;
  padding: 0;
  width: 100%;
  background: #f4f7f4;
  color: var(--text);
  font-family: Arial, Helvetica, sans-serif;
  -webkit-text-size-adjust: 100%;
}}

body {{
  padding: clamp(10px, 2vw, 28px);
}}

.save-btn-container {{
  display: flex;
  justify-content: center;
  margin: 0 auto 14px;
}}

.save-img-btn {{
  border: 0;
  border-radius: 10px;
  padding: 12px 20px;
  background: var(--green);
  color: white;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,.16);
}}

.save-img-btn:hover {{
  background: var(--green-mid);
}}

.receipt-page {{
  width: min(100%, 1500px);
  margin: 0 auto;
  background: #fff;
  overflow: hidden;
  border: 1px solid #d7ddd7;
  border-top: 5px solid var(--green);
  box-shadow: 0 10px 30px rgba(0,0,0,.10);
  position: relative;
}}

.receipt-page::before {{
  content: "";
  position: absolute;
  top: 0;
  right: 0;
  width: 42%;
  height: 88px;
  background:
    linear-gradient(145deg, transparent 0 34%, rgba(7,92,40,.09) 35% 58%, transparent 59%),
    linear-gradient(145deg, transparent 0 48%, rgba(181,139,36,.10) 49% 62%, transparent 63%);
  pointer-events: none;
}}

.receipt-page::after {{
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  width: 340px;
  height: 100px;
  opacity: .08;
  background:
    linear-gradient(90deg, transparent 0 15%, var(--green) 15% 16%, transparent 16% 31%, var(--green) 31% 32%, transparent 32% 47%, var(--green) 47% 48%, transparent 48%),
    linear-gradient(0deg, transparent 0 38%, var(--green) 38% 40%, transparent 40% 63%, var(--green) 63% 65%, transparent 65%);
  clip-path: polygon(0 100%, 0 68%, 14% 54%, 26% 65%, 39% 43%, 54% 62%, 69% 35%, 82% 58%, 100% 43%, 100% 100%);
  pointer-events: none;
}}

.receipt-inner {{
  position: relative;
  z-index: 1;
  padding: clamp(18px, 3vw, 48px);
}}

.top-gold-line {{
  height: 2px;
  width: 100%;
  background: linear-gradient(90deg, var(--gold), transparent 72%);
  margin: -12px 0 18px;
}}

.header {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, .48fr);
  gap: 30px;
  align-items: center;
  padding-bottom: 24px;
}}

.brand {{
  display: flex;
  align-items: center;
  gap: 17px;
  min-width: 0;
}}

.house-logo {{
  width: 94px;
  height: 94px;
  flex: 0 0 auto;
}}

.company-name {{
  margin: 0;
  color: var(--green);
  font-size: clamp(25px, 3vw, 46px);
  line-height: 1.05;
  font-weight: 900;
  letter-spacing: -.8px;
  text-transform: uppercase;
}}

.company-sub {{
  margin: 7px 0 0;
  color: #606a63;
  font-size: clamp(11px, 1.1vw, 17px);
  line-height: 1.5;
}}

.company-version {{
  color: #606a63;
}}

.backup {{
  margin-top: 3px;
}}

.backup em {{
  color: var(--green);
  font-weight: 700;
}}

.receipt-meta {{
  min-height: 115px;
  padding-left: 28px;
  border-left: 1px solid #d7ddd7;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-end;
  text-align: right;
}}

.receipt-meta h2 {{
  margin: 0 0 14px;
  color: var(--green);
  font-size: clamp(20px, 2.1vw, 32px);
  line-height: 1.15;
  font-weight: 900;
  text-transform: uppercase;
}}

.date-line {{
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 9px;
  color: #59645c;
  font-size: clamp(12px, 1vw, 16px);
  font-weight: 700;
}}

.calendar-icon {{
  color: var(--green);
  font-size: 22px;
}}

.table-wrap {{
  width: 100%;
  overflow-x: auto;
  border: 1px solid #d7ddd7;
  border-radius: 16px;
  -webkit-overflow-scrolling: touch;
}}

.receipt-table {{
  width: 100%;
  min-width: 760px;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
}}

.receipt-table thead th {{
  background: var(--green);
  color: #fff;
  padding: 15px 13px;
  text-align: left;
  font-size: 12px;
  letter-spacing: .04em;
  text-transform: uppercase;
  white-space: nowrap;
  border-right: 1px solid rgba(255,255,255,.13);
}}

.receipt-table thead th:first-child {{
  border-top-left-radius: 14px;
}}

.receipt-table thead th:last-child {{
  border-top-right-radius: 14px;
  border-right: 0;
}}

.receipt-table td {{
  padding: 17px 13px;
  border-right: 1px solid #e5eae5;
  border-bottom: 1px solid #e5eae5;
  vertical-align: middle;
  background: #fff;
}}

.receipt-table tbody tr:last-child td {{
  border-bottom: 0;
}}

.receipt-table td:last-child {{
  border-right: 0;
}}

.receipt-table .center {{
  text-align: center;
}}

.receipt-table .money {{
  text-align: right;
  white-space: nowrap;
}}

.receipt-table .description {{
  color: var(--green);
  font-weight: 800;
  text-transform: uppercase;
}}

.receipt-table .total-cell {{
  color: var(--green);
  font-weight: 900;
}}

.empty-row td {{
  text-align: center;
  color: #89928b;
  padding: 28px;
}}

.bottom-grid {{
  display: grid;
  grid-template-columns: minmax(300px, 1fr) minmax(390px, .92fr);
  gap: clamp(22px, 5vw, 80px);
  align-items: end;
  margin-top: 28px;
}}

.thank-you {{
  max-width: 500px;
  padding: 22px 24px;
  border: 1px solid #d6ddd6;
  border-radius: 18px;
  background: rgba(255,255,255,.94);
  box-shadow: 0 4px 14px rgba(0,0,0,.05);
}}

.thank-row {{
  display: flex;
  gap: 15px;
  align-items: center;
}}

.check {{
  width: 46px;
  height: 46px;
  flex: 0 0 46px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #e8f5e9;
  color: var(--green);
  border: 1px solid #c9dfcc;
  font-size: 23px;
  font-weight: 900;
}}

.thank-you h3 {{
  margin: 0 0 5px;
  color: var(--green);
  font-size: 18px;
}}

.thank-you p {{
  margin: 0;
  color: #667169;
  font-size: 12px;
  line-height: 1.55;
}}

.summary {{
  background: var(--green);
  color: #fff;
  padding: 26px 30px;
  border-radius: 16px;
  box-shadow: 0 8px 18px rgba(3,71,31,.16);
}}

.summary-row {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 20px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255,255,255,.22);
  font-size: 14px;
}}

.summary-row strong {{
  white-space: nowrap;
}}

.summary-main {{
  font-size: clamp(19px, 1.8vw, 27px);
  font-weight: 900;
  padding-top: 0;
}}

.summary-main span:last-child {{
  font-size: clamp(18px, 1.7vw, 25px);
}}

.summary-row.status-row {{
  margin-top: 5px;
  padding-top: 15px;
  border-top: 1px dashed rgba(255,255,255,.35);
  font-size: clamp(17px, 1.5vw, 23px);
  font-weight: 900;
}}

.summary-row.shortage strong {{
  color: #ffb4a8;
}}

.summary-row.excess strong {{
  color: #d7ffe4;
}}

.summary-row.balanced strong {{
  color: #fff;
}}

.final-balance {{
  margin-top: 5px;
  padding-top: 15px;
  border-top: 1px dashed rgba(255,255,255,.55);
  display: flex;
  justify-content: space-between;
  gap: 20px;
  font-size: clamp(18px, 1.7vw, 25px);
  font-weight: 900;
}}

.final-balance strong {{
  color: {balance_color};
  white-space: nowrap;
}}

.footer {{
  margin-top: 34px;
  padding: 15px 0 2px;
  border-top: 2px solid #e5e9e5;
  text-align: center;
  color: #657168;
  font-size: 10px;
  letter-spacing: .11em;
  text-transform: uppercase;
}}

.footer::before {{
  content: "✓";
  display: inline-grid;
  place-items: center;
  width: 18px;
  height: 18px;
  margin-right: 9px;
  border-radius: 50%;
  background: #e6f3e8;
  color: var(--green);
  font-weight: 900;
}}

@media (max-width: 850px) {{
  .header {{
    grid-template-columns: 1fr;
    gap: 18px;
  }}

  .receipt-meta {{
    border-left: 0;
    border-top: 1px solid #d7ddd7;
    padding: 18px 0 0;
    align-items: flex-start;
    text-align: left;
  }}

  .date-line {{
    justify-content: flex-start;
  }}

  .bottom-grid {{
    grid-template-columns: 1fr;
    gap: 18px;
  }}

  .thank-you {{
    max-width: none;
  }}
}}

@media (max-width: 600px) {{
  body {{
    padding: 6px;
  }}

  .save-img-btn {{
    width: 100%;
    min-height: 44px;
  }}

  .receipt-page {{
    border-top-width: 4px;
    border-radius: 0;
  }}

  .receipt-inner {{
    padding: 14px;
  }}

  .brand {{
    align-items: flex-start;
    gap: 10px;
  }}

  .house-logo {{
    width: 64px;
    height: 64px;
  }}

  .company-name {{
    font-size: 24px;
  }}

  .company-sub {{
    font-size: 10px;
  }}

  .receipt-meta h2 {{
    font-size: 20px;
  }}

  .table-wrap {{
    border: 0;
    overflow: visible;
  }}

  .receipt-table {{
    min-width: 0;
    display: block;
    font-size: 12px;
  }}

  .receipt-table thead {{
    display: none;
  }}

  .receipt-table tbody,
  .receipt-table tr,
  .receipt-table td {{
    display: block;
    width: 100%;
  }}

  .receipt-table tr {{
    margin-bottom: 12px;
    border: 1px solid #d7ddd7;
    border-radius: 12px;
    overflow: hidden;
    background: #fff;
    box-shadow: 0 3px 10px rgba(0,0,0,.04);
  }}

  .receipt-table td {{
    min-height: 38px;
    padding: 9px 12px 9px 43%;
    position: relative;
    border-right: 0;
    border-bottom: 1px solid #edf0ed;
    text-align: right !important;
    white-space: normal;
  }}

  .receipt-table td:last-child {{
    border-bottom: 0;
  }}

  .receipt-table td::before {{
    content: attr(data-label);
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #667169;
    font-size: 9px;
    font-weight: 900;
    letter-spacing: .08em;
    text-transform: uppercase;
    text-align: left;
  }}

  .receipt-table .description {{
    color: var(--green);
  }}

  .receipt-table .money {{
    white-space: normal;
  }}

  .empty-row td {{
    padding: 24px 15px;
    text-align: center !important;
  }}

  .empty-row td::before {{
    display: none;
  }}

  .summary {{
    padding: 20px 18px;
    border-radius: 13px;
  }}

  .summary-row {{
    font-size: 12px;
  }}

  .summary-main {{
    font-size: 18px;
  }}

  .summary-row.status-row {{
    font-size: 17px;
  }}

  .final-balance {{
    font-size: 18px;
  }}

  .thank-you {{
    padding: 17px;
  }}

  .thank-you h3 {{
    font-size: 16px;
  }}

  .footer {{
    font-size: 8px;
    line-height: 1.6;
  }}
}}

@media print {{
  body {{
    background: white;
    padding: 0;
  }}

  .save-btn-container {{
    display: none !important;
  }}

  .receipt-page {{
    width: 100%;
    box-shadow: none;
    border: 0;
    border-top: 5px solid var(--green);
  }}
}}
</style>
</head>

<body>
<div class="save-btn-container">
  <button class="save-img-btn" onclick="saveAsImage()">SEE PHOTO &amp; DOWNLOAD IMAGE • UHD 4K</button>
</div>

<div class="receipt-page" id="receiptContent">
  <div class="receipt-inner">

    <div class="top-gold-line"></div>

    <header class="header">
      <div class="brand">
        {logo_svg}
        <div>
          <h1 class="company-name">AILYN HOUSE PROJECT</h1>
          <p class="company-sub">Official Material &amp; Expense Inventory</p>
          <p class="company-sub company-version">Management System {APP_VERSION}</p>
          <p class="company-sub backup">Backup Receiver: <em>{RECEIVER_AILYN}</em></p>
        </div>
      </div>

      <div class="receipt-meta">
        <h2>{custom_title}</h2>
        <div class="date-line">
          <span class="calendar-icon">▣</span>
          <span>Date: ____________________</span>
        </div>
        <div class="company-sub" style="margin-top:7px;">Generated: {date_now}</div>
      </div>
    </header>

    <div class="table-wrap">
      <table class="receipt-table">
        <thead>
          <tr>
            <th>▣ &nbsp; DATE</th>
            <th>▦ &nbsp; QTY</th>
            <th>⚒ &nbsp; ITEM / DESCRIPTION</th>
            <th>◆ &nbsp; UNIT PRICE</th>
            <th>▰ &nbsp; DELIVERY</th>
            <th>▤ &nbsp; TOTAL</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>

    <div class="bottom-grid">
      <div class="thank-you">
        <div class="thank-row">
          <div class="check">✓</div>
          <div>
            <h3>Thank you for your trust.</h3>
            <p>This receipt confirms the materials and expenses recorded for the Ailyn House Project.</p>
          </div>
        </div>
      </div>

      <div class="summary">
        <div class="summary-row summary-main">
          <span>Material/Expense Total:</span>
          <span>PHP {material_total:,.2f}</span>
        </div>

        {excess_html}

        <div class="summary-row">
          <span>Total Budget:</span>
          <strong>PHP {float(budget):,.2f}</strong>
        </div>

        {balance_status_html}

        <div class="final-balance">
          <span>FINAL BALANCE</span>
          <strong>PHP {remaining_balance:,.2f}</strong>
        </div>
      </div>
    </div>

    <footer class="footer">
      THIS DOCUMENT WAS ELECTRONICALLY GENERATED AND IS VALID WITHOUT SIGNATURE.
    </footer>

  </div>
</div>

<script>
function saveAsImage() {{
  const element = document.getElementById('receiptContent');

  if (typeof html2canvas === 'undefined') {{
    window.print();
    return;
  }}

  html2canvas(element, {{
    scale: Math.min(4, Math.max(2, 3840 / Math.max(element.getBoundingClientRect().width, 1))), windowWidth: element.scrollWidth, windowHeight: element.scrollHeight,
    useCORS: true,
    backgroundColor: '#ffffff',
    logging: false,
    scrollX: 0,
    scrollY: 0
  }}).then(canvas => {{
    const link = document.createElement('a');
    link.download = '{custom_title.replace(" ", "_")}_Receipt.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  }}).catch(() => {{
    window.print();
  }});
}}
</script>
</body>
</html>"""

    return html


def generate_payroll_html(labor_records, expense_records, remaining_money=0.0, custom_title="PAYROLL RECEIPT"):
    """Generate a responsive Ailyn Construction payroll receipt matching the reference design."""
    date_str = datetime.now().strftime("%B %d, %Y | %I:%M %p")
    receipt_no = datetime.now().strftime("PR-%Y%m%d-%H%M%S")
    total_labor = sum(float(r.get('net', 0) or 0) for r in labor_records)
    total_expenses = sum(float(e.get('price', 0) or 0) for e in expense_records)
    total_ca = sum(float(r.get('ca', 0) or 0) for r in labor_records)
    subtotal = total_labor + total_expenses
    grand_total = subtotal - (remaining_money or 0.0)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
    font-family: Arial, Helvetica, sans-serif;
    background: #ffffff;
    color: #183528;
    padding: 0;
}}
.page {{
    width: 100%;
    min-height: 100vh;
    background: #fff;
    position: relative;
    overflow: hidden;
}}
.top-line {{ height: 10px; background: #075d2c; width: 100%; }}
.gold-line {{ height: 2px; background: #c79a2b; width: 52%; margin: 42px 0 0 38px; }}
.receipt {{
    width: min(1460px, calc(100% - 72px));
    margin: 0 auto;
    padding: 28px 0 34px;
    position: relative;
}}
.receipt::after {{
    content: "";
    position: absolute;
    right: -40px;
    top: 0;
    width: 300px;
    height: 170px;
    background: linear-gradient(135deg, transparent 0 32%, rgba(7,93,44,.08) 32% 52%, transparent 52% 62%, rgba(199,154,43,.05) 62% 76%, transparent 76%);
    pointer-events: none;
}}
.header {{
    display: grid;
    grid-template-columns: 1fr 0.65fr;
    gap: 38px;
    align-items: center;
    padding: 0 0 28px;
}}
.brand {{ display: flex; align-items: center; gap: 22px; min-width: 0; }}
.logo {{ width: 150px; height: 145px; flex: 0 0 150px; }}
.brand h1 {{
    margin: 0;
    color: #075d2c;
    font-size: clamp(34px, 4vw, 67px);
    line-height: .95;
    font-weight: 900;
    letter-spacing: -2px;
    text-transform: uppercase;
}}
.brand .subtitle {{ color: #075d2c; font-size: clamp(16px, 1.5vw, 22px); margin-top: 12px; }}
.brand .system {{ color: #444; font-size: 17px; margin-top: 16px; }}
.brand .account {{ color: #333; font-size: 17px; margin-top: 10px; }}
.brand .account b {{ color: #075d2c; }}
.meta {{ border-left: 1px solid #d8ded9; padding: 10px 0 10px 48px; text-align: right; position: relative; z-index: 2; }}
.meta h2 {{ color: #075d2c; margin: 0 0 26px; font-size: clamp(28px, 3vw, 48px); font-weight: 900; text-transform: uppercase; }}
.meta .row {{ margin: 0 0 16px; font-size: 17px; color: #333; white-space: nowrap; }}
.meta .label {{ color: #075d2c; font-weight: 800; margin-right: 10px; }}
.meta .date-line {{ border-bottom: 1px solid #cfd8d2; padding-bottom: 9px; display: inline-block; min-width: 300px; }}
.table-wrap {{ width: 100%; overflow-x: auto; border: 1px solid #c7d0ca; border-radius: 18px; margin-top: 6px; }}
table.payroll {{ width: 100%; min-width: 900px; border-collapse: separate; border-spacing: 0; }}
table.payroll th {{
    background: #075d2c; color: white; padding: 17px 18px; font-size: 16px; font-weight: 800;
    text-transform: uppercase; text-align: left; border-right: 1px solid rgba(255,255,255,.2);
}}
table.payroll th:first-child {{ border-radius: 16px 0 0 0; }}
table.payroll th:last-child {{ border-radius: 0 16px 0 0; border-right: 0; }}
table.payroll td {{ padding: 20px 18px; height: 62px; border-right: 1px solid #e0e5e1; border-bottom: 1px dashed #d8ded9; font-size: 15px; }}
table.payroll tr:last-child td {{ border-bottom: 0; }}
table.payroll td:last-child {{ border-right: 0; }}
table.payroll .center {{ text-align: center; }}
table.payroll .money {{ text-align: right; white-space: nowrap; }}
table.payroll .net {{ color: #075d2c; font-weight: 800; }}
.empty-row td {{ height: 55px; }}
.lower {{ display: grid; grid-template-columns: 1fr 1.35fr; gap: 80px; align-items: center; margin-top: 48px; }}
.thanks {{ border: 1px solid #c9d3cd; border-radius: 18px; padding: 28px 30px; display: flex; align-items: center; gap: 26px; max-width: 560px; }}
.check {{ width: 76px; height: 76px; flex: 0 0 76px; border-radius: 50%; background: #e3f1e7; display: grid; place-items: center; color: #075d2c; font-size: 48px; font-weight: 300; }}
.thanks h3 {{ margin: 0 0 12px; color: #075d2c; font-size: 25px; }}
.thanks p {{ margin: 0; color: #333; font-size: 17px; line-height: 1.45; }}
.summary {{ background: linear-gradient(135deg, #075d2c, #006b31); color: white; border-radius: 20px; padding: 30px 34px; min-height: 260px; position: relative; overflow: hidden; }}
.summary::after {{ content: "⌂"; position: absolute; right: 10px; bottom: -45px; font-size: 220px; line-height: 1; color: rgba(255,255,255,.055); font-weight: 900; }}
.sum-row {{ position: relative; z-index: 1; display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 4px 0 17px; margin-bottom: 14px; border-bottom: 1px dashed rgba(255,255,255,.42); font-size: 20px; font-weight: 700; }}
.sum-row:last-of-type {{ border-bottom: 0; }}
.sum-row .value {{ white-space: nowrap; }}
.final {{ position: relative; z-index: 1; border-top: 1px solid rgba(255,255,255,.8); padding-top: 25px; display: flex; justify-content: space-between; align-items: center; gap: 20px; }}
.final .label {{ font-size: 31px; font-weight: 900; text-transform: uppercase; }}
.final .value {{ font-size: clamp(30px, 3.2vw, 48px); font-weight: 900; white-space: nowrap; }}
.footer {{ margin-top: 60px; border-top: 1px solid #d7ddd9; padding: 24px 30px; text-align: center; color: #5c625f; font-size: 12px; letter-spacing: 2px; text-transform: uppercase; }}
.footer .shield {{ color: #075d2c; font-size: 24px; vertical-align: middle; margin-right: 16px; }}
.save-btn-container {{ text-align: center; padding: 18px; background: #f7faf8; }}
.save-img-btn {{ background: #075d2c; color: white; border: 0; padding: 13px 24px; font-size: 14px; font-weight: 800; border-radius: 8px; cursor: pointer; }}
.save-img-btn:hover {{ background: #0a7137; }}
@media print {{ .save-btn-container {{ display: none; }} body {{ background: white; }} .receipt {{ width: calc(100% - 30px); }} }}
@media (max-width: 900px) {{
    .receipt {{ width: calc(100% - 28px); padding-top: 18px; }}
    .header {{ grid-template-columns: 1fr; gap: 18px; }}
    .meta {{ border-left: 0; border-top: 1px solid #d8ded9; padding: 20px 0 0; text-align: left; }}
    .meta h2 {{ margin-bottom: 14px; }}
    .meta .date-line {{ min-width: 0; }}
    .lower {{ grid-template-columns: 1fr; gap: 22px; }}
    .summary {{ min-height: 230px; }}
}}
@media (max-width: 600px) {{
    .gold-line {{ margin: 18px 0 0 18px; width: 65%; }}
    .receipt {{ width: calc(100% - 18px); padding: 12px 0 20px; }}
    .brand {{ gap: 12px; align-items: flex-start; }}
    .logo {{ width: 74px; height: 72px; flex-basis: 74px; }}
    .brand h1 {{ font-size: 31px; letter-spacing: -1px; }}
    .brand .subtitle {{ font-size: 14px; margin-top: 6px; }}
    .brand .system, .brand .account {{ font-size: 12px; margin-top: 6px; }}
    .meta h2 {{ font-size: 25px; }}
    .meta .row {{ font-size: 13px; white-space: normal; }}
    .table-wrap {{ border: 0; overflow: visible; }}
    table.payroll {{ min-width: 0; display: block; }}
    table.payroll thead {{ display: none; }}
    table.payroll tbody, table.payroll tr, table.payroll td {{ display: block; width: 100%; }}
    table.payroll tr {{ border: 1px solid #c7d0ca; border-radius: 14px; margin-bottom: 12px; overflow: hidden; background: #fff; }}
    table.payroll td {{ height: auto; min-height: 0; padding: 9px 14px 9px 48%; text-align: right; border-right: 0; border-bottom: 1px solid #edf0ee; position: relative; font-size: 13px; }}
    table.payroll td::before {{ content: attr(data-label); position: absolute; left: 14px; top: 9px; width: 42%; text-align: left; font-weight: 800; color: #075d2c; text-transform: uppercase; font-size: 10px; }}
    table.payroll .center, table.payroll .money {{ text-align: right; }}
    .empty-row {{ display: none !important; }}
    .lower {{ margin-top: 25px; }}
    .thanks {{ padding: 20px; gap: 14px; }}
    .check {{ width: 56px; height: 56px; flex-basis: 56px; font-size: 34px; }}
    .thanks h3 {{ font-size: 20px; }}
    .thanks p {{ font-size: 14px; }}
    .summary {{ padding: 22px 20px; border-radius: 16px; }}
    .sum-row {{ font-size: 15px; padding-bottom: 12px; }}
    .final .label {{ font-size: 21px; }}
    .final .value {{ font-size: 29px; }}
    .footer {{ margin-top: 28px; padding: 18px 8px; font-size: 9px; letter-spacing: 1px; }}
}}
</style>
</head>
<body>
<div class="page">
<div class="top-line"></div>
<div class="gold-line"></div>
<div class="save-btn-container">
    <button class="save-img-btn" onclick="saveAsImage()">SEE PHOTO &amp; DOWNLOAD IMAGE • UHD 4K</button>
</div>
<div class="receipt" id="receiptContent">
    <div class="header">
        <div class="brand">
            <svg class="logo" viewBox="0 0 180 170" xmlns="http://www.w3.org/2000/svg" aria-label="Ailyn Construction logo">
                <path d="M18 142 L18 87 L53 55 L53 113 L87 81 L87 35 L116 9 L116 103 L145 79 L145 140 Z" fill="#075d2c"/>
                <path d="M4 145 L90 80 L176 145 L162 145 L90 111 L18 145 Z" fill="#075d2c"/>
                <path d="M37 136 L90 104 L143 136 L143 154 L37 154 Z" fill="white"/>
                <path d="M67 136 h46 v28 h-46z" fill="#075d2c"/>
                <path d="M82 137 h16 v27 h-16z M67 148 h46 v8 h-46z" fill="white"/>
                <path d="M30 160 H151" stroke="#075d2c" stroke-width="5"/>
            </svg>
            <div>
                <h1>AILYN CONSTRUCTION</h1>
                <div class="subtitle">Official Labor &amp; Payroll Inventory</div>
                <div class="system">Management System {APP_VERSION} — Payroll Management System</div>
                <div class="account"><b>Account:</b> {RECEIVER_EMAIL}</div>
            </div>
        </div>
        <div class="meta">
            <h2>{custom_title}</h2>
            <div class="row"><span class="label">▣ Date:</span><span class="date-line">{date_str}</span></div>
            <div class="row"><span class="label">Receipt No.:</span> {receipt_no}</div>
        </div>
    </div>

    <div class="table-wrap">
    <table class="payroll">
        <thead>
            <tr>
                <th>▣ &nbsp; Worker Name</th>
                <th>● &nbsp; Role</th>
                <th>▣ &nbsp; Days / Point</th>
                <th>▣ &nbsp; Gross Pay</th>
                <th>− &nbsp; C.A.</th>
                <th>▣ &nbsp; Net Pay</th>
            </tr>
        </thead>
        <tbody>
"""

    for r in labor_records:
        role_display = r.get('role', 'Labor')
        gross = float(r.get('gross_pay', float(r.get('days', 0) or 0) * float(r.get('rate', 0) or 0)))
        ca = float(r.get('ca', 0) or 0)
        net = float(r.get('net', 0) or 0)
        html += f"""
            <tr>
                <td data-label="Worker Name"><b>{r.get('name', '')}</b></td>
                <td data-label="Role" class="center">{role_display}</td>
                <td data-label="Days / Point" class="center">{float(r.get('days', 0) or 0):.1f}</td>
                <td data-label="Gross Pay" class="money">PHP {gross:,.2f}</td>
                <td data-label="C.A." class="money">PHP {ca:,.2f}</td>
                <td data-label="Net Pay" class="money net">PHP {net:,.2f}</td>
            </tr>
"""

    if not labor_records:
        for _ in range(3):
            html += """<tr class="empty-row"><td></td><td></td><td></td><td></td><td></td><td></td></tr>"""

    if expense_records:
        html += """
            <tr class="expense-heading">
                <td data-label="Expense" colspan="5"><b>Expense Description</b></td>
                <td data-label="Amount" class="money"><b>Amount</b></td>
            </tr>
"""
        for e in expense_records:
            price = float(e.get('price', 0) or 0)
            html += f"""
            <tr>
                <td data-label="Expense Description" colspan="5">{e.get('item', '')}</td>
                <td data-label="Amount" class="money">PHP {price:,.2f}</td>
            </tr>
"""

    html += f"""
        </tbody>
    </table>
    </div>

    <div class="lower">
        <div class="thanks">
            <div class="check">✓</div>
            <div>
                <h3>Thank you for your hard work!</h3>
                <p>This payroll receipt confirms your earnings<br class="desktop-only"> for the specified period.</p>
            </div>
        </div>
        <div class="summary">
            <div class="sum-row"><span>Subtotal Expenses:</span><span class="value">PHP {subtotal:,.2f}</span></div>
            <div class="sum-row"><span>Total Deductions (C.A.):</span><span class="value">PHP {total_ca:,.2f}</span></div>
            <div class="final"><span class="label">Final Net Pay</span><span class="value">PHP {grand_total:,.2f}</span></div>
        </div>
    </div>

    <div class="footer"><span class="shield">♢</span> THIS DOCUMENT WAS ELECTRONICALLY GENERATED AND IS VALID WITHOUT SIGNATURE.</div>
</div>
</div>
<script>
function saveAsImage() {{
    const element = document.getElementById('receiptContent');
    html2canvas(element, {{ scale: Math.min(4, Math.max(2, 3840 / Math.max(element.getBoundingClientRect().width, 1))), windowWidth: element.scrollWidth, windowHeight: element.scrollHeight, useCORS: true, backgroundColor: '#ffffff', imageTimeout: 30000 }}).then(canvas => {{
        const link = document.createElement('a');
        link.download = '{custom_title.replace(" ", "_")}_Receipt.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
    }}).catch(() => {{
        window.print();
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
<button class="save-img-btn" onclick="saveAsImage()">SEE PHOTO & DOWNLOAD IMAGE • UHD 4K</button>
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
    html2canvas(element, {{ scale: Math.min(4, Math.max(2, 3840 / Math.max(element.getBoundingClientRect().width, 1))), windowWidth: element.scrollWidth, windowHeight: element.scrollHeight, useCORS: true, imageTimeout: 30000 }}).then(canvas => {{
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
html,body,[class*="css"]{font-family:'Manrope',sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;text-rendering:geometricPrecision}
img,svg,canvas{image-rendering:auto}
.stApp,.block-container{transform:translateZ(0)}
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
.cal-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px;margin-top:18px}.cal-card{position:relative;overflow:hidden;background:linear-gradient(145deg,rgba(16,69,40,.80),rgba(4,27,16,.85));border:1px solid rgba(165,255,195,.18);border-radius:24px;padding:20px;box-shadow:0 14px 34px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.08);transition:.22s cubic-bezier(.2,.8,.2,1);backdrop-filter:blur(14px)}.cal-card:hover{transform:translateY(-7px) scale(1.012);border-color:rgba(114,247,176,.45);box-shadow:0 24px 50px rgba(0,0,0,.40),0 0 30px rgba(114,247,176,.11)}.cal-date-badge{background:rgba(114,247,176,.10);color:#72f7b0;border:1px solid rgba(114,247,176,.28);padding:5px 11px;border-radius:999px;font-size:10px;font-weight:900}.cal-task-title{color:#fff;font-family:'Outfit';font-size:17px;font-weight:800}.cal-phase{color:#a8dcb8;font-size:12px}.cal-status-tag{font-size:9px;font-weight:900;padding:5px 10px;border-radius:999px;text-transform:uppercase}

/* sidebar reference polish: glass depth, touch lift, directional light */
section[data-testid="stSidebar"] button{backdrop-filter:blur(18px) saturate(150%);-webkit-backdrop-filter:blur(18px) saturate(150%);box-shadow:0 10px 24px rgba(0,0,0,.30),inset 0 1px 0 rgba(255,255,255,.09),inset 0 -10px 22px rgba(0,0,0,.12)!important}
section[data-testid="stSidebar"] button::before{content:"";position:absolute;inset:0;background:linear-gradient(105deg,transparent 8%,rgba(255,255,255,.075) 43%,transparent 57%);transform:translateX(-125%);transition:transform .65s ease;pointer-events:none}
section[data-testid="stSidebar"] button:hover::before{transform:translateX(125%)}
section[data-testid="stSidebar"] button:hover{transform:translate3d(5px,-3px,0) scale(1.005)!important;box-shadow:0 15px 32px rgba(0,0,0,.40),0 0 24px rgba(57,233,130,.12),inset 0 1px 0 rgba(255,255,255,.16),inset 0 -10px 24px rgba(0,0,0,.10)!important}
section[data-testid="stSidebar"] button:active{transform:translate3d(2px,2px,0) scale(.995)!important}
section[data-testid="stSidebar"] .brand-logo{transition:transform .28s cubic-bezier(.2,.8,.2,1),filter .28s ease;filter:drop-shadow(0 9px 15px rgba(0,0,0,.30))}
section[data-testid="stSidebar"] .sidebar-brand:hover .brand-logo{transform:translateY(-3px) scale(1.035);filter:drop-shadow(0 13px 24px rgba(57,233,130,.24))}

/* ===== SIDEBAR V2 — reference-inspired glass command rail ===== */
section[data-testid="stSidebar"]{
  background:
    radial-gradient(circle at 55% 7%, rgba(24,132,74,.18), transparent 27%),
    radial-gradient(circle at 20% 58%, rgba(19,103,59,.13), transparent 32%),
    linear-gradient(180deg, rgba(1,18,11,.985), rgba(2,28,17,.975) 48%, rgba(1,14,9,.99)) !important;
  border-right:1px solid rgba(91,236,153,.18)!important;
  box-shadow: 20px 0 70px rgba(0,0,0,.48), inset -1px 0 0 rgba(255,255,255,.035)!important;
}
section[data-testid="stSidebar"] > div{padding:18px 14px 30px!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]{color:#ecfff4!important}
section[data-testid="stSidebar"] .sidebar-brand{
  background:linear-gradient(145deg,rgba(8,67,38,.62),rgba(1,22,13,.45))!important;
  border:1px solid rgba(61,221,128,.20)!important;
  border-radius:24px!important;
  box-shadow:0 22px 50px rgba(0,0,0,.42),inset 0 1px 0 rgba(255,255,255,.08),inset 0 0 30px rgba(52,222,122,.035)!important;
  backdrop-filter:blur(24px) saturate(145%);-webkit-backdrop-filter:blur(24px) saturate(145%);
}
section[data-testid="stSidebar"] .brand-icon{
  background:linear-gradient(145deg,rgba(42,171,98,.35),rgba(7,79,43,.18))!important;
  border:1px solid rgba(96,255,165,.30)!important;
  box-shadow:0 10px 28px rgba(0,0,0,.35),0 0 28px rgba(58,225,125,.12),inset 0 1px 0 rgba(255,255,255,.18)!important;
}
section[data-testid="stSidebar"] .brand-title{font-size:15px!important;letter-spacing:.08em!important;color:#f3fff7!important}
section[data-testid="stSidebar"] .brand-sub{color:#7df0ab!important}
section[data-testid="stSidebar"] .sidebar-live{
  margin:10px 2px 0!important;padding:8px 10px!important;border-radius:12px!important;
  color:#73f2a6!important;font-size:9px!important;font-weight:900!important;letter-spacing:.13em!important;
  background:rgba(45,209,112,.055)!important;border:1px solid rgba(77,237,145,.09)!important;
  text-align:center!important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3{
  display:flex;align-items:center;gap:10px;font-family:'Outfit'!important;font-size:10px!important;
  letter-spacing:.18em!important;color:#71efa4!important;margin:19px 5px 9px!important;
  text-transform:uppercase!important;white-space:nowrap;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3::before{
  content:"";width:7px;height:7px;flex:0 0 7px;border-radius:50%;background:#39e982;
  box-shadow:0 0 12px #39e982,0 0 24px rgba(57,233,130,.5);
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3::after{
  content:"";height:1px;flex:1;background:linear-gradient(90deg,rgba(64,222,128,.45),rgba(64,222,128,.05));
}
section[data-testid="stSidebar"] .sidebar-gap{height:7px!important}
section[data-testid="stSidebar"] button{
  min-height:66px!important;margin:6px 0!important;padding:0 18px!important;border-radius:18px!important;
  text-align:left!important;position:relative!important;overflow:hidden!important;
  color:#effff5!important;
  background:linear-gradient(135deg,rgba(9,73,43,.52),rgba(2,31,19,.34))!important;
  border:1px solid rgba(58,224,128,.18)!important;
  box-shadow:0 13px 25px rgba(0,0,0,.30), inset 0 1px 0 rgba(255,255,255,.07), inset 0 0 24px rgba(44,211,114,.025)!important;
  backdrop-filter:blur(22px) saturate(150%)!important;-webkit-backdrop-filter:blur(22px) saturate(150%)!important;
  transition:transform .20s cubic-bezier(.2,.8,.2,1),box-shadow .20s,border-color .20s,background .20s!important;
}
section[data-testid="stSidebar"] button::before{
  content:"";position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(105deg,transparent 15%,rgba(129,255,181,.10) 44%,transparent 58%);
  transform:translateX(-125%);transition:transform .65s ease;
}
section[data-testid="stSidebar"] button:hover{
  transform:translate3d(4px,-3px,0)!important;
  border-color:rgba(67,238,139,.58)!important;
  background:linear-gradient(135deg,rgba(12,91,52,.68),rgba(3,41,24,.46))!important;
  box-shadow:0 18px 34px rgba(0,0,0,.42),0 0 28px rgba(45,224,121,.12),inset 0 1px 0 rgba(255,255,255,.13)!important;
}
section[data-testid="stSidebar"] button:hover::before{transform:translateX(125%)}
section[data-testid="stSidebar"] button:active{transform:translate3d(2px,2px,0)!important;box-shadow:0 7px 16px rgba(0,0,0,.32)!important}
section[data-testid="stSidebar"] button p{font-family:'Manrope'!important;font-size:14px!important;font-weight:800!important;letter-spacing:.01em!important}
section[data-testid="stSidebar"] .stNumberInput > div{
  background:linear-gradient(145deg,rgba(4,40,24,.55),rgba(1,22,13,.35))!important;
  border:1px solid rgba(60,223,127,.18)!important;border-radius:17px!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 10px 25px rgba(0,0,0,.25)!important;
  backdrop-filter:blur(20px)!important;
}
section[data-testid="stSidebar"] .stNumberInput input{font-size:14px!important;font-weight:700!important}
section[data-testid="stSidebar"] .stNumberInput button{min-height:38px!important;height:38px!important;width:38px!important;border-radius:12px!important;margin:0 4px!important}
section[data-testid="stSidebar"] hr{border-color:rgba(69,227,131,.09)!important;margin:12px 4px!important}
@media(max-width:700px){
  section[data-testid="stSidebar"] > div{padding:12px 10px 22px!important}
  section[data-testid="stSidebar"] button{min-height:58px!important;border-radius:16px!important}
  section[data-testid="stSidebar"] button p{font-size:13px!important}
}
.badge-notstarted{background:rgba(255,255,255,.07);color:#d1d5db}.badge-inprogress{background:rgba(245,158,11,.14);color:#fbbf24}.badge-completed{background:rgba(34,197,94,.14);color:#65f394}
[data-testid="stExpander"]{background:rgba(5,29,17,.58)!important;border:1px solid rgba(163,255,194,.15)!important;border-radius:20px!important;box-shadow:0 10px 25px rgba(0,0,0,.18)!important}.stAlert{border-radius:17px!important;background:rgba(8,42,24,.65)!important;border:1px solid rgba(163,255,194,.18)!important}
@keyframes scan{0%,55%{transform:translateX(-130%)}80%,100%{transform:translateX(180%)}}
@media(max-width:900px){.block-container{padding:18px 14px 30px!important;margin:10px!important}.headbar-card{padding:16px}.headbar-title{font-size:24px!important}.headbar-subtitle{margin-left:92px}.hero-title{font-size:32px}.donut-wrap{flex-direction:column;align-items:flex-start}.donut{width:170px;height:170px;flex-basis:170px}.donut:after{inset:42px}.schedule{align-items:flex-start;flex-wrap:wrap}.open-planner{margin-left:0}}
@media(max-width:600px){.headbar-card{display:block}.headbar-title{font-size:21px!important;gap:10px}.headbar-title img{width:52px;height:52px}.headbar-subtitle{margin-left:62px;font-size:8px}.headbar-time{margin-top:12px;display:inline-block}.hero-row{align-items:flex-start}.hero-logo{width:60px;height:60px}.hero-title{font-size:25px}.hero-sub{font-size:9px;letter-spacing:.14em}.dash-section{padding:16px}.tx-row{gap:8px}.tx-right{font-size:11px}.open-planner{width:100%;text-align:center}.sidebar-brand{padding:14px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}
/* UHD 4K rendering helpers */
img{image-rendering:auto;-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}
/* UHD display rendering: keep the interface crisp on high-DPI / 4K screens */
html, body, [class*="css"] { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: geometricPrecision; }
.stApp, .block-container, section[data-testid="stSidebar"] { image-rendering: auto; }

.save-img-btn{font-weight:900!important;letter-spacing:.02em!important}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="headbar-container">
  <div class="headbar-card">
    <div>
      <div class="headbar-title"><img src="{AILYN_LOGO_DATA}" alt="Ailyn Construction Official Logo">AILYN CONSTRUCTION</div>
      <div class="headbar-subtitle">PROJECT MANAGEMENT SYSTEM • PROJECT CONTROL CENTER</div>
    </div>
    <div class="headbar-time">◷ &nbsp; {datetime.now().strftime('%b %d, %Y  |  %I:%M %p')}</div>
  </div>
</div>
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
    st.markdown(f"<div class='sidebar-live'>● &nbsp; LIVE SYSTEM &nbsp; • &nbsp; {datetime.now().strftime('%I:%M %p  |  %b %d')}</div>", unsafe_allow_html=True)
    st.divider()

    st.subheader("Executive Overview")
    if st.button("▣  Dashboard                                      ›", use_container_width=True, key="side_dashboard"):
        set_view("home")

    st.markdown("<div class='sidebar-budget-card'><div class='budget-card-title'>Set Account Budget</div><div class='budget-card-note'>Add unlimited budget amounts. Every new amount is added to the running total.</div></div>", unsafe_allow_html=True)
    budget_input = st.number_input("", min_value=0.01, key="budget_input_sidebar", value=None, placeholder="Enter budget amount...", label_visibility="collapsed")
    b1, b2 = st.columns([1.35, .85])
    with b1:
        if st.button("＋  Add Budget", use_container_width=True, key="side_add_budget"):
            if budget_input is not None and float(budget_input) > 0:
                st.session_state.budget_entries.append(float(budget_input))
                st.session_state.budget = float(sum(st.session_state.budget_entries))
                persist_state()
                st.success(f"Added PHP {float(budget_input):,.2f} to budget.")
                st.rerun()
            else:
                st.warning("Please enter a budget amount.")
    with b2:
        if st.button("↻  Total", use_container_width=True, key="side_budget_current"):
            st.info(f"Budget: PHP {float(sum(st.session_state.budget_entries or [0])):,.2f}")
    if st.session_state.budget_entries:
        total_b = float(sum(st.session_state.budget_entries))
        st.markdown(f"<div class='sidebar-budget-total'><span>TOTAL BUDGET</span><strong>PHP {total_b:,.2f}</strong><small>{len(st.session_state.budget_entries)} amount(s) added</small></div>", unsafe_allow_html=True)
        if st.button("↺  Reset Budget Entries", use_container_width=True, key="side_reset_budget"):
            st.session_state.budget_entries = []
            st.session_state.budget = 0.0
            persist_state()
            st.rerun()

    if st.button("⚙  Restart System                              ›", use_container_width=True, key="side_restart"):
        clear_all()
        set_view("home")

    st.markdown("<div class='sidebar-gap'></div>", unsafe_allow_html=True)
    st.subheader("Project Control")
    if st.button("▣  New Work Entry                              ›", use_container_width=True, key="side_new_work"):
        set_view("planner_input")
    if st.button("☷  Schedule & Progress                      ›", use_container_width=True, key="side_schedule"):
        set_view("planner_output")

    st.markdown("<div class='sidebar-gap'></div>", unsafe_allow_html=True)
    st.subheader("Financial Operations")
    if st.button("◇  Material Entry                              ›", use_container_width=True, key="side_material"):
        set_view("material")
    if st.button("▤  Expense Entry                              ›", use_container_width=True, key="side_expense"):
        set_view("expense")
    if st.button("♨  Encash Deposit                              ›", use_container_width=True, key="side_excess"):
        set_view("excess")
    if st.button("▣  Financial Ledger                            ›", use_container_width=True, key="side_ledger"):
        set_view("ledger")
    if st.button("▥  Financial Report                            ›", use_container_width=True, key="side_report"):
        set_view("export")

    st.markdown("<div class='sidebar-gap'></div>", unsafe_allow_html=True)
    st.subheader("Payroll Operations")
    if st.button("●  Labor Account                               ›", use_container_width=True, key="side_labor"):
        set_view("add_labor")
    if st.button("▣  Payroll Expense                              ›", use_container_width=True, key="side_pay_exp"):
        set_view("add_payroll_expense")
    if st.button("♟  Account Remainder                            ›", use_container_width=True, key="side_pay_rem"):
        set_view("payroll_remaining")
    if st.button("♟  Labor Accounts                              ›", use_container_width=True, key="side_pay_ledger"):
        set_view("payroll_ledger")
    if st.button("▤  Payroll Report                               ›", use_container_width=True, key="side_pay_report"):
        set_view("payroll_export")
    if st.button("▣  Receipts Archive                             ›", use_container_width=True, key="side_archive"):
        set_view("receipt_archive")

view = st.session_state.view

if view == "home":
    budget = float(sum(st.session_state.get("budget_entries", []) or [0.0]))
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
    <div class="dash-hero">
      <div class="hero-row">
        <img class="hero-logo" src="{AILYN_LOGO_DATA}" alt="Ailyn Construction Logo">
        <div>
          <div class="hero-title">AILYN CONSTRUCTION</div>
          <div class="hero-sub">PROJECT MANAGEMENT SYSTEM</div>
        </div>
      </div>
      <div class="hero-rule"></div>
      <div class="welcome">🛡️ &nbsp; Welcome back, <b>Ailyn Project!</b> &nbsp;&nbsp;|&nbsp;&nbsp; Manage your construction project efficiently.</div>
    </div>
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
    st.caption("Edit material names, quantities, prices, delivery, sender, or expense details before exporting the receipt.")
    if not st.session_state.records:
        st.info("No transaction records found in ledger.")
    else:
        for i, r in enumerate(list(st.session_state.records)):
            rtype = r.get("type", "material")
            with st.expander(f"{'📦' if rtype == 'material' else '▤' if rtype == 'expense' else '♨'}  {r.get('name','ENTRY')}  •  PHP {float(r.get('amount',0)):,.2f}", expanded=False):
                with st.form(key=f"edit_construction_{r.get('id', i)}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        edit_name = st.text_input("Material / Entry Name", value=str(r.get("name", "")), key=f"edit_name_{i}")
                        edit_price = st.number_input("Unit Price / Amount", min_value=0.01, value=float(r.get("price", r.get("amount", 0)) or 0.01), step=0.01, key=f"edit_price_{i}")
                    with c2:
                        edit_qty = st.number_input("Quantity", min_value=1, value=int(r.get("qty", 1) or 1), step=1, key=f"edit_qty_{i}")
                        edit_delivery = st.number_input("Delivery", min_value=0.0, value=float(r.get("delivery", 0) or 0), step=0.01, key=f"edit_delivery_{i}")
                    edit_sender = st.selectbox("Sender", ["Garr", "Aily"], index=0 if r.get("sender", "Garr") == "Garr" else 1, key=f"edit_sender_{i}")
                    save_col, delete_col = st.columns(2)
                    with save_col:
                        save_edit = st.form_submit_button("💾 SAVE CHANGES", use_container_width=True)
                    with delete_col:
                        delete_edit = st.form_submit_button("❌ DELETE ENTRY", use_container_width=True)
                    if save_edit:
                        if update_material_record(i, edit_name, edit_price, edit_qty, edit_delivery, edit_sender):
                            st.success("Ledger entry updated. Export will use the new values.")
                            st.rerun()
                        else:
                            st.error("Please enter a valid name, price, and quantity.")
                    if delete_edit:
                        st.session_state.records.pop(i)
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
    st.caption("You can now re-edit worker names, roles, days/points, cash advances, and payroll expenses before exporting.")
    st.markdown("### Labor Records")
    if not st.session_state.labor_records:
        st.info("No labor records.")
    else:
        for i, r in enumerate(list(st.session_state.labor_records)):
            role_disp = r.get('role', 'Labor')
            gross_disp = float(r.get('gross_pay', float(r.get('days', 0) or 0) * float(r.get('rate', 0) or 0)))
            with st.expander(f"👷  {r.get('name','WORKER')}  •  {role_disp}  •  {float(r.get('days',0) or 0):.1f} day(s)  •  PHP {float(r.get('net',0) or 0):,.2f}", expanded=False):
                with st.form(key=f"edit_labor_{i}"):
                    l1, l2 = st.columns(2)
                    with l1:
                        edit_labor_name = st.text_input("Worker Name", value=str(r.get("name", "")), key=f"edit_labor_name_{i}")
                        edit_role = st.selectbox("Role", ["Labor", "Skill", "Forman"], index=["Labor", "Skill", "Forman"].index(role_disp) if role_disp in ["Labor", "Skill", "Forman"] else 0, key=f"edit_role_{i}")
                    with l2:
                        edit_days = st.number_input("Worked Days / Point", min_value=0.1, value=float(r.get("days", 0.1) or 0.1), step=0.1, key=f"edit_days_{i}")
                        edit_ca = st.number_input("Cash Advance (C.A.)", min_value=0.0, value=float(r.get("ca", 0) or 0), step=0.01, key=f"edit_ca_{i}")
                    preview_gross, _, _ = calculate_labor_pay(float(edit_days), edit_role)
                    st.info(f"Preview → Gross: PHP {preview_gross:,.2f}  |  C.A.: PHP {float(edit_ca):,.2f}  |  Net: PHP {preview_gross-float(edit_ca):,.2f}")
                    save_col, delete_col = st.columns(2)
                    with save_col:
                        save_labor = st.form_submit_button("💾 SAVE LABOR CHANGES", use_container_width=True)
                    with delete_col:
                        delete_labor = st.form_submit_button("❌ DELETE LABOR ENTRY", use_container_width=True)
                    if save_labor:
                        if update_labor_record(i, edit_labor_name, edit_role, edit_days, edit_ca):
                            st.success("Labor record updated. Payroll receipt will use the new values.")
                            st.rerun()
                        else:
                            st.error("Please enter a valid worker name and days.")
                    if delete_labor:
                        st.session_state.labor_records.pop(i)
                        persist_state()
                        st.rerun()

    st.markdown("<div class='sidebar-gap'></div>", unsafe_allow_html=True)
    st.markdown("### Payroll Expenses")
    if not st.session_state.payroll_expenses:
        st.info("No payroll expenses.")
    else:
        for i, e in enumerate(list(st.session_state.payroll_expenses)):
            with st.expander(f"▤  {e.get('item','EXPENSE')}  •  PHP {float(e.get('price',0) or 0):,.2f}", expanded=False):
                with st.form(key=f"edit_pay_exp_{i}"):
                    edit_item = st.text_input("Expense Description", value=str(e.get("item", "")), key=f"edit_pay_item_{i}")
                    edit_pay_price = st.number_input("Amount", min_value=0.01, value=float(e.get("price", 0.01) or 0.01), step=0.01, key=f"edit_pay_price_{i}")
                    save_col, delete_col = st.columns(2)
                    with save_col:
                        save_pay_exp = st.form_submit_button("💾 SAVE EXPENSE CHANGES", use_container_width=True)
                    with delete_col:
                        delete_pay_exp = st.form_submit_button("❌ DELETE PAYROLL EXPENSE", use_container_width=True)
                    if save_pay_exp:
                        if update_payroll_expense(i, edit_item, edit_pay_price):
                            st.success("Payroll expense updated.")
                            st.rerun()
                        else:
                            st.error("Please enter a valid description and amount.")
                    if delete_pay_exp:
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