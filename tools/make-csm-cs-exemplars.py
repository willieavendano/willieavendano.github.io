#!/usr/bin/env python3
"""Build the fictional CS II/III exemplars. Run --verify to audit existing files.

No spreadsheet calculation engine is required: independent arithmetic validates the
canonical outputs; the saved formulas are evaluated by a small, separate interpreter.
Only the two requested xlsx files are written. Source inputs: exemplar-numbers.json.
"""
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import re
import zipfile
from openpyxl import Workbook, load_workbook
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule
from openpyxl.workbook.properties import CalcProperties
from openpyxl.formula.tokenizer import Tokenizer
from openpyxl.utils import get_column_letter, range_boundaries

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'docs/csm-cs2-cs3/exemplar-numbers.json').read_text())
OUT = ROOT / 'computer-science-math/resources'
MONEY = '$#,##0.00;[Red]($#,##0.00);$0.00'
PCT = '0.0%'
BLUE = '0E406A'
SOURCE = 'Teacher-issued credit profile (fictional exemplar)'
# Plain-English labels shown in column A; the internal keys stay the same so refs and checks are unchanged.
DISPLAY = {
    'name': 'Name', 'age': 'Age', 'job': 'Job', 'employment': 'Employment type', 'salary': 'Gross salary ($/yr)',
    'score': 'Credit score', 'tier': 'Credit tier', 'history_yrs': 'Credit history (years)',
    'utilization': 'Card utilization', 'late_payments': 'Late payments (last 2 yrs)', 'open_accounts': 'Open accounts',
    'year': 'Model year', 'make': 'Make', 'model': 'Model', 'trim': 'Trim', 'condition': 'New or used',
    'listed_price': 'Listed price ($)', 'fl_sales_tax_rate': 'Florida sales tax rate',
    'surtax_rate': 'Miami-Dade surtax rate', 'surtax_cap': 'Surtax applies to the first ($)',
    'dealer_fee': 'Dealer fee ($)', 'title_registration': 'Title & registration ($)', 'down_payment': 'Down payment ($)',
    'state_sales_tax': 'Florida sales tax ($)', 'county_surtax': 'Miami-Dade surtax ($)',
    'out_the_door': 'Out-the-door price ($)', 'financed': 'Amount financed ($)',
    'OTD ceiling': 'Out-the-door ceiling ($)', 'Minimum down': 'Minimum down payment ($)',
    'OTD within ceiling': 'Check: out-the-door ≤ ceiling', 'Down payment meets floor': 'Check: down payment ≥ minimum',
    'mpg_combined': 'Combined mpg', 'miles_per_month': 'Miles per month', 'gas_price': 'Gas price ($/gal)',
    'insurance_month': 'Insurance ($/mo)', 'maintenance_month': 'Maintenance ($/mo)', 'sunpass_month': 'Tolls, SunPass ($/mo)',
    'fuel_month': 'Fuel ($/mo)', 'ownership_month': 'Cost to own ($/mo)',
    'neighborhood': 'Neighborhood', 'unit': 'Unit', 'listed_rent': 'Listed rent ($/mo)', 'roommates': 'Roommates',
    'commute_minutes': 'Commute (minutes)', 'lease_months': 'Lease length (months)',
}
SOURCES = {
    'year': 'Dealer listing (illustrative for this exemplar)', 'make': 'Dealer listing (illustrative for this exemplar)',
    'model': 'Dealer listing (illustrative for this exemplar)', 'trim': 'Dealer listing (illustrative for this exemplar)',
    'condition': 'Dealer listing (illustrative). New car, so the profile rates apply as-is',
    'listed_price': 'Dealer listing (illustrative for this exemplar)',
    'dealer_fee': 'Assumption: typical Florida dealer fee (Florida sets no cap)',
    'title_registration': 'Assumption: Florida title + first registration estimate',
    'down_payment': 'My choice, above the $4,000 class minimum',
    'OTD ceiling': 'Class rule (Cornerstone II spec)', 'Minimum down': 'Class rule (Cornerstone II spec)',
    'miles_per_month': 'Assumption: weekday commute + weekends', 'gas_price': 'Assumption: Miami regular unleaded',
    'maintenance_month': 'Assumption: new-car maintenance reserve', 'sunpass_month': 'Assumption: SunPass tolls on my commute',
    'neighborhood': 'Apartment listing (illustrative for this exemplar)', 'unit': 'Apartment listing (illustrative for this exemplar)',
    'listed_rent': 'Apartment listing (illustrative for this exemplar)', 'roommates': 'My choice: one roommate',
    'commute_minutes': 'Assumption: drive to work at rush hour', 'lease_months': 'Listing terms (illustrative)',
}
IRS = 'IRS Rev. Proc. 2025-32, single filer: https://www.irs.gov/irb/2025-45_IRB'


def rounded(x, n=2):
    return round(x + 1e-9, n)


def payment(principal, annual, months):
    r = annual / 12
    return principal / months if r == 0 else principal * r / (1 - (1 + r) ** -months)


class Builder:
    def __init__(self):
        self.w = Workbook()
        self.w.remove(self.w.active)
        self.rows = {}
        self.targets = {}
        self.expected = {}
        self.w.calculation = CalcProperties(calcId=191029, fullCalcOnLoad=True, forceFullCalc=True, calcMode='auto')
        self.w.properties.creator = 'CS Math — fictional exemplar'
        self.w.properties.title = 'Camila Ortiz | Level 4 — Advanced'

    def sheet(self, name, title, widths=(43, 23, 24, 72)):
        s = self.w.create_sheet(name)
        s.sheet_view.showGridLines = False
        s.sheet_view.zoomScale = 90
        s.sheet_properties.pageSetUpPr.fitToPage = True
        s.sheet_properties.tabColor = BLUE
        s.freeze_panes = 'B5'
        s.page_setup.orientation = 'landscape'
        s.page_setup.paperSize = s.PAPERSIZE_A4
        s.page_setup.fitToWidth = 1
        s.page_setup.fitToHeight = 0
        s.print_options.horizontalCentered = True
        s.oddFooter.center.text = 'CS Math | Fictional exemplar | Page &P'
        for i, width in enumerate(widths, 1):
            s.column_dimensions[get_column_letter(i)].width = width
        s.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(widths))
        s['A1'] = title
        s['A1'].font = Font(name='Aptos', size=17, bold=True, color=BLUE)
        s.row_dimensions[1].height = 33
        s.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(widths))
        s['A2'] = 'Camila Ortiz • fictional • 4.0 Advanced | Blue + pale fill = editable input; black = formula; ≈ means display rounding.'
        s['A2'].font = Font(name='Aptos', size=10, italic=True, color='55504A')
        s['A2'].alignment = Alignment(wrap_text=True)
        s.row_dimensions[2].height = 32
        self.rows[name] = {}
        return s

    def cell(self, s, row, col, value, fmt=None):
        c = s.cell(row, col, value)
        c.font = Font(name='Aptos', size=11, color='111111' if c.data_type == 'f' else ('0071CE' if col > 1 else BLUE))
        c.alignment = Alignment(vertical='center', wrap_text=True)
        if c.data_type != 'f' and col > 1:
            c.fill = PatternFill('solid', fgColor='EAF3FB')
        if fmt:
            c.number_format = fmt
        s.row_dimensions[row].height = max(s.row_dimensions[row].height or 25, 29)
        return c

    def row(self, s, key, value, fmt=None, source='Formula — follows labelled inputs'):
        r = max(s.max_row + 1, 5)
        self.rows[s.title][key] = r
        self.cell(s, r, 1, DISPLAY.get(key, key))
        self.cell(s, r, 2, value, fmt)
        self.cell(s, r, 4, SOURCES.get(key, source) if source == SOURCE else source)
        s.row_dimensions[r].height = 44
        return r

    def ref(self, sheet, key, col=2):
        r = self.rows[sheet][key]
        address = f'${get_column_letter(col)}${r}'
        self.targets[(sheet, address)] = (self.w[sheet].cell(r, 1).value, r)
        return f"'{sheet}'!{address}"

    def local(self, s, key, col=2):
        return f'${get_column_letter(col)}${self.rows[s.title][key]}'

    def headers(self, s, r, labels):
        for i, label in enumerate(labels, 1):
            c = self.cell(s, r, i, label)
            c.fill = PatternFill('solid', fgColor=BLUE)
            c.font = Font(name='Aptos', color='FFFFFF', bold=True, size=11)
        s.row_dimensions[r].height = 35

    def note(self, s, label, text):
        r = self.row(s, label, text, source='')
        s.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        s.cell(r, 2).fill = PatternFill('solid', fgColor='F3EFE7')
        s.cell(r, 2).font = Font(name='Aptos', size=11, color='111111' if s.cell(r, 2).data_type == 'f' else '55504A')
        s.row_dimensions[r].height = max(54, 16 * math.ceil(len(text) / 105))

    def expect(self, sheet, key, val, digits=2, col=2):
        self.expected[(sheet, self.ref(sheet, key, col).split('!')[1])] = (val, digits)

    def chart(self, s, first, last, cols, anchor, title, ytitle='Dollars', kind='line', labels=1):
        ch = BarChart() if kind == 'bar' else LineChart()
        ch.title, ch.y_axis.title, ch.x_axis.title = title, ytitle, 'Category' if kind == 'bar' else 'Month'
        ch.y_axis.scaling.min = 0
        ch.height, ch.width = 10, 22
        ch.display_blanks = 'gap'
        for col in cols:
            ch.add_data(Reference(s, min_col=col, min_row=first-1, max_row=last), titles_from_data=True)
        ch.set_categories(Reference(s, min_col=labels, min_row=first, max_row=last))
        s.add_chart(ch, anchor)

    def build(self, cs3=False):
        p, c, b = DATA['persona'], DATA['car'], DATA['budget']
        s = self.sheet('READ ME', 'The workbook is the work | Cornerstone II' + (' + III' if cs3 else ''))
        self.note(s, 'What this is', 'A finished Level 4 (4.0 Advanced) model by fictional Camila Ortiz. All people and listings are illustrative. The grade is the average of rubric criteria to one decimal, never points.')
        self.note(s, 'Navigate CS II', 'Profile & Car → Loan Options → Amortization → Cost to Own → Recommendation. Change a blue input, then trace formulas. The chosen-term selector is on Loan Options. Loan inputs and the schedule follow the familiar bridge layout: opening, interest, payment, principal, closing.')
        self.note(s, 'Illustrative listings', 'No real listing URL or dealer photo is implied. The car and apartment are illustrative Miami-Dade listings. Your submitted workbook links a real listing, dates it and includes a screenshot. Exemplar record date is the model preparation date, not evidence of a market search.')
        for label, body in [
            ('Model Correctness', 'Five payments, totals and a selectable 84-row amortization build reconcile. Zero-rate loans work. CS III links the car model, computes progressive tax, and models cash flow and runway.'),
            ('Formula Honesty', 'No typed answers: PMT, MIN surtax cap, SUM, SUMIF, INDEX/MATCH and TEXT show their work. Loan totals retain full precision; budget payment and fuel are rounded to cents at the monthly cash boundary.'),
            ('Data Structure', 'One labelled input per assumption, stable row labels, sources beside inputs, separate builds, freeze panes, consistent currency formats and native charts with labelled axes and dollars from zero.'),
            ('Sources & Assumptions', 'Class inputs are distinguished from verified publications. Listing placeholders are honest. Insurance, fuel and tax limitations are stated, so a reader can replace uncertain inputs.'),
        ]:
            self.note(s, 'What makes this a 4: ' + label, body)
        self.note(s, 'Precision & recalculation', 'Displayed currency is rounded to cents (≈); formulas keep full precision. Percentages display one decimal. Model assumptions: equal monthly periods, on-time payments, no finance fees; the profile APR is used as the contract rate.')
        if cs3:
            self.note(s, 'Navigate CS III / midterm', 'Continue in the SAME workbook: Income & Tax → Housing → Budget → Scenarios. Car rows link directly to CS II. Baseline checkpoint Dec 3; scenarios Dec 10; workbook + slides due Dec 15, 2026 at 8:00 AM. Four-minute talk plus live defense.')
            self.note(s, 'Scenario assumptions', 'Each scenario changes one thing: a hurricane bill, a rent increase, hours cut, a one-time bonus (good news) and a 7-year loan. Hours cut means take-home falls 30% (taxes not rebuilt). The fix cuts four expenses; it buys time but the month is still negative. Fund charts stop at $0.')
        s = self.sheet('Profile & Car', 'Profile & Car | sources beside every assumption')
        for k, v in p.items():
            self.row(s, k, v, MONEY if k == 'salary' else ('0%' if k == 'utilization' else None), SOURCE)
        self.row(s, 'Gross monthly income', f'={self.local(s,"salary")}/12', MONEY)
        for key in ['year','make','model','trim','condition']:
            self.row(s, key, c[key], source=SOURCE)
        self.row(s, 'Listing URL', 'illustrative listing — your workbook links the real one', source='Illustrative for this exemplar. Your workbook links the real Miami-Dade listing')
        self.row(s, 'Date viewed / prepared', dt.date(2026,11,16), 'mmm d, yyyy', 'Illustrative record preparation date; no actual viewing claimed')
        self.row(s, 'Mileage', 0, '0', 'Illustrative new-car odometer assumption')
        for k in ['listed_price','fl_sales_tax_rate','surtax_rate','surtax_cap','dealer_fee','title_registration','down_payment']:
            src = SOURCE
            if k in ['fl_sales_tax_rate','surtax_rate','surtax_cap']:
                src = 'Florida Dept. of Revenue: 6% state tax; county surtax only on the first $5,000 of a single item. https://floridarevenue.com/taxes/taxesfees/Pages/sales_tax.aspx'
            self.row(s, k, c[k], '0%' if k.endswith('rate') else MONEY, src)
        L=lambda k: self.local(s,k)
        self.row(s,'state_sales_tax',f'={L("listed_price")}*{L("fl_sales_tax_rate")}',MONEY)
        self.row(s,'county_surtax',f'=MIN({L("listed_price")},{L("surtax_cap")})*{L("surtax_rate")}',MONEY)
        self.row(s,'out_the_door','='+'+'.join(L(k) for k in ['listed_price','state_sales_tax','county_surtax','dealer_fee','title_registration']),MONEY)
        self.row(s,'financed',f'={L("out_the_door")}-{L("down_payment")}',MONEY)
        self.row(s,'OTD ceiling',40000,MONEY,SOURCE)
        self.row(s,'Minimum down',4000,MONEY,SOURCE)
        self.row(s,'OTD within ceiling',f'={L("out_the_door")}<={L("OTD ceiling")}')
        self.row(s,'Down payment meets floor',f'={L("down_payment")}>={L("Minimum down")}')
        self.row(s,'Used-car APR addition',0.0266,'0.00%', 'Class model: Experian Q2 2026 prime used 8.81% minus new 6.15%; https://www.experian.com/blogs/ask-experian/average-car-loan-interest-rates-by-credit-score/')
        for term, apr in DATA['apr_by_term_pct'].items():
            self.row(s,f'{term}-month new APR',apr/100,'0.00%', 'Fictional class credit profile; term-adjusted model based on Experian Q2 2026; not a lender offer')
        for key in ['state_sales_tax','county_surtax','out_the_door','financed']:
            self.expect(s.title,key,c[key])
        self.expect(s.title,'Gross monthly income',b['gross_month'])
        s = self.sheet('Loan Options','Loan Options | compare full cost, then select a term',(17,18,21,23,22,24,22))
        self.headers(s,4,['Term (months)','APR','Payment ≈','Total paid ≈','Total interest ≈','Total car cost ≈','Payment / gross'])
        loanrows = {}
        financed=self.ref('Profile & Car','financed')
        for r,(term, loan) in enumerate(DATA['loans'].items(),5):
            loanrows[int(term)]=r
            key=f'{term} months'
            self.rows[s.title][key]=r
            self.cell(s,r,1,int(term),'0')
            rate=self.ref('Profile & Car',f'{term}-month new APR')
            cond=self.ref('Profile & Car','condition'); add=self.ref('Profile & Car','Used-car APR addition')
            self.cell(s,r,2,f'={rate}+IF({cond}="Used",{add},0)','0.00%')
            self.cell(s,r,3,f'=IF(B{r}=0,{financed}/A{r},-PMT(B{r}/12,A{r},{financed}))',MONEY)
            self.cell(s,r,4,f'=C{r}*A{r}',MONEY)
            self.cell(s,r,5,f'=D{r}-{financed}',MONEY)
            self.cell(s,r,6,f'=D{r}+{self.ref("Profile & Car","down_payment")}',MONEY)
            self.cell(s,r,7,f'=C{r}/{self.ref("Profile & Car","Gross monthly income")}',PCT)
            for col, field in enumerate(['apr_pct','payment','total_paid','total_interest','total_cost_of_car','share_of_gross'],2):
                self.expect(s.title,key,loan[field]/100 if field=='apr_pct' else loan[field],4 if field in ['apr_pct','share_of_gross'] else 2,col)
        self.row(s,'Chosen term (months)',c['chosen_term'],'0', 'Choose 36, 48, 60, 72 or 84; drives schedule and budget')
        selector=self.local(s,'Chosen term (months)')
        dv=DataValidation(type='list',formula1='"36,48,60,72,84"'); dv.errorTitle='Choose a listed term'; dv.error='Use a term from the menu.'; dv.showErrorMessage=True; dv.errorStyle='stop'; s.add_data_validation(dv); dv.add(s[selector.replace('$','')])
        for key,col,fmt in [('Chosen APR','B','0.00%'),('Chosen payment','C',MONEY),('Chosen total interest','E',MONEY),('Chosen total cost','F',MONEY),('Chosen income share','G',PCT)]:
            self.row(s,key,f'=INDEX({col}5:{col}9,MATCH({selector},A5:A9,0))',fmt)
        for operator,formulas,color in [('lessThan',['0.15'],'D9EAD3'),('between',['0.15','0.20'],'FFF2CC'),('greaterThan',['0.20'],'F4CCCC')]:
            s.conditional_formatting.add('G5:G9',CellIsRule(operator=operator,formula=formulas,fill=PatternFill('solid',fgColor=color)))
        self.note(s,'Affordability guide','<15% comfortable; 15–20% tight; >20% likely declined (class lender guideline). This ratio alone omits rent and ownership. Totals use the unrounded PMT, so displayed payment × term can differ from displayed total.')
        self.make_amort()
        s=self.sheet('Cost to Own','Cost to Own | monthly costs beyond the payment')
        for k in ['mpg_combined','miles_per_month','gas_price','insurance_month','maintenance_month','sunpass_month']:
            src=SOURCE
            if k=='mpg_combined': src='Combined mpg for this trim (fueleconomy.gov): https://www.fueleconomy.gov/feg/findacar.shtml'
            if k=='insurance_month': src='Assumption: full coverage, age 25, Miami, informed by published Florida averages (Bankrate); not a personal quote. https://www.bankrate.com/insurance/car/average-cost-of-car-insurance-in-florida/'
            self.row(s,k,c[k], '0' if k in ['mpg_combined','miles_per_month'] else MONEY,src)
            if k=='insurance_month': s.row_dimensions[self.rows[s.title][k]].height=82
        self.row(s,'fuel_month',f'=ROUND({self.local(s,"miles_per_month")}/{self.local(s,"mpg_combined")}*{self.local(s,"gas_price")},2)',MONEY)
        self.row(s,'ownership_month','='+'+'.join(self.local(s,k) for k in ['insurance_month','fuel_month','maintenance_month','sunpass_month']),MONEY)
        self.row(s,'Payment + ownership',f'={self.ref("Loan Options","Chosen payment")}+{self.local(s,"ownership_month")}',MONEY)
        self.note(s,'Limitation','Insurance is a class-model assumption, never a personal quote. Mileage, mpg and gas price are illustrative. Replace each with documented local evidence for your own submission; tolls and maintenance are monthly reserves, not guaranteed bills.')
        for k in ['fuel_month','ownership_month']: self.expect(s.title,k,c[k])
        s=self.sheet('Recommendation','Recommendation | Camila explains her decision')
        q=lambda k:self.ref('Loan Options',k)
        self.note(s,'My choice',f'="I choose "&TEXT({q("Chosen term (months)")}/12,"0")&" years: payment ≈ "&TEXT({q("Chosen payment")},"$#,##0.00")&", "&TEXT({q("Chosen income share")},"0.0%")&" of gross. Total interest ≈ "&TEXT({q("Chosen total interest")},"$#,##0.00")&"; total car cost ≈ "&TEXT({q("Chosen total cost")},"$#,##0.00")&"."')
        self.note(s,'Why five years', 'Five years is the shortest term under about 12% of gross. Four years is affordable on paper but leaves less room when rent and insurance land. A smaller payment does not make the car cheaper; six or seven years add interest and extend negative-equity risk.')
        self.note(s,'Seven-year tradeoff',f'="Seven years frees ≈ "&TEXT({self.ref("Loan Options","60 months",3)}-{self.ref("Loan Options","84 months",3)},"$#,##0.00")&" per month but adds ≈ "&TEXT(ROUND({self.ref("Loan Options","84 months",5)},2)-ROUND({self.ref("Loan Options","60 months",5)},2),"$#,##0.00")&" interest versus five years."')
        self.note(s,'Limitations','Rates are class averages used as the contract rate, not offers. Insurance is a supplied class assumption rather than a verified published average for this driver. Dealer fees, title and registration are estimates. This model omits depreciation and future resale value.')
        if cs3: self.make_budget()
        for sh in self.w:
            sh.print_area=f'A1:{get_column_letter(sh.max_column)}{sh.max_row+28 if sh._charts else sh.max_row}'
        return self

    def make_amort(self):
        s=self.sheet('Amortization','Amortization | selected term, full-precision monthly model',(24,23,22,22,22,23))
        for key,source,fmt in [('Amount financed',('Profile & Car','financed'),MONEY),('Annual rate',('Loan Options','Chosen APR'),'0.00%'),('Term months',('Loan Options','Chosen term (months)'),'0'),('Monthly payment',('Loan Options','Chosen payment'),MONEY),('Total interest',('Loan Options','Chosen total interest'),MONEY)]:
            self.row(s,key,'='+self.ref(*source),fmt)
        a=lambda k:self.local(s,k)
        h=s.max_row+2
        self.headers(s,h,['Month','Opening balance','Interest','Payment','Principal','Closing balance'])
        start=h+1; end=start+83
        for r in range(start,end+1):
            month=r-start+1
            self.cell(s,r,1,f'=IF({month}<={a("Term months")},{month},"")','0')
            opening=a('Amount financed') if r==start else f'F{r-1}'
            for col,expr in [(2,opening),(3,f'B{r}*{a("Annual rate")}/12'),(4,a('Monthly payment')),(5,f'D{r}-C{r}'),(6,f'B{r}-E{r}')]:
                self.cell(s,r,col,f'=IF(A{r}="","",{expr})',MONEY)
        self.row(s,'Final balance ≈ zero',f'=ABS(INDEX(F{start}:F{end},{a("Term months")}))<0.005')
        self.row(s,'Principal sum = financed',f'=ABS(SUM(E{start}:E{end})-{a("Amount financed")})<0.005')
        self.row(s,'Interest sum = loan interest',f'=ABS(SUM(C{start}:C{end})-{a("Total interest")})<0.005')
        self.chart(s,start,end,[6],f'A{end+7}','Balance over the selected loan term')
        for col,key in [(3,'month1_interest'),(5,'month1_principal')]:
            self.expected[(s.title,f'${get_column_letter(col)}${start}')]=(DATA['amortization_60'][key],2)
        self.expected[(s.title,f'$F${start+59}')]=(0,2)
        for key in ['Final balance ≈ zero','Principal sum = financed','Interest sum = loan interest']: self.expect(s.title,key,True,0)
        s.print_title_rows=f'{h}:{h}'
        s.freeze_panes=f'B{start}'
        s.print_area=f'A1:P{end+5}'

    def make_budget(self):
        b=DATA['budget']; a=b['apartment']
        s=self.sheet('Income & Tax','Income & Tax | 2026 single filer, W-2')
        for key,val,fmt in [('Tax year',b['tax_year'],'0'),('Standard deduction',b['standard_deduction'],MONEY),('FICA rate',0.0765,'0.00%'),('Florida tax rate',0,PCT),('Comparison state rate',0.05,PCT)]:
            self.row(s,key,val,fmt,IRS if key in ['Tax year','Standard deduction'] else ('Hypothetical flat state tax, no deductions or credits; not a particular state' if key=='Comparison state rate' else 'Class model; W-2 FICA 7.65%, Florida personal income tax 0%'))
        self.row(s,'Annual gross','='+self.ref('Profile & Car','salary'),MONEY)
        L=lambda k:self.local(s,k)
        self.row(s,'Taxable income',f'=MAX(0,{L("Annual gross")}-{L("Standard deduction")})',MONEY)
        bracket_tax=[]
        for i,(upper,rate) in enumerate(b['brackets'],1):
            self.row(s,f'Bracket {i} ceiling',upper,MONEY,IRS)
            self.row(s,f'Bracket {i} rate',rate,PCT,IRS)
            lower='0' if i==1 else L(f'Bracket {i-1} ceiling')
            self.row(s,f'Bracket {i} tax',f'=MAX(0,MIN({L("Taxable income")},{L(f"Bracket {i} ceiling")})-{lower})*{L(f"Bracket {i} rate")}',MONEY)
            bracket_tax.append(L(f'Bracket {i} tax'))
        self.row(s,'Federal tax','='+'+'.join(bracket_tax),MONEY)
        self.row(s,'FICA',f'={L("Annual gross")}*{L("FICA rate")}',MONEY)
        self.row(s,'Florida tax',f'={L("Annual gross")}*{L("Florida tax rate")}',MONEY)
        self.row(s,'Take-home annual',f'={L("Annual gross")}-{L("Federal tax")}-{L("FICA")}-{L("Florida tax")}',MONEY)
        self.row(s,'Take-home monthly',f'=ROUND({L("Take-home annual")}/12,2)',MONEY)
        self.row(s,'Florida advantage / month',f'={L("Annual gross")}*{L("Comparison state rate")}/12',MONEY)
        self.row(s,'Within tax table coverage',f'={L("Taxable income")}<={L("Bracket 4 ceiling")}')
        self.note(s,'Tax scope','W-2 employee, single, standard deduction, no credits or pre-tax benefits. FICA model assumes wages below the Social Security cap. Table covers taxable income through $201,775; extend before modelling higher income. Self-employment requires a different tax build (not Camila). Florida advantage compares an explicitly hypothetical 5% flat tax on gross.')
        for key,jkey in [('Taxable income','taxable_income'),('Federal tax','federal_tax'),('FICA','fica'),('Take-home annual','takehome_year'),('Take-home monthly','takehome_month')]: self.expect(s.title,key,b[jkey])
        s=self.sheet('Housing','Housing | illustrative Miami-Dade apartment')
        for key in ['neighborhood','unit','listed_rent','roommates','commute_minutes','lease_months']:
            self.row(s,key,a[key],MONEY if key=='listed_rent' else None,SOURCE)
        self.row(s,'Listing URL','illustrative listing — your workbook links the real one',source='Illustrative for this exemplar. Your workbook links the real Miami-Dade listing')
        self.row(s,'Date viewed / prepared',dt.date(2026,11,16),'mmm d, yyyy','Illustrative record preparation date')
        L=lambda k:self.local(s,k)
        self.row(s,'People sharing',f'={L("roommates")}+1','0')
        self.row(s,'Rent share',f'={L("listed_rent")}/{L("People sharing")}',MONEY, 'Equal split between Camila and one roommate (2 people total)')
        self.row(s,'Share of gross',f'={L("Rent share")}/{self.ref("Profile & Car","Gross monthly income")}',PCT)
        self.row(s,'Housing guideline',0.30,PCT,'Class guideline: housing at most 30% of gross')
        self.row(s,'Within guideline',f'={L("Share of gross")}<={L("Housing guideline")}')
        self.expect(s.title,'Rent share',a['rent_share']); self.expect(s.title,'Share of gross',b['rent_share_of_gross'],4)
        s=self.sheet('Budget','Budget | linked CS II costs → monthly cash flow',(43,21,19,72))
        self.headers(s,4,['Category','Monthly amount ≈','Fixed / Variable','Source or labelled assumption'])
        links={0:('Housing','Rent share'),5:('Loan Options','Chosen payment'),6:('Cost to Own','insurance_month'),7:('Cost to Own','fuel_month'),8:('Cost to Own','maintenance_month'),9:('Cost to Own','sunpass_month')}
        for i,e in enumerate(b['expenses']):
            r=i+5; key=e['category']; self.rows[s.title][key]=r
            self.cell(s,r,1,key)
            val=f'=ROUND({self.ref(*links[i])},2)' if i in links else e['amount']
            self.cell(s,r,2,val,MONEY); self.cell(s,r,3,e['kind'])
            src=e['source']
            if i==0: src='Linked from Housing: rent ÷ 2 people (me + one roommate)'
            elif i not in links: src+=' (illustrative)'
            self.cell(s,r,4,src); s.row_dimensions[r].height=44
            self.expect(s.title,key,e['amount'])
        L=lambda k:self.local(s,k)
        self.row(s,'Fixed total','=SUMIF(C5:C21,"Fixed",B5:B21)',MONEY)
        self.row(s,'Variable total','=SUMIF(C5:C21,"Variable",B5:B21)',MONEY)
        self.row(s,'Total expenses','=SUM(B5:B21)',MONEY)
        self.row(s,'Take-home monthly','='+self.ref('Income & Tax','Take-home monthly'),MONEY)
        self.row(s,'Savings monthly',f'=ROUND({L("Take-home monthly")}-{L("Total expenses")},2)',MONEY)
        self.row(s,'Savings rate',f'=IF({L("Take-home monthly")}=0,0,{L("Savings monthly")}/{L("Take-home monthly")})',PCT)
        self.row(s,'Savings target',0.10,PCT,'Class target: at least 10% of take-home')
        self.row(s,'At least target',f'={L("Savings rate")}>={L("Savings target")}')
        self.row(s,'Target shortfall / month',f'=MAX(0,{L("Take-home monthly")}*{L("Savings target")}-{L("Savings monthly")})',MONEY)
        self.row(s,'Emergency fund start',b['emergency_fund_start'],MONEY,'Class default / assumption')
        for key,jkey in [('Total expenses','expenses_total'),('Savings monthly','savings_month'),('Savings rate','savings_rate')]: self.expect(s.title,key,b[jkey],4 if key=='Savings rate' else 2)
        self.chart(s,5,21,[2],f'A{s.max_row+3}','Where the money goes',kind='bar')
        s=self.sheet('Scenarios','Scenarios | one change per case, then a modelled fix',(40,24,24,24,24,24,24,24))
        inputs=[('Hurricane one-time',1150,MONEY),('Rent increase',0.08,PCT),('Take-home hours cut',0.30,PCT),('Bonus one-time',1000,MONEY)]
        for key,val,fmt in inputs: self.row(s,key,val,fmt,'Scenario assumption (one change per case)')
        cuts=b['scenarios']['Hours cut + my fix']['cuts']; cutrefs=[]
        for category,amount in cuts.items():
            key='Cut: '+category
            self.row(s,key,amount,MONEY,'Fix assumption: reduce this Budget category by this amount')
            cutrefs.append(self.local(s,key))
            self.row(s,'Remaining: '+category,f'={self.ref("Budget",category)}-{self.local(s,key)}',MONEY)
        self.row(s,'Total modelled cuts','=SUM('+','.join(cutrefs)+')',MONEY)
        self.note(s,'How to read','Baseline; hurricane changes one-time spending; rent changes rent share; hours changes take-home; fix adds cuts to hours stress; 7-year case substitutes only the payment; bonus changes one-time income. Hours stress is assumed to persist for runway, rather than end after six months. The fix buys time but does not balance the budget.')
        h=s.max_row+2
        labels=['Metric','Baseline','Hurricane','Rent +8%','Hours −30%','Hours + fix','7-year loan','Bonus (extra)']
        self.headers(s,h,labels)
        metrics=['Take-home monthly','Recurring expenses','Ongoing savings','One-time change','Month 1 savings','Months to zero','Extra loan interest']
        mr={k:h+1+i for i,k in enumerate(metrics)}
        for key,r in mr.items(): self.cell(s,r,1,key); self.rows[s.title][key]=r
        net=self.ref('Budget','Take-home monthly'); exp=self.ref('Budget','Total expenses'); fund=self.ref('Budget','Emergency fund start')
        L=lambda k:self.local(s,k)
        for col in range(2,9):
            letter=get_column_letter(col)
            take=f'ROUND({net}*(1-{L("Take-home hours cut")}),2)' if col in [5,6] else net
            spend=exp
            if col==4: spend+=f'+{self.ref("Housing","Rent share")}*{L("Rent increase")}'
            if col==6: spend+=f'-{L("Total modelled cuts")}'
            if col==7: spend+=f'-ROUND({self.ref("Loan Options","Chosen payment")},2)+ROUND({self.ref("Loan Options","84 months",3)},2)'
            formulas=[take,spend,f'ROUND({letter}{mr["Take-home monthly"]}-{letter}{mr["Recurring expenses"]},2)',f'-{L("Hurricane one-time")}' if col==3 else (L('Bonus one-time') if col==8 else '0'),f'{letter}{mr["Ongoing savings"]}+{letter}{mr["One-time change"]}',f'IF({fund}+{letter}{mr["Month 1 savings"]}<=0,1,IF({letter}{mr["Ongoing savings"]}<0,1+ROUNDUP(({fund}+{letter}{mr["Month 1 savings"]})/-{letter}{mr["Ongoing savings"]},0),"Not depleted"))',f'ROUND({self.ref("Loan Options","84 months",5)},2)-ROUND({self.ref("Loan Options","60 months",5)},2)' if col==7 else '0']
            for key,expr in zip(metrics,formulas): self.cell(s,mr[key],col,'='+expr,'0' if key=='Months to zero' else MONEY)
        cases=list(b['scenarios'].values())
        for case,col in zip(cases,[3,4,5,6,7]):
            for key in ['ongoing','month1_change','months_to_zero','extra_interest_vs_5yr']:
                if key in case:
                    metric={'ongoing':'Ongoing savings','month1_change':'Month 1 savings','months_to_zero':'Months to zero','extra_interest_vs_5yr':'Extra loan interest'}[key]
                    self.expect(s.title,metric,case[key],0 if key=='months_to_zero' else 2,col)
        self.note(s,'My budget breaks',f'="Hours cut: ≈ "&TEXT(E{mr["Ongoing savings"]},"$#,##0.00")&" per month; fund depleted in "&TEXT(E{mr["Months to zero"]},"0")&" months. My cuts buy "&TEXT(F{mr["Months to zero"]}-E{mr["Months to zero"]},"0")&" extra months, but I still need more hours, cheaper housing or another change."')
        start=s.max_row+3
        self.headers(s,start-1,['Month','Baseline fund','Hours-cut fund','Hours + fix fund'])
        for month in range(13):
            r=start+month; self.cell(s,r,1,month,'0')
            for col,casecol in [(2,'B'),(3,'E'),(4,'F')]:
                self.cell(s,r,col,f'=MAX(0,{fund}+A{r}*{casecol}{mr["Ongoing savings"]})',MONEY)
        self.chart(s,start,start+12,[2,3,4],f'A{start+15}','Emergency fund: baseline, stress, fix')
        s.page_setup.paperSize = s.PAPERSIZE_A3
        s.freeze_panes=f'B{h+1}'


class FormulaEvaluator:
    """Small read-only evaluator for the Excel subset authored above; never caches to xlsx.

    PMT is evaluated through the annuity future-value identity, independently of
    the direct present-value payment arithmetic used by the canonical audit.
    IF is lazy, so rows outside the chosen term remain genuinely blank.
    """
    precedence={'=':1,'<>':1,'<':1,'>':1,'<=':1,'>=':1,'&':2,'+':3,'-':3,'*':4,'/':4,'^':5}

    def __init__(self, workbook):
        self.w=workbook
        self.cache={}
        self.visiting=set()

    def cell(self, sheet, address):
        address=address.replace('$','')
        key=(sheet,address)
        if key in self.cache: return self.cache[key]
        assert key not in self.visiting, f'Circular reference: {key}'
        self.visiting.add(key)
        value=self.w[sheet][address].value
        if isinstance(value,str) and value.startswith('='):
            ts=[t for t in Tokenizer(value).items if t.type!='WHITE-SPACE']
            tree,pos=self.parse(ts,0)
            assert pos==len(ts),(value,pos)
            value=self.run(tree,sheet)
        self.visiting.remove(key)
        self.cache[key]=value
        return value

    def parse(self,ts,pos,minimum=0):
        t=ts[pos]; pos+=1
        if t.type=='OPERATOR-PREFIX':
            arg,pos=self.parse(ts,pos,6); node=('unary',t.value,arg)
        elif t.type in ['FUNC','PAREN'] and t.subtype=='OPEN':
            args=[]
            if ts[pos].subtype!='CLOSE':
                while True:
                    arg,pos=self.parse(ts,pos); args.append(arg)
                    if ts[pos].type=='SEP': pos+=1
                    else: break
            assert ts[pos].subtype=='CLOSE'; pos+=1
            node=('func',t.value[:-1].upper(),args) if t.type=='FUNC' else args[0]
        elif t.type=='OPERAND':
            node=(t.subtype,t.value)
        else: raise ValueError((t.type,t.value))
        while pos<len(ts) and ts[pos].type=='OPERATOR-INFIX' and self.precedence[ts[pos].value]>=minimum:
            op=ts[pos].value; pos+=1
            right,pos=self.parse(ts,pos,self.precedence[op]+1)
            node=('op',op,node,right)
        return node,pos

    def run(self,n,sheet):
        kind=n[0]
        if kind=='NUMBER': return float(n[1])
        if kind=='TEXT': return n[1][1:-1].replace('""','"')
        if kind=='LOGICAL': return n[1]=='TRUE'
        if kind=='RANGE':
            ref=n[1]
            target=sheet
            if '!' in ref:
                target,ref=ref.rsplit('!',1); target=target.strip("'").replace("''", "'")
            if ':' not in ref: return self.cell(target,ref)
            lo,top,hi,bottom=range_boundaries(ref.replace('$',''))
            return [self.cell(target,f'{get_column_letter(col)}{row}') for row in range(top,bottom+1) for col in range(lo,hi+1)]
        if kind=='unary':
            v=self.run(n[2],sheet); return -v if n[1]=='-' else v
        if kind=='op':
            a,b=self.run(n[2],sheet),self.run(n[3],sheet); op=n[1]
            if op=='&': return str(a)+str(b)
            if op=='=': return a==b
            if op=='<>': return a!=b
            if op=='<': return a<b
            if op=='>': return a>b
            if op=='<=': return a<=b
            if op=='>=': return a>=b
            if op=='+': return a+b
            if op=='-': return a-b
            if op=='*': return a*b
            if op=='/': return a/b
            if op=='^': return a**b
        if kind=='func':
            fn,args=n[1:]
            if fn=='IF': return self.run(args[1] if self.run(args[0],sheet) else args[2],sheet)
            vals=[self.run(a,sheet) for a in args]
            flat=[v for arg in vals for v in (arg if isinstance(arg,list) else [arg]) if isinstance(v,(float,int))]
            if fn=='SUM': return sum(flat)
            if fn=='MIN': return min(flat)
            if fn=='MAX': return max(flat)
            if fn=='ABS': return abs(vals[0])
            if fn=='ROUND': return rounded(vals[0],int(vals[1]))
            if fn=='ROUNDUP': return math.ceil(vals[0]*10**vals[1])/10**vals[1]
            if fn=='PMT':
                rate,nper,pv=vals
                if not rate: return -pv/nper
                compound=(1+rate)**nper
                return -pv*compound*rate/(compound-1)
            if fn=='MATCH': return vals[1].index(vals[0])+1
            if fn=='INDEX': return vals[0][int(vals[1])-1]
            if fn=='SUMIF': return sum(v for k,v in zip(vals[0],vals[2]) if k==vals[1])
            if fn=='TEXT':
                x,fmt=vals
                if fmt=='0': return f'{x:.0f}'
                if fmt=='0.0%': return f'{x:.1%}'
                if fmt=='$#,##0.00': return f'${x:,.2f}'
            raise ValueError((fn,vals))
        raise ValueError(n)


def independent_audit():
    """Recompute every canonical output from input fields using only plain Python."""
    c,p,b=DATA['car'],DATA['persona'],DATA['budget']
    checked=0
    def check(got,expected,digits=2):
        nonlocal checked
        assert rounded(got,digits)==expected,(got,expected)
        checked+=1
    tax=c['listed_price']*c['fl_sales_tax_rate']
    surtax=min(c['listed_price'],c['surtax_cap'])*c['surtax_rate']
    otd=c['listed_price']+tax+surtax+c['dealer_fee']+c['title_registration']
    financed=otd-c['down_payment']
    fuel=rounded(c['miles_per_month']/c['mpg_combined']*c['gas_price'])
    ownership=fuel+c['insurance_month']+c['maintenance_month']+c['sunpass_month']
    for field,value in [('state_sales_tax',tax),('county_surtax',surtax),('out_the_door',otd),('financed',financed),('fuel_month',fuel),('ownership_month',ownership)]: check(value,c[field])
    gross=p['salary']/12
    pays={}; ints={}
    for term,loan in DATA['loans'].items():
        n=int(term); annual=DATA['apr_by_term_pct'][term]/100
        pay=payment(financed,annual,n); pays[n]=rounded(pay); ints[n]=rounded(pay*n-financed)
        for field,value in [('apr_pct',annual*100),('payment',pay),('total_paid',pay*n),('total_interest',pay*n-financed),('total_cost_of_car',pay*n+c['down_payment']),('share_of_gross',pay/gross)]: check(value,loan[field],4 if field=='share_of_gross' else 2)
        bal=financed; principal_sum=interest_sum=0; cross=None
        for month in range(1,n+1):
            interest=bal*annual/12; principal=pay-interest; bal-=principal
            interest_sum+=interest; principal_sum+=principal
            if principal>interest and cross is None: cross=month
            if n==60 and month==1:
                check(interest,DATA['amortization_60']['month1_interest']); check(principal,DATA['amortization_60']['month1_principal'])
        check(bal,0); check(principal_sum,financed); check(interest_sum,loan['total_interest'])
        if n==60:
            check(bal,DATA['amortization_60']['final_balance']); check(cross,DATA['amortization_60']['first_month_principal_exceeds_interest'])
    # Tax is a progressive band build, not an effective flat tax.
    taxable=max(0,p['salary']-b['standard_deduction']); federal=0; lower=0
    for ceiling,rate in b['brackets']:
        federal+=max(0,min(taxable,ceiling)-lower)*rate; lower=ceiling
    fica=p['salary']*.0765; year=p['salary']-federal-fica; net=rounded(year/12)
    for key,value in [('taxable_income',taxable),('federal_tax',federal),('fica',fica),('takehome_year',year),('takehome_month',net),('gross_month',gross)]: check(value,b[key])
    rent=b['apartment']['listed_rent']/(1+b['apartment']['roommates'])
    check(rent,b['apartment']['rent_share']); check(rent/gross,b['rent_share_of_gross'],4)
    linked={0:rent,5:pays[c['chosen_term']],6:c['insurance_month'],7:fuel,8:c['maintenance_month'],9:c['sunpass_month']}
    amounts=[linked.get(i,e['amount']) for i,e in enumerate(b['expenses'])]
    for value,e in zip(amounts,b['expenses']): check(value,e['amount'])
    total=rounded(sum(amounts)); savings=rounded(net-total)
    check(total,b['expenses_total']); check(savings,b['savings_month']); check(savings/net,b['savings_rate'],4)
    sc=b['scenarios']; vals=list(sc.values())
    check(savings-1150,vals[0]['month1_change']); check(savings,vals[0]['ongoing']); check(savings-rent*.08,vals[1]['ongoing'])
    broken=rounded(rounded(net*.7)-total); fixed=rounded(broken+sum(vals[3]['cuts'].values()))
    for v,case in [(broken,vals[2]),(fixed,vals[3])]:
        check(v,case['ongoing']); check(math.ceil(b['emergency_fund_start']/-v),case['months_to_zero'])
    check(savings+pays[60]-pays[84],vals[4]['ongoing']); check(ints[84]-ints[60],vals[4]['extra_interest_vs_5yr'])
    # Boundary verification: every supported term and zero-rate principal recovery.
    for n in [36,48,60,72,84]: check(payment(financed,0,n)*n,financed)
    print(f'PASS independent Python audit: {checked} canonical / boundary assertions; five schedules reconcile.')


def verify_file(path,builder):
    w=load_workbook(path,data_only=False)
    assert w.calculation.fullCalcOnLoad and w.calculation.forceFullCalc
    assert w.sheetnames==builder.w.sheetnames
    refs=0; formula_count=0
    ev=FormulaEvaluator(w)
    for s in w:
        assert s.freeze_panes
        for row in s:
            for cell in row:
                if cell.data_type!='f': continue
                formula_count+=1
                for token in Tokenizer(cell.value).items:
                    if token.subtype=='RANGE' and '!' in token.value:
                        sheet,addr=token.value.rsplit('!',1); sheet=sheet.strip("'")
                        assert (sheet,addr) in builder.targets,(s.title,cell.coordinate,token.value)
                        label,r=builder.targets[(sheet,addr)]
                        assert w[sheet].cell(r,1).value==label,(sheet,addr,label)
                        assert w[sheet][addr.replace('$','')].value is not None
                        refs+=1
                result=ev.cell(s.title,cell.coordinate)
                assert result is not None,(s.title,cell.coordinate)
    for (sheet,addr),(expected,digits) in builder.expected.items():
        got=ev.cell(sheet,addr)
        assert rounded(got,digits)==rounded(expected,digits),(sheet,addr,got,expected)
    # Exercise all selector values, including the end of the longest schedule,
    # and the zero-rate branch using the actual saved formulas.
    chosenrow=builder.rows['Loan Options']['Chosen term (months)']
    for term in [36,48,60,72,84]:
        w['Loan Options'].cell(chosenrow,2,term)
        trial=FormulaEvaluator(w)
        for key in ['Final balance ≈ zero','Principal sum = financed','Interest sum = loan interest']:
            assert trial.cell('Amortization',builder.local(w['Amortization'],key)) is True
    w['Loan Options'].cell(chosenrow,2,60)
    aprrow=builder.rows['Profile & Car']['60-month new APR']
    original=w['Profile & Car'].cell(aprrow,2).value
    w['Profile & Car'].cell(aprrow,2,0)
    trial=FormulaEvaluator(w)
    assert rounded(trial.cell('Loan Options',builder.local(w['Loan Options'],'Chosen payment')))==540.60
    assert trial.cell('Amortization',builder.local(w['Amortization'],'Final balance ≈ zero')) is True
    w['Profile & Car'].cell(aprrow,2,original)
    if 'Budget' in w:
        # Meaningful live-change checks on a disposable in-memory copy: propagate car
        # payment, fuel, rent and salary through the actual saved formula graph.
        chosen=builder.rows['Loan Options']['Chosen term (months)']
        w['Loan Options'].cell(chosen,2,84)
        changed=FormulaEvaluator(w)
        val=changed.cell('Budget',builder.local(w['Budget'],'Savings monthly'))
        assert rounded(val)==DATA['budget']['scenarios']['Same budget, 7-year loan']['ongoing']
        w['Loan Options'].cell(chosen,2,60)
        rental=builder.rows['Housing']['listed_rent']
        w['Housing'].cell(rental,2,2800)
        assert rounded(FormulaEvaluator(w).cell('Budget',builder.local(w['Budget'],'Savings monthly')))==835.46
        w['Housing'].cell(rental,2,2600)
        price_row=builder.rows['Cost to Own']['gas_price']
        w['Cost to Own'].cell(price_row,2,4.4)
        assert rounded(FormulaEvaluator(w).cell('Cost to Own',builder.local(w['Cost to Own'],'fuel_month')))==112.82
        w['Cost to Own'].cell(price_row,2,3.4)
        salaryrow=builder.rows['Profile & Car']['salary']
        w['Profile & Car'].cell(salaryrow,2,57600)
        assert FormulaEvaluator(w).cell('Budget',builder.local(w['Budget'],'Take-home monthly'))<4467
    print(f'PASS {path.name}: {formula_count} formulas evaluated; {len(builder.expected)} expected-output assertions; {refs} cross-sheet reference occurrences land on intended labels.')
    for s in builder.w:
        print(f'  {s.title}: {sum(c.data_type=="f" for row in s for c in row)} formulas')
    print(f'  Native charts: {sum(len(s._charts) for s in builder.w)}; fullCalcOnLoad=True; input-change checks passed.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true',help='Audit existing workbooks without writing files')
    args=parser.parse_args()
    independent_audit()
    for cs3 in [False,True]:
        builder=Builder().build(cs3)
        path=OUT/('csm-cs3-exemplar.xlsx' if cs3 else 'csm-cs2-exemplar.xlsx')
        if not args.verify: builder.w.save(path)
        verify_file(path,builder)
    print('PASS all verification. No Excel/LibreOffice recalculation performed; formula caches intentionally absent.')


if __name__=='__main__':
    main()
