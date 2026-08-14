#!/usr/bin/env python3
"""
Car Loan Amortization Calculator
Demonstrates how interest accrues over time on car payments
"""


def calculate_monthly_payment(principal, annual_rate, years):
    """Calculate monthly payment using loan amortization formula"""
    monthly_rate = annual_rate / 100 / 12
    num_payments = years * 12

    if monthly_rate == 0:
        return principal / num_payments

    monthly_payment = (
        principal
        * (monthly_rate * (1 + monthly_rate) ** num_payments)
        / ((1 + monthly_rate) ** num_payments - 1)
    )
    return monthly_payment


def generate_amortization_table(principal, annual_rate, years):
    """Generate complete amortization table"""
    monthly_rate = annual_rate / 100 / 12
    monthly_payment = calculate_monthly_payment(principal, annual_rate, years)
    num_payments = years * 12

    table = []
    remaining_balance = principal
    total_interest_paid = 0

    for payment_num in range(1, num_payments + 1):
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        remaining_balance -= principal_payment
        total_interest_paid += interest_payment

        table.append(
            {
                "Payment": payment_num,
                "Payment Amount": round(monthly_payment, 2),
                "Principal": round(principal_payment, 2),
                "Interest": round(interest_payment, 2),
                "Remaining Balance": round(max(0, remaining_balance), 2),
                "Total Interest Paid": round(total_interest_paid, 2),
            }
        )

    return table, monthly_payment, total_interest_paid


def display_amortization_table(
    table, monthly_payment, total_interest, principal, years, rate, msrp, down_payment
):
    """Display the amortization table in a formatted way"""
    print(f"\n{'=' * 80}")
    print(f"CAR LOAN AMORTIZATION SCHEDULE")
    print(f"{'=' * 80}")
    print(f"Car MSRP: ${msrp:,.2f}")
    print(f"Down Payment: ${down_payment:,.2f} ({((down_payment / msrp) * 100):.1f}%)")
    print(f"Loan Amount: ${principal:,.2f}")
    print(f"Annual Interest Rate: {rate}%")
    print(f"Loan Term: {years} years")
    print(f"Monthly Payment: ${monthly_payment:,.2f}")
    print(f"Total Interest Paid: ${total_interest:,.2f}")
    print(f"Total Amount Paid: ${principal + total_interest + down_payment:,.2f}")
    print(f"{'=' * 80}")

    # Print header
    header = f"{'Payment':>8} | {'Payment':>12} | {'Principal':>12} | {'Interest':>12} | {'Balance':>15} | {'Total Interest':>15}"
    print(header)
    print("-" * 80)

    # Print every 12th payment (yearly summary) plus first and last
    for i, row in enumerate(table):
        if i == 0 or i == len(table) - 1 or (i + 1) % 12 == 0:
            print(
                f"{row['Payment']:>8} | ${row['Payment Amount']:>11,.2f} | ${row['Principal']:>11,.2f} | ${row['Interest']:>11,.2f} | ${row['Remaining Balance']:>14,.2f} | ${row['Total Interest Paid']:>14,.2f}"
            )

    print("-" * 80)


def compare_down_payment_scenarios(msrp, annual_rate, years):
    """Compare different down payment scenarios"""
    down_payment_options = [0, 0.10, 0.20, 0.30]  # 0%, 10%, 20%, 30%

    print(f"\n📊 DOWN PAYMENT COMPARISON (MSRP: ${msrp:,.2f})")
    print("=" * 90)
    print(
        f"{'Down Payment':>12} | {'Loan Amount':>12} | {'Monthly':>10} | {'Total Interest':>14} | {'Interest Saved':>13}"
    )
    print("-" * 90)

    baseline_interest = None

    for dp_percent in down_payment_options:
        down_payment = msrp * dp_percent
        loan_amount = msrp - down_payment

        if loan_amount <= 0:
            continue

        table, monthly_payment, total_interest = generate_amortization_table(
            loan_amount, annual_rate, years
        )

        if baseline_interest is None:
            baseline_interest = total_interest
            interest_saved = 0
        else:
            interest_saved = baseline_interest - total_interest

        print(
            f"${down_payment:>11,.2f} | ${loan_amount:>11,.2f} | ${monthly_payment:>9,.2f} | ${total_interest:>13,.2f} | ${interest_saved:>12,.2f}"
        )

    print("-" * 90)


def main():
    """Main program that interacts with user"""
    print("Car Loan Amortization Calculator")
    print("This tool demonstrates how interest accrues over time on car payments.\n")

    try:
        # Get user input
        msrp = float(input("Enter car MSRP: $"))
        down_payment = float(input("Enter down payment amount: $"))
        annual_rate = float(input("Enter annual interest rate (e.g., 4.5 for 4.5%): "))
        years = int(input("Enter loan term in years: "))

        # Calculate loan amount after down payment
        loan_amount = msrp - down_payment

        # Validate input
        if msrp <= 0 or down_payment < 0 or annual_rate < 0 or years <= 0:
            print(
                "Error: Please enter positive values for MSRP and term, and non-negative values for down payment and interest rate."
            )
            return

        if down_payment >= msrp:
            print("Error: Down payment cannot equal or exceed the MSRP.")
            return

        # Generate and display amortization table
        table, monthly_payment, total_interest = generate_amortization_table(
            loan_amount, annual_rate, years
        )
        display_amortization_table(
            table,
            monthly_payment,
            total_interest,
            loan_amount,
            years,
            annual_rate,
            msrp,
            down_payment,
        )

        # Show some educational insights
        print(f"\n📚 EDUCATIONAL INSIGHTS:")
        print(f"• In the first year, you'll pay more interest than principal")
        first_year_interest = sum(row["Interest"] for row in table[:12])
        first_year_principal = sum(row["Principal"] for row in table[:12])
        print(
            f"• Year 1: ${first_year_interest:,.2f} in interest vs ${first_year_principal:,.2f} in principal"
        )
        print(f"• By the final year, you'll pay mostly principal")
        last_year_interest = sum(row["Interest"] for row in table[-12:])
        last_year_principal = sum(row["Principal"] for row in table[-12:])
        print(
            f"• Year {years}: ${last_year_interest:,.2f} in interest vs ${last_year_principal:,.2f} in principal"
        )
        print(
            f"• Total interest equals {((total_interest / loan_amount) * 100):.1f}% of your loan amount"
        )
        print(
            f"• Your down payment is {((down_payment / msrp) * 100):.1f}% of the car price"
        )

        # Show comparison with different down payments
        compare_down_payment_scenarios(msrp, annual_rate, years)

    except ValueError:
        print("Error: Please enter valid numeric values.")
    except KeyboardInterrupt:
        print("\nProgram cancelled.")


if __name__ == "__main__":
    main()
