# Excel/Google Sheets Car Loan Amortization Tutorial

This guide teaches students how to create a car loan amortization schedule in Excel or Google Sheets, helping them understand how interest accrues over time.

## 🎯 Learning Objectives
- Understand loan amortization formulas
- See how interest vs principal payments change over time
- Learn essential spreadsheet functions
- Visualize the true cost of borrowing

## 📋 Step-by-Step Instructions

### Step 1: Set Up Input Variables
Create these cells in your spreadsheet:

| Cell | Label | Example Value | Formula |
|------|-------|---------------|---------|
| B1 | Car MSRP | $25,000 | (user input) |
| B2 | Down Payment | $5,000 | (user input) |
| B3 | Annual Interest Rate | 4.5% | (user input) |
| B4 | Loan Term (Years) | 5 | (user input) |
| B5 | Loan Amount | | =B1-B2 |
| B6 | Monthly Interest Rate | | =B3/12 |
| B7 | Total Payments | | =B4*12 |
| B8 | Down Payment % | | =B2/B1 |

### Step 2: Calculate Monthly Payment
In cell B9, use the PMT function:
```
=PMT(B6, B7, -B5)
```
*Note: The negative sign on B5 makes the payment positive*

### Step 3: Create Amortization Table Headers
Set up these column headers starting at row 11:

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Payment # | Payment | Principal | Interest | Balance | Total Interest |

### Step 4: Build the First Row (Payment 1)
In row 12, enter these formulas:

- **A12**: `=1` (Payment number)
- **B12**: `=$B$9` (Monthly payment - absolute reference)
- **C12**: `=B12-D12` (Principal payment)
- **D12**: `=B5*$B$6` (Interest payment)
- **E12**: `=B5-C12` (Remaining balance)
- **F12**: `=D12` (Total interest paid)

### Step 5: Build the Second Row (Payment 2)
In row 13, enter these formulas:

- **A13**: `=A12+1`
- **B13**: `=$B$9`
- **C13**: `=B13-D13`
- **D13**: `=E12*$B$6` (Interest on remaining balance)
- **E13**: `=E12-C13`
- **F13**: `=F12+D13`

### Step 6: Fill Down the Table
1. Select row 13 (cells A13:F13)
2. Drag the fill handle down to row 70 (for 60 payments)
3. The table will automatically calculate all payments

### Step 7: Add Summary Statistics
Add these calculations somewhere in your sheet:

```
Total Paid: =B9*B7+B2
Total Interest: =F70
Interest % of Loan: =F70/B5
Total Cost: =B5+F70+B2
```

## 🔍 Key Teaching Points

### 1. The Interest Formula
`=Previous_Balance * Monthly_Rate`
- Students see that interest is calculated on the REMAINING balance
- This is why interest decreases over time

### 2. Principal vs Interest Split
- Early payments: Mostly interest, little principal
- Late payments: Mostly principal, little interest
- This demonstrates the "front-loaded" nature of loan interest

### 3. Total Interest Impact
Have students experiment with different scenarios:
- What happens with a 2% vs 8% interest rate?
- How does a 3-year vs 6-year term affect total interest?
- What's the impact of a larger down payment?

## 📊 Down Payment Comparison Activity

### Step 8: Create Down Payment Scenarios
Create a comparison table to show how different down payments affect the loan:

| Cell | Label | Formula |
|------|-------|---------|
| G1 | **Down Payment Comparison** | |
| G2 | Down Payment % | 0% |
| G3 | Down Payment % | 10% |
| G4 | Down Payment % | 20% |
| G5 | Down Payment % | 30% |
| H2 | Down Payment Amount | =$B$1*G2 |
| H3 | Down Payment Amount | =$B$1*G3 |
| H4 | Down Payment Amount | =$B$1*G4 |
| H5 | Down Payment Amount | =$B$1*G5 |
| I2 | Loan Amount | =$B$1-H2 |
| I3 | Loan Amount | =$B$1-H3 |
| I4 | Loan Amount | =$B$1-H4 |
| I5 | Loan Amount | =$B$1-H5 |
| J2 | Monthly Payment | =PMT($B$6,$B$7,-I2) |
| J3 | Monthly Payment | =PMT($B$6,$B$7,-I3) |
| J4 | Monthly Payment | =PMT($B$6,$B$7,-I4) |
| J5 | Monthly Payment | =PMT($B$6,$B$7,-I5) |
| K2 | Total Interest | =J2*$B$7-I2 |
| K3 | Total Interest | =J3*$B$7-I3 |
| K4 | Total Interest | =J4*$B$7-I4 |
| K5 | Total Interest | =J5*$B$7-I5 |
| L2 | Interest Saved | =$K$2-K2 |
| L3 | Interest Saved | =$K$2-K3 |
| L4 | Interest Saved | =$K$2-K4 |
| L5 | Interest Saved | =$K$2-K5 |

**Teaching Point**: Students can see how increasing the down payment reduces both monthly payments and total interest paid!

## 📊 Extension Activities

### Activity 1: Create Charts
1. Select columns C and D (Principal and Interest)
2. Insert → Chart → Stacked Column Chart
3. This visualizes the changing payment composition over time

### Activity 2: Extra Payment Analysis
Add a column for extra payments and see how they affect:
- Total interest paid
- Loan payoff time
- Monthly cash flow

### Activity 3: Down Payment Impact Chart
1. Select the down payment comparison data (G2:L5)
2. Insert → Chart → Column Chart
3. This visualizes how down payments affect monthly payments and total interest
4. Students can clearly see the financial benefits of larger down payments

### Activity 4: Sensitivity Analysis
Create a data table to see how different combinations of down payments and interest rates affect monthly payments:
1. Set up interest rates across the top row (3%, 4%, 5%, 6%)
2. Set up down payment percentages down the first column (0%, 10%, 20%, 30%)
3. Use Data → What-If Analysis → Data Table to fill in the monthly payments for each combination

## 🧮 Formulas to Remember

| Function | Purpose | Example |
|----------|---------|---------|
| PMT | Calculate loan payment | `=PMT(rate, nper, pv)` |
| IPMT | Calculate interest portion | `=IPMT(rate, per, nper, pv)` |
| PPMT | Calculate principal portion | `=PPMT(rate, per, nper, pv)` |
| CUMIPMT | Cumulative interest | `=CUMIPMT(rate, nper, pv, start, end, type)` |

## 💡 Pro Tips for Students

1. **Use Absolute References**: Use `$` signs (like `$B$6`) when you don't want cell references to change when filling down.

2. **Format as Currency**: Select your monetary cells and format them as currency for better readability.

3. **Check Your Work**: The final balance should be $0 (or very close due to rounding).

4. **Understand the Math**: The monthly payment formula is:
   ```
   Payment = P × [r(1+r)^n] / [(1+r)^n - 1]
   ```
   Where P=principal, r=monthly rate, n=number of payments

## 🎓 Real-World Applications

- Compare dealer financing vs bank loans
- Understand the true cost of different loan terms
- Make informed decisions about down payments
- See the long-term impact of interest rates

This exercise helps students develop financial literacy while mastering essential spreadsheet skills!