from flask import Flask, render_template, url_for
import json

app = Flask(__name__)

# --- Enhanced Sample Data (Simulating a Database) ---
# This structure is more detailed, breaking down compensation.

PEOPLE = {
    1: {'name': 'Alex Rivera', 'status': 'Active'},
    2: {'name': 'Samantha Chen', 'status': 'Active'},
    3: {'name': 'David Garcia', 'status': 'Active'},
    4: {'name': 'Maria Rodriguez', 'status': 'Active'},
    5: {'name': 'James "Jim" Peterson', 'status': 'Retired'},
    6: {'name': 'Patricia Jenkins', 'status': 'Active'},
}

COMPANIES = {
    101: {'name': 'Quantum Innovations Inc.', 'ticker': 'QII', 'sector': 'Technology'},
    102: {'name': 'Apex Solutions Ltd.', 'ticker': 'ASL', 'sector': 'Industrials'},
    103: {'name': 'Stellar Holdings Group', 'ticker': 'SHG', 'sector': 'Financials'},
}

# Roles now contain a detailed breakdown of compensation.
ROLES = [
    {'person_id': 1, 'company_id': 101, 'title': 'Chief Executive Officer', 'year': 2024, 'base_salary': 1_500_000,
     'bonus': 5_000_000, 'stock_awards': 19_000_000},
    {'person_id': 1, 'company_id': 102, 'title': 'Board Member', 'year': 2024, 'base_salary': 100_000, 'bonus': 0,
     'stock_awards': 250_000},
    {'person_id': 2, 'company_id': 101, 'title': 'Chief Financial Officer', 'year': 2024, 'base_salary': 950_000,
     'bonus': 2_250_000, 'stock_awards': 12_000_000},
    {'person_id': 3, 'company_id': 101, 'title': 'Chairman of the Board', 'year': 2024, 'base_salary': 200_000,
     'bonus': 0, 'stock_awards': 300_000},
    {'person_id': 4, 'company_id': 102, 'title': 'Chief Executive Officer', 'year': 2024, 'base_salary': 1_200_000,
     'bonus': 3_600_000, 'stock_awards': 15_000_000},
    {'person_id': 5, 'company_id': 102, 'title': 'Chief Technology Officer', 'year': 2023, 'base_salary': 800_000,
     'bonus': 1_200_000, 'stock_awards': 10_000_000},
    {'person_id': 6, 'company_id': 103, 'title': 'CEO & Chairperson', 'year': 2024, 'base_salary': 1_800_000,
     'bonus': 4_300_000, 'stock_awards': 16_000_000},
    {'person_id': 2, 'company_id': 103, 'title': 'Board Member', 'year': 2024, 'base_salary': 125_000, 'bonus': 0,
     'stock_awards': 250_000},
]


# --- Helper Function for Calculations ---

def get_total_compensation(role):
    """Calculates the sum of all compensation fields for a role."""
    return role.get('base_salary', 0) + role.get('bonus', 0) + role.get('stock_awards', 0)


# --- Web Page Routes ---

@app.route('/')
def index():
    """Renders the main dashboard page."""
    # Calculate top 5 highest paid individuals across all roles
    all_roles_detailed = []
    for role in ROLES:
        total_comp = get_total_compensation(role)
        all_roles_detailed.append({
            'person_id': role['person_id'],
            'person_name': PEOPLE[role['person_id']]['name'],
            'company_name': COMPANIES[role['company_id']]['name'],
            'title': role['title'],
            'total_compensation': total_comp
        })

    top_earners = sorted(all_roles_detailed, key=lambda x: x['total_compensation'], reverse=True)[:5]

    return render_template('index.html', top_earners=top_earners)


@app.route('/companies')
def company_list():
    """Renders the list of all companies with their total payroll."""
    company_payrolls = []
    for cid, company_data in COMPANIES.items():
        total_payroll = sum(get_total_compensation(r) for r in ROLES if r['company_id'] == cid)
        company_payrolls.append({
            'id': cid,
            'name': company_data['name'],
            'ticker': company_data['ticker'],
            'total_payroll': total_payroll
        })

    # Sort by payroll, highest first
    sorted_companies = sorted(company_payrolls, key=lambda x: x['total_payroll'], reverse=True)
    return render_template('companies.html', companies=sorted_companies)


@app.route('/company/<int:company_id>')
def company_detail(company_id):
    """Renders the detail page for a single company."""
    company_info = COMPANIES.get(company_id)
    if not company_info:
        return "Company not found", 404

    # Find all executives for this company and calculate totals
    executives = []
    total_payroll = 0
    for role in ROLES:
        if role['company_id'] == company_id:
            person = PEOPLE.get(role['person_id'])
            total_comp = get_total_compensation(role)
            total_payroll += total_comp
            executives.append({
                'person_id': role['person_id'],
                'name': person['name'],
                'title': role['title'],
                'base_salary': role['base_salary'],
                'bonus': role['bonus'],
                'stock_awards': role['stock_awards'],
                'total_compensation': total_comp
            })

    # Sort executives by total compensation for the table
    executives = sorted(executives, key=lambda x: x['total_compensation'], reverse=True)

    # Prepare data for Chart.js
    chart_labels = [exec['name'] for exec in executives]
    chart_data = [exec['total_compensation'] for exec in executives]

    return render_template(
        'company_detail.html',
        company=company_info,
        executives=executives,
        total_payroll=total_payroll,
        # Safely pass data to JavaScript
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data)
    )


@app.route('/person/<int:person_id>')
def person_detail(person_id):
    """Renders the detail page for a single person, showing all their roles."""
    person_info = PEOPLE.get(person_id)
    if not person_info:
        return "Person not found", 404

    person_roles = []
    total_earnings = 0
    for role in ROLES:
        if role['person_id'] == person_id:
            company = COMPANIES.get(role['company_id'])
            total_comp = get_total_compensation(role)
            total_earnings += total_comp
            person_roles.append({
                'company_id': role['company_id'],
                'company_name': company['name'],
                'title': role['title'],
                'year': role['year'],
                'base_salary': role['base_salary'],
                'bonus': role['bonus'],
                'stock_awards': role['stock_awards'],
                'total_compensation': total_comp
            })

    return render_template('person_detail.html', person=person_info, roles=person_roles, total_earnings=total_earnings)


if __name__ == '__main__':
    app.run(debug=True)
