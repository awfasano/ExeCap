from flask import Flask, render_template, url_for
import json

app = Flask(__name__)

# Enhanced data structure with cap space elements
COMPANIES = {
    101: {
        'name': 'Quantum Innovations Inc.',
        'ticker': 'QII',
        'sector': 'Technology',
        'market_cap': 85_000_000_000,  # $85B
        'revenue': 12_500_000_000,  # $12.5B
        'exec_budget': 50_000_000,  # "Salary cap" for executives
        'founded': 2010
    },
    102: {
        'name': 'Apex Solutions Ltd.',
        'ticker': 'ASL',
        'sector': 'Industrials',
        'market_cap': 32_000_000_000,  # $32B
        'revenue': 8_200_000_000,  # $8.2B
        'exec_budget': 35_000_000,  # Executive budget
        'founded': 2005
    },
    103: {
        'name': 'Stellar Holdings Group',
        'ticker': 'SHG',
        'sector': 'Financials',
        'market_cap': 67_000_000_000,  # $67B
        'revenue': 15_800_000_000,  # $15.8B
        'exec_budget': 45_000_000,  # Executive budget
        'founded': 1998
    },
}

PEOPLE = {
    1: {
        'name': 'Alex Rivera',
        'status': 'Active',
        'age': 52,
        'experience': 15,  # Years as executive
        'education': 'MBA Harvard',
        'previous_companies': ['Meta', 'Google']
    },
    2: {
        'name': 'Samantha Chen',
        'status': 'Active',
        'age': 48,
        'experience': 12,
        'education': 'CPA, Wharton',
        'previous_companies': ['Goldman Sachs', 'JP Morgan']
    },
    3: {
        'name': 'David Garcia',
        'status': 'Active',
        'age': 65,
        'experience': 25,
        'education': 'JD Stanford',
        'previous_companies': ['Boeing', 'Lockheed Martin']
    },
    4: {
        'name': 'Maria Rodriguez',
        'status': 'Active',
        'age': 45,
        'experience': 10,
        'education': 'PhD MIT',
        'previous_companies': ['Tesla', 'SpaceX']
    },
    5: {
        'name': 'James "Jim" Peterson',
        'status': 'Retired',
        'age': 68,
        'experience': 30,
        'education': 'MBA Kellogg',
        'previous_companies': ['IBM', 'Microsoft']
    },
    6: {
        'name': 'Patricia Jenkins',
        'status': 'Active',
        'age': 50,
        'experience': 18,
        'education': 'MBA Sloan',
        'previous_companies': ['Bank of America', 'Wells Fargo']
    },
}

ROLES = [
    # Quantum Innovations Inc. (QII) - "Roster"
    {'person_id': 1, 'company_id': 101, 'title': 'Chief Executive Officer', 'position_type': 'C-Suite', 'year': 2024,
     'contract_years': 5, 'base_salary': 1_500_000, 'bonus': 5_000_000, 'stock_awards': 19_000_000,
     'signing_bonus': 2_000_000},
    {'person_id': 2, 'company_id': 101, 'title': 'Chief Financial Officer', 'position_type': 'C-Suite', 'year': 2024,
     'contract_years': 4, 'base_salary': 950_000, 'bonus': 2_250_000, 'stock_awards': 12_000_000, 'signing_bonus': 0},
    {'person_id': 3, 'company_id': 101, 'title': 'Chairman of the Board', 'position_type': 'Board', 'year': 2024,
     'contract_years': 3, 'base_salary': 200_000, 'bonus': 0, 'stock_awards': 300_000, 'signing_bonus': 0},

    # Apex Solutions Ltd. (ASL) - "Roster"
    {'person_id': 4, 'company_id': 102, 'title': 'Chief Executive Officer', 'position_type': 'C-Suite', 'year': 2024,
     'contract_years': 6, 'base_salary': 1_200_000, 'bonus': 3_600_000, 'stock_awards': 15_000_000,
     'signing_bonus': 1_500_000},
    {'person_id': 5, 'company_id': 102, 'title': 'Chief Technology Officer', 'position_type': 'C-Suite', 'year': 2023,
     'contract_years': 2, 'base_salary': 800_000, 'bonus': 1_200_000, 'stock_awards': 10_000_000, 'signing_bonus': 0},
    {'person_id': 1, 'company_id': 102, 'title': 'Board Member', 'position_type': 'Board', 'year': 2024,
     'contract_years': 2, 'base_salary': 100_000, 'bonus': 0, 'stock_awards': 250_000, 'signing_bonus': 0},

    # Stellar Holdings Group (SHG) - "Roster"
    {'person_id': 6, 'company_id': 103, 'title': 'CEO & Chairperson', 'position_type': 'C-Suite', 'year': 2024,
     'contract_years': 5, 'base_salary': 1_800_000, 'bonus': 4_300_000, 'stock_awards': 16_000_000,
     'signing_bonus': 3_000_000},
    {'person_id': 2, 'company_id': 103, 'title': 'Board Member', 'position_type': 'Board', 'year': 2024,
     'contract_years': 3, 'base_salary': 125_000, 'bonus': 0, 'stock_awards': 250_000, 'signing_bonus': 0},
]


def get_total_compensation(role):
    """Calculate total compensation including all components"""
    return (role.get('base_salary', 0) +
            role.get('bonus', 0) +
            role.get('stock_awards', 0) +
            role.get('signing_bonus', 0))


def get_cap_utilization(company_id):
    """Calculate how much of the executive budget is being used"""
    company = COMPANIES[company_id]
    total_spent = sum(get_total_compensation(r) for r in ROLES if r['company_id'] == company_id)
    budget = company['exec_budget']
    utilization = (total_spent / budget) * 100 if budget > 0 else 0
    return {
        'total_spent': total_spent,
        'budget': budget,
        'remaining': budget - total_spent,
        'utilization_pct': utilization
    }


@app.route('/')
def index():
    """League Overview - like NFL.com homepage"""
    # Top earners across the "league"
    all_executives = []
    for role in ROLES:
        if role['position_type'] == 'C-Suite':  # Focus on C-Suite for top earners
            total_comp = get_total_compensation(role)
            all_executives.append({
                'person_id': role['person_id'],
                'person_name': PEOPLE[role['person_id']]['name'],
                'company_name': COMPANIES[role['company_id']]['name'],
                'company_ticker': COMPANIES[role['company_id']]['ticker'],
                'title': role['title'],
                'total_compensation': total_comp,
                'experience': PEOPLE[role['person_id']]['experience']
            })

    top_earners = sorted(all_executives, key=lambda x: x['total_compensation'], reverse=True)[:5]

    # League standings by market cap
    league_standings = []
    for cid, company in COMPANIES.items():
        cap_info = get_cap_utilization(cid)
        league_standings.append({
            'company': company,
            'company_id': cid,
            'cap_info': cap_info,
            'executive_count': len([r for r in ROLES if r['company_id'] == cid])
        })

    league_standings = sorted(league_standings, key=lambda x: x['company']['market_cap'], reverse=True)

    return render_template('index.html',
                           top_earners=top_earners,
                           league_standings=league_standings)


@app.route('/companies')
def company_list():
    """All Companies - like NFL teams page"""
    companies_data = []
    for cid, company_data in COMPANIES.items():
        cap_info = get_cap_utilization(cid)

        # Get roster composition
        c_suite_count = len([r for r in ROLES if r['company_id'] == cid and r['position_type'] == 'C-Suite'])
        board_count = len([r for r in ROLES if r['company_id'] == cid and r['position_type'] == 'Board'])

        companies_data.append({
            'id': cid,
            'name': company_data['name'],
            'ticker': company_data['ticker'],
            'sector': company_data['sector'],
            'market_cap': company_data['market_cap'],
            'revenue': company_data['revenue'],
            'cap_info': cap_info,
            'c_suite_count': c_suite_count,
            'board_count': board_count,
            'total_executives': c_suite_count + board_count
        })

    # Sort by cap utilization percentage
    sorted_companies = sorted(companies_data, key=lambda x: x['cap_info']['utilization_pct'], reverse=True)
    return render_template('companies.html', companies=sorted_companies)


@app.route('/company/<int:company_id>')
def company_detail(company_id):
    """Team Roster & Cap Space - like individual NFL team page"""
    company_info = COMPANIES.get(company_id)
    if not company_info:
        return "Company not found", 404

    cap_info = get_cap_utilization(company_id)

    # Get the "roster"
    executives = []
    for role in ROLES:
        if role['company_id'] == company_id:
            person = PEOPLE.get(role['person_id'])
            total_comp = get_total_compensation(role)
            executives.append({
                'person_id': role['person_id'],
                'name': person['name'],
                'title': role['title'],
                'position_type': role['position_type'],
                'contract_years': role['contract_years'],
                'age': person['age'],
                'experience': person['experience'],
                'base_salary': role['base_salary'],
                'bonus': role['bonus'],
                'stock_awards': role['stock_awards'],
                'signing_bonus': role['signing_bonus'],
                'total_compensation': total_comp,
                'cap_hit_pct': (total_comp / company_info['exec_budget']) * 100
            })

    # Sort by total compensation
    executives = sorted(executives, key=lambda x: x['total_compensation'], reverse=True)

    # Separate C-Suite and Board
    c_suite = [e for e in executives if e['position_type'] == 'C-Suite']
    board_members = [e for e in executives if e['position_type'] == 'Board']

    # Chart data
    chart_labels = [exec['name'] for exec in executives]
    chart_data = [exec['total_compensation'] for exec in executives]

    return render_template(
        'company_detail.html',
        company=company_info,
        company_id=company_id,
        cap_info=cap_info,
        c_suite=c_suite,
        board_members=board_members,
        all_executives=executives,
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data)
    )


@app.route('/person/<int:person_id>')
def person_detail(person_id):
    """Player Profile - like individual NFL player page"""
    person_info = PEOPLE.get(person_id)
    if not person_info:
        return "Person not found", 404

    # Get all roles/contracts
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
                'company_ticker': company['ticker'],
                'title': role['title'],
                'position_type': role['position_type'],
                'year': role['year'],
                'contract_years': role['contract_years'],
                'base_salary': role['base_salary'],
                'bonus': role['bonus'],
                'stock_awards': role['stock_awards'],
                'signing_bonus': role['signing_bonus'],
                'total_compensation': total_comp
            })

    # Career stats
    years_active = len(set(role['year'] for role in person_roles))
    companies_played_for = len(set(role['company_id'] for role in person_roles))
    avg_annual = total_earnings / years_active if years_active > 0 else 0

    career_stats = {
        'total_earnings': total_earnings,
        'years_active': years_active,
        'companies_count': companies_played_for,
        'avg_annual': avg_annual,
        'highest_single_year': max((get_total_compensation(r) for r in ROLES if r['person_id'] == person_id), default=0)
    }

    return render_template('person_detail.html',
                           person=person_info,
                           roles=person_roles,
                           career_stats=career_stats)


@app.route('/free-agents')
def free_agents():
    """Available executives not currently with companies"""
    # In a real app, this would show executives between companies
    # For now, we'll show retired executives who could potentially return
    free_agents = []
    for pid, person in PEOPLE.items():
        if person['status'] == 'Retired':
            # Get their last known compensation
            last_roles = [r for r in ROLES if r['person_id'] == pid]
            if last_roles:
                last_role = max(last_roles, key=lambda x: x['year'])
                last_comp = get_total_compensation(last_role)
                free_agents.append({
                    'person_id': pid,
                    'name': person['name'],
                    'age': person['age'],
                    'experience': person['experience'],
                    'education': person['education'],
                    'last_title': last_role['title'],
                    'last_compensation': last_comp,
                    'previous_companies': person['previous_companies']
                })

    return render_template('free_agents.html', free_agents=free_agents)


if __name__ == '__main__':
    app.run(debug=True)