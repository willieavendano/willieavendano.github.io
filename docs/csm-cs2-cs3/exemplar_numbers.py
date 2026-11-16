"""Canonical numbers for the CS II / CS III Level-4 exemplars (fictional student Camila Ortiz).
Every exemplar workbook and deck must match exemplar-numbers.json to the cent."""
import json

def r2(x): return round(x + 1e-9, 2)

# ---------- Persona (fictional; same rate model as the class credit profiles)
persona = dict(name="Camila Ortiz", age=25, job="Civil engineer (EIT)", employment="W-2 employee",
               salary=64000, score=726, tier="Prime", history_yrs=6, utilization=0.18, late_payments=0, open_accounts=5)
ANCH = [(630, 9.71), (720, 6.15), (800, 4.41)]
def tier_rate(s):
    for (a, ra), (b, rb) in zip(ANCH, ANCH[1:]):
        if a <= s <= b: return ra + (rb - ra) * (s - a) / (b - a)
ADJ = {36: -0.65, 48: -0.55, 60: -0.40, 72: -0.05, 84: 0.40}
base = round(tier_rate(persona["score"]), 2)
apr = {n: round(base + ADJ[n], 2) for n in ADJ}               # percent

# ---------- CS II: the car (illustrative listing, new car → new-car rates apply)
car = dict(year=2026, make="Toyota", model="RAV4", trim="LE Hybrid", condition="New",
           listed_price=33950.00, dealer_fee=999.00, title_registration=400.00,
           fl_sales_tax_rate=0.06, surtax_rate=0.01, surtax_cap=5000.00,
           mpg_combined=39, miles_per_month=1000, gas_price=3.40,
           insurance_month=310.00, maintenance_month=50.00, sunpass_month=40.00,
           down_payment=5000.00, chosen_term=60)
car["state_sales_tax"] = r2(car["listed_price"] * car["fl_sales_tax_rate"])
car["county_surtax"] = r2(min(car["listed_price"], car["surtax_cap"]) * car["surtax_rate"])
car["out_the_door"] = r2(car["listed_price"] + car["state_sales_tax"] + car["county_surtax"] + car["dealer_fee"] + car["title_registration"])
car["financed"] = r2(car["out_the_door"] - car["down_payment"])
car["fuel_month"] = r2(car["miles_per_month"] / car["mpg_combined"] * car["gas_price"])
car["ownership_month"] = r2(car["insurance_month"] + car["fuel_month"] + car["maintenance_month"] + car["sunpass_month"])

def pmt(P, apr_pct, n):
    i = apr_pct / 1200
    return P * i / (1 - (1 + i) ** -n)

gross_month = persona["salary"] / 12
loans = {}
for n in ADJ:
    p = pmt(car["financed"], apr[n], n)
    loans[n] = dict(apr_pct=apr[n], payment=r2(p), total_paid=r2(p * n), total_interest=r2(p * n - car["financed"]),
                    total_cost_of_car=r2(car["down_payment"] + p * n), share_of_gross=round(p / gross_month, 4))
# Amortization check for chosen term (full precision; display rounding only)
n = car["chosen_term"]; i = apr[n] / 1200; p = pmt(car["financed"], apr[n], n); bal = car["financed"]
m1_int = bal * i; m1_prin = p - m1_int
cross = None; b = bal
for k in range(1, n + 1):
    it = b * i; pr = p - it; b -= pr
    if cross is None and pr > it: cross = k
amort = dict(month1_interest=r2(m1_int), month1_principal=r2(m1_prin), final_balance=r2(b), first_month_principal_exceeds_interest=cross)

# ---------- CS III: the budget (2026 federal tax, single, standard deduction; FL no state income tax)
STD = 16100.0; BR = [(12400, .10), (50400, .12), (105700, .22), (201775, .24)]
taxable = max(0, persona["salary"] - STD)
fed = 0.0; lo = 0
for hi, rate in BR:
    if taxable > lo: fed += (min(taxable, hi) - lo) * rate
    lo = hi
fica = persona["salary"] * 0.0765
takehome_year = persona["salary"] - fed - fica
takehome_month = r2(takehome_year / 12)

apt = dict(neighborhood="Little Havana", unit="2-bedroom, 1-bath apartment", listed_rent=2600.00, roommates=1,
           rent_share=1300.00, commute_minutes=15, lease_months=12)
car_payment = loans[60]["payment"]
expenses = [  # (category, amount, Fixed/Variable, source note)
    ("Rent (my half of a 2BR)", apt["rent_share"], "Fixed", "Listing ÷ 2 roommates"),
    ("Renter's insurance", 18.00, "Fixed", "Published FL average, assumption"),
    ("Electric (FPL), my half", 85.00, "Variable", "FPL bill estimate, assumption"),
    ("Internet, my half", 40.00, "Fixed", "Provider plan ÷ 2"),
    ("Phone", 55.00, "Fixed", "Carrier plan"),
    ("Car payment (5 yr)", car_payment, "Fixed", "Linked from CS II"),
    ("Car insurance", car["insurance_month"], "Fixed", "Linked from CS II"),
    ("Gas", car["fuel_month"], "Variable", "Linked from CS II"),
    ("Car maintenance", car["maintenance_month"], "Variable", "Linked from CS II"),
    ("Tolls (SunPass)", car["sunpass_month"], "Variable", "Linked from CS II"),
    ("Health insurance (employee share)", 140.00, "Fixed", "Employer plan, assumption"),
    ("Groceries", 380.00, "Variable", "USDA moderate food plan, assumption"),
    ("Eating out / cafecitos", 160.00, "Variable", "Own estimate"),
    ("Personal care & clothing", 80.00, "Variable", "Own estimate"),
    ("Subscriptions", 30.00, "Fixed", "Own estimate"),
    ("Gym", 35.00, "Fixed", "Gym plan"),
    ("Entertainment", 100.00, "Variable", "Own estimate"),
]
exp_total = r2(sum(e[1] for e in expenses))
savings_month = r2(takehome_month - exp_total)
savings_rate = round(savings_month / takehome_month, 4)
emergency_fund_start = 3000.00

def months_to_zero(fund, monthly_change):
    if monthly_change >= 0: return None
    m = 0; f = fund
    while f > 0 and m < 600:
        f += monthly_change; m += 1
    return m
scen = {}
# A: Hurricane season — one-time $1,000 comprehensive deductible + $150 supplies, month 1
scen["Hurricane deductible (one-time $1,150)"] = dict(month1_change=r2(savings_month - 1150), ongoing=savings_month)
# B: Rent hike 8% at renewal (rent share +104)
hike = r2(apt["rent_share"] * 0.08)
scen["Rent +8% at renewal"] = dict(ongoing=r2(savings_month - hike))
# C: Breaks the budget — hours cut: take-home falls 30% for 6 months
cut_net = r2(takehome_month * 0.70)
cut_change = r2(cut_net - exp_total)
scen["Hours cut 30% (breaks the budget)"] = dict(ongoing=cut_change, months_to_zero=months_to_zero(emergency_fund_start, cut_change))
# The fix for C: cut entertainment, eating out to 60, gym pause, subscriptions → savings
fix_cuts = {"Eating out / cafecitos": 100.00, "Entertainment": 70.00, "Gym": 35.00, "Subscriptions": 20.00}
fix_change = r2(cut_change + sum(fix_cuts.values()))
scen["Hours cut + my fix"] = dict(ongoing=fix_change, cuts=fix_cuts, months_to_zero=months_to_zero(emergency_fund_start, fix_change))
# Car decision comparison: same budget with 7-yr loan
scen["Same budget, 7-year loan"] = dict(ongoing=r2(savings_month + car_payment - loans[84]["payment"]),
                                         extra_interest_vs_5yr=r2(loans[84]["total_interest"] - loans[60]["total_interest"]))

out = dict(persona=persona, apr_by_term_pct=apr, car=car, loans=loans, amortization_60=amort,
           budget=dict(tax_year=2026, standard_deduction=STD, brackets=BR, taxable_income=r2(taxable), federal_tax=r2(fed),
                       fica=r2(fica), takehome_year=r2(takehome_year), takehome_month=takehome_month, gross_month=r2(gross_month),
                       apartment=apt, rent_share_of_gross=round(apt["rent_share"] / gross_month, 4),
                       expenses=[dict(category=c, amount=a, kind=k, source=s) for c, a, k, s in expenses],
                       expenses_total=exp_total, savings_month=savings_month, savings_rate=savings_rate,
                       emergency_fund_start=emergency_fund_start, scenarios=scen))
json.dump(out, open("exemplar-numbers.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: out[k] for k in ("apr_by_term_pct",)}, indent=0))
print("OTD", car["out_the_door"], "financed", car["financed"], "fuel", car["fuel_month"], "own", car["ownership_month"])
for n_, L in loans.items(): print(n_, L)
print(amort)
b = out["budget"]; print("tax", b["federal_tax"], "fica", b["fica"], "net/mo", b["takehome_month"], "exp", b["expenses_total"], "save", b["savings_month"], b["savings_rate"])
for k, v in scen.items(): print(k, v)
