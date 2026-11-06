# sanjivani-sj-13-aapleseva

## AapleSeva Project Card

- **Product:** AapleSeva Citizen Services Assistant - An automated platform and CLI tool for Maharashtra Government's Aaple Sarkar citizen services portal.
- **User:** Citizens of Maharashtra, students applying for admissions and scholarships, job aspirants, and farmers.
- **Problem:** People face confusion regarding document requirements, eligibility rules, and processing time for government certificates (Income, Domicile, Caste, Non-Creamy Layer).
- **Data Source:** Official Aaple Sarkar Portal (https://aaplesarkar.mahaonline.gov.in) and Maharashtra Right to Public Services Act (RTS Act, 2015).

---

## Project Structure

```text
sanjivani-sj-13-aapleseva/
├── .gitignore               # Ignored files (.venv, __pycache__, etc.)
├── requirements.txt         # Project requirements
├── README.md                # Project card and documentation
├── day01_intro.py           # Day 01: Project card with variables & f-strings
├── day01_menu.py            # Day 01: While-loop menu with domain rule check
├── data/
│   ├── sample_records.py    # S1: 20 Revenue notified services list of dicts
│   └── sample_records.json  # Exported JSON dataset
├── app/
│   ├── __init__.py          # Package initializer
│   ├── records.py           # S2: load_records, search, count_by, get_by_id
│   └── cli.py               # S2: Interactive CLI and flag-based interface
└── tests/
    └── test_records.py      # Unit tests for core record functions
```

---

## S1: 20 Revenue Department Notified Services
The 20 most frequently used services recorded under Maharashtra Right to Public Services Act (RTS 2015):
1. Age, Nationality and Domicile Certificate (15 days)
2. Income Certificate (15 days)
3. Caste Certificate (21 days)
4. Non-Creamy Layer Certificate (21 days)
5. Certified Copy of 7/12 Extract (1 day)
6. Certified Copy of 8A Extract (1 day)
7. Senior Citizen Certificate (8 days)
8. Solvency Certificate (21 days)
9. Small and Marginal Farmer Certificate (15 days)
10. Temporary Residence Certificate (7 days)
11. Agriculturist Certificate (15 days)
12. Character Certificate (15 days)
13. Economically Weaker Section (EWS) Certificate (15 days)
14. Legal Heir Certificate (21 days)
15. Minority Certificate (15 days)
16. Certified Copy of Mutation Entry (5 days)
17. Attestation of Affidavit (1 day)
18. Land Valuation Certificate (15 days)
19. Permission for Non-Agricultural Assessment (30 days)
20. Public Event and Loudspeaker Permission (5 days)

Each record captures: `id`, `service_name`, `department`, `category`, `time_limit_days`, `designated_officer`, `first_appellate_officer`, `second_appellate_officer`, and `source_url`.

---

## How to Run

### Setup Virtual Environment:
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate
```

### S1 Demo:
```bash
python data/sample_records.py
```

### S2 Interactive CLI:
```bash
python app/cli.py
```

### S2 Direct CLI Flags:
```bash
# List all 20 services
python app/cli.py --list

# Search by keyword
python app/cli.py --search caste
python app/cli.py --search farmer

# View service details by ID
python app/cli.py --id 4

# View counts grouped by category
python app/cli.py --count category
```

### Run Tests:
```bash
python tests/test_records.py
```
