from flask import Flask, render_template, url_for, jsonify
import json
from company_folder_loader import CompanyFolderLoader

app = Flask(__name__)

# Configuration - UPDATE THESE WITH YOUR ACTUAL VALUES
BUCKET_NAME = "your-bucket-name"  # Replace with your actual GCS bucket name
CREDENTIALS_PATH = None  # Use None for default credentials or specify path to JSON file

# Initialize the Excel loader
folder_loader = CompanyFolderLoader(BUCKET_NAME, CREDENTIALS_PATH)

# Load data from all company folders
load_result = folder_loader.load_all_company_data()
if load_result['status'] == 'success':
    print(f"Successfully loaded data for companies: {load_result['companies_loaded']}")
    print(f"Total: {load_result['companies_count']} companies, {load_result['people_count']} people, {load_result['roles_count']} roles")
else:
    print(f"Error loading data: {load_result.get('message', 'Unknown error')}")

COMPANIES = folder_loader.get_companies()
PEOPLE = folder_loader.get_people()
ROLES = folder_loader.get_roles()


def get_total_compensation(role):
    """Calculate total compensation including all components"""
    return (role.get('base_salary', 0) +
            role.get('bonus', 0) +
            role.get('stock_awards', 0) +
            role.get('signing_bonus', 0))


def get_cap_utilization(company_id):
    """Calculate how much of the executive budget is being used"""
    company = COMPANIES.get(company_id, {})
    total_spent = sum(get_total_compensation(r) for r in ROLES if r['company_id'] == company_id)
    budget = company.get('exec_budget', 0)
    utilization = (total_spent / budget) * 100 if budget > 0 else 0
    return {
        'total_spent': total_spent,
        'budget': budget,
        'remaining': budget - total_spent,
        'utilization_pct': utilization
    }


@app.route('/')
def index():
    """League Overview - using Excel data"""
    all_executives = []
    for role in ROLES:
        if role['position_type'] == 'C-Suite':
            total_comp = get_total_compensation(role)
            person = PEOPLE.get(role['person_id'], {})
            company = COMPANIES.get(role['company_id'], {})

            all_executives.append({
                'person_id': role['person_id'],
                'person_name': person.get('name', 'Unknown'),
                'company_name': company.get('name', 'Unknown'),
                'company_ticker': company.get('ticker', 'UNK'),
                'title': role['title'],
                'total_compensation': total_comp,
                'experience': person.get('experience', 0)
            })

    top_earners = sorted(all_executives, key=lambda x: x['total_compensation'], reverse=True)[:5]

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
    """All Companies - using Excel data"""
    companies_data = []
    for cid, company_data in COMPANIES.items():
        cap_info = get_cap_utilization(cid)
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

    sorted_companies = sorted(companies_data, key=lambda x: x['cap_info']['utilization_pct'], reverse=True)
    return render_template('companies.html', companies=sorted_companies)


@app.route('/company/<int:company_id>')
def company_detail(company_id):
    """Team Roster & Cap Space - using Excel data"""
    company_info = COMPANIES.get(company_id)
    if not company_info:
        return "Company not found", 404

    cap_info = get_cap_utilization(company_id)

    executives = []
    for role in ROLES:
        if role['company_id'] == company_id:
            person = PEOPLE.get(role['person_id'], {})
            total_comp = get_total_compensation(role)
            executives.append({
                'person_id': role['person_id'],
                'name': person.get('name', 'Unknown'),
                'title': role['title'],
                'position_type': role['position_type'],
                'contract_years': role['contract_years'],
                'age': person.get('age', 0),
                'experience': person.get('experience', 0),
                'base_salary': role['base_salary'],
                'bonus': role['bonus'],
                'stock_awards': role['stock_awards'],
                'signing_bonus': role['signing_bonus'],
                'total_compensation': total_comp,
                'cap_hit_pct': (total_comp / company_info['exec_budget']) * 100
            })

    executives = sorted(executives, key=lambda x: x['total_compensation'], reverse=True)
    c_suite = [e for e in executives if e['position_type'] == 'C-Suite']
    board_members = [e for e in executives if e['position_type'] == 'Board']

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
    """Player Profile - using Excel data"""
    person_info = PEOPLE.get(person_id)
    if not person_info:
        return "Person not found", 404

    person_roles = []
    total_earnings = 0
    for role in ROLES:
        if role['person_id'] == person_id:
            company = COMPANIES.get(role['company_id'], {})
            total_comp = get_total_compensation(role)
            total_earnings += total_comp
            person_roles.append({
                'company_id': role['company_id'],
                'company_name': company.get('name', 'Unknown'),
                'company_ticker': company.get('ticker', 'UNK'),
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
    free_agents = []
    for pid, person in PEOPLE.items():
        if person['status'] == 'Retired':
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


@app.route('/refresh-data')
def refresh_data():
    """Refresh data from company folders"""
    global COMPANIES, PEOPLE, ROLES

    load_result = folder_loader.load_all_company_data()
    if load_result['status'] == 'success':
        COMPANIES = folder_loader.get_companies()
        PEOPLE = folder_loader.get_people()
        ROLES = folder_loader.get_roles()

        return f"Data refreshed! Loaded {load_result['companies_count']} companies, {load_result['people_count']} people, {load_result['roles_count']} roles"
    else:
        return f"Error refreshing data: {load_result.get('message')}"


@app.route('/api/company-folders')
def list_company_folders():
    """API endpoint to list available company folders"""
    folders = folder_loader.list_company_folders()
    company_files = {}

    for company in folders:
        company_files[company] = folder_loader.list_excel_files_for_company(company)

    return jsonify({
        'folders': folders,
        'files_by_company': company_files
    })


if __name__ == '__main__':
    app.run(debug=True)
