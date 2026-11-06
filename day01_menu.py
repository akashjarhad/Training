# Day 01 - AapleSeva Menu Driven Program
while True:
    print("\n" + "=" * 40)
    print("         AAPLESEVA MAIN MENU")
    print("=" * 40)
    print("1. About AapleSeva")
    print("2. Sample Questions")
    print("3. Check Eligibility (NCL / Income)")
    print("0. Exit")
    print("=" * 40)

    choice = input("Enter your choice (0-3): ")

    if choice == "1":
        print("\n--- About AapleSeva ---")
        print("AapleSeva (Aaple Sarkar) is a citizen service portal by the Government of Maharashtra.")
        print("It helps citizens apply online for Income, Caste, Domicile, and other certificates.")
        print("It is backed by the Maharashtra Right to Public Services Act (RTS Act, 2015).")
        print("Official portal: https://aaplesarkar.mahaonline.gov.in")

    elif choice == "2":
        print("\n--- Sample Questions ---")
        print("1. What documents are needed for an Income Certificate?")
        print("2. What is the time limit for getting a Domicile Certificate under RTS?")
        print("3. Who is eligible for a Non-Creamy Layer (NCL) Certificate?")
        print("4. How do I track my submitted application status?")

    elif choice == "3":
        print("\n--- Eligibility Rule Check ---")
        category = input("Enter your category (SC / ST / OBC / OPEN): ").upper()
        
        try:
            income = int(input("Enter your annual family income (in Rs): "))
        except ValueError:
            print("Invalid input! Please enter numbers only for income.")
            continue

        # Domain rule check using if / elif / else
        if income < 0:
            print("Income cannot be negative.")
        elif category in ["SC", "ST"]:
            print(f"For {category} category, Non-Creamy Layer is not required.")
            print("You are eligible for reservation benefits using Caste Certificate.")
        elif category == "OBC":
            if income <= 800000:
                print(f"Eligible for Non-Creamy Layer (NCL) certificate. Annual income Rs {income} is <= 8 Lakhs.")
            else:
                print(f"Not eligible for NCL. Annual income Rs {income} exceeds the 8 Lakhs creamy layer limit.")
        elif category == "OPEN":
            if income <= 800000:
                print(f"Eligible for EWS (Economically Weaker Section) certificate (Income <= 8 Lakhs).")
            else:
                print("Open category: General income certificate only (No reservation).")
        else:
            print("Category not recognized. Please enter SC, ST, OBC, or OPEN.")

    elif choice == "0":
        print("\nThank you for using AapleSeva Portal! Goodbye.")
        break

    else:
        print("\nInvalid choice! Please choose between 0 and 3.")
