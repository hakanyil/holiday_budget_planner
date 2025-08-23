# 🏖️ Holiday Budget Planner

**Holiday Budget Planner** is a Python-based **desktop application** built with **Tkinter** and **Matplotlib** to manage shared expenses during trips.  
Track expenses, visualize spending, calculate balances, and generate reports — all in one place!

---

## ✨ Features

### **Core Functionalities**
- 🧾 **Expense Tracking** – Add expenses with payer, amount, and beneficiaries.
- ⚖️ **Automatic Cost Splitting** – Uses **half-up rounding** for accurate cost distribution.
- 📊 **Debt & Balance Calculation** – Generates a **debt matrix** and **net balances**.
- 💸 **Smart Settlement Suggestions** – Greedy optimization minimizes required transactions.
- 🔎 **Advanced Search & Filtering** – Filter expenses by **payer**, **beneficiary**, or **amount range**.

### **Data Visualization**
- 📈 **Total Spending Per Person**
- 📉 **Net Balances Overview**
- 🥧 **Spending Share Pie Chart**

### **Comprehensive Reporting**
- 📑 **Summary Report**:
  - Total & average spending  
  - Biggest & smallest spenders  
  - Top creditors & debtors  
- 📂 **Export Options**:  
  - **TXT**: Human-readable report  
  - **CSV**: Raw expense data for further analysis

---

## 🚀 Installation

### **1. Clone the Repository**
```bash
git clone https://github.com/hakanyil/holiday_budget_planner.git
cd holiday-budget-planner
```

### **2. Create a Virtual Environment**
```bash
python -m venv .venv
```

### **3. Activate the Virtual Environment**
**Windows (PowerShell):**
```bash
.venv\Scripts\Activate
```
**macOS / Linux:**
```bash
source .venv/bin/activate
```

### **4. Install Dependencies**
```bash
pip install -r requirements.txt
```

---

## 🖥️ Usage

Start the application:

```bash
python expense_app.py
```

Once launched, you can:
- Add expenses
- View the debt matrix
- Filter expenses instantly
- See interactive charts
- Export reports and raw data

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **UI Framework:** Tkinter
- **Visualization:** Matplotlib
- **Storage:** JSON

---

## 🧩 Project Structure

```
holiday_budget_planner/
├── expense_app.py        # Main application file
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
└── expenses.json         # Stored expense data
```

---

## 💡 Future Improvements
- 🌐 **Multi-currency support** (real-time exchange rates)
- ☁️ **Cloud synchronization**
- 📅 **Expense categories & timeline filters**
- 🤖 **AI-powered budget recommendations**


