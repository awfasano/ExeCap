# app.py - Complete version with year-based data structure support
from flask import Flask, render_template, url_for, jsonify, request
import json
from company_folder_loader import CompanyFolderLoader

app = Flask(__name__)

# Configuration
BUCKET_NAME = "execap"  # Your GCS bucket name
CREDENTIALS_PATH = None  # Use None for default credentials (uses Application Default Credentials)
DEFAULT_YEAR = "2024"  # Default year to load

# Initialize the Excel loader
folder_loader = CompanyFolderLoader(BUCKET_NAME, CREDENTIALS_PATH)


# Get current year from query params or use default
def get_selected_year():
    return request.args.get('year', DEFAULT_YEAR)


# Load initial data
print("Loading initial data...")
try:
    load_result = folder_loader.load_all_company_data(
        specific_year=DEFAULT_YEAR,  # Load specific year on startup
        load_all_years=False  # Set to True if you want to load all years at once
    )

    if load_result['status'] == 'success':
        print(f"Successfully loaded data for companies: {load_result['companies_loaded']}")
        print(
            f"Total: {load_result['companies_count']} companies, {load_result['people_count']} people, {load_result['roles_count']} roles")

        # Get the league manager directly from the loader
        league_manager = folder_loader.get_league_manager()
    else:
        print(f"Error loading data: {load_result.get('message', 'Unknown error')}")
        # Initialize empty league manager
        from models import LeagueManager

        league_manager = LeagueManager()
except Exception as e:
    print(f"Failed to load initial data: {str(e)}")
    print("Starting with empty data. You may need to:")
    print("1. Check your GCS bucket permissions")
    print("2. Verify the bucket name is 'execap'")
    print("3. Upload Excel files in the correct structure")
    from models import LeagueManager

    league_manager = LeagueManager()


@app.route('/')
def index():
    """League Overview with year selection"""
    year = get_selected_year()

    # Get available years for dropdown
    available_years = sorted(folder_loader.get_available_years(), reverse=True)

    # Filter data by year if needed
    top_earners_data = league_manager.get_top_earners_league_wide(limit=5)

    # Format for template
    top_earners = []
    for earner_data in top_earners_data:
        # Only include if role matches selected year
        if str(earner_data['role'].year) == year or not year:
            top_earners.append({
                'person_id': earner_data['person'].person_id,
                'person_name': earner_data['person'].name,
                'company_name': earner_data['company'].name,
                'company_ticker': earner_data['company'].ticker,
                'title': earner_data['role'].title,
                'total_compensation': earner_data['total_compensation'],
                'experience': earner_data['person'].experience,
                'year': earner_data['role'].year
            })

    # Get league standings
    league_standings = []
    for company in league_manager.get_league_standings():
        league_standings.append({
            'company': company.to_dict(),
            'company_id': company.company_id,
            'cap_info': company.get_cap_info(),
            'executive_count': company.executive_count
        })

    return render_template('index.html',
                           top_earners=top_earners[:5],
                           league_standings=league_standings,
                           selected_year=year,
                           available_years=available_years)


@app.route('/companies')
def company_list():
    """All Companies with year filtering"""
    year = get_selected_year()
    companies_data = []

    for company in league_manager.companies.values():
        # Filter roles by year if specified
        if year:
            year_roles = [r for r in company.all_roles if str(r.year) == year]
            if not year_roles:
                continue  # Skip companies with no data for this year

            # Calculate cap info for specific year
            year_spending = sum(r.total_compensation for r in year_roles)
            cap_info = {
                'total_spent': year_spending,
                'budget': company.exec_budget,
                'remaining': company.exec_budget - year_spending,
                'utilization_pct': (year_spending / company.exec_budget * 100) if company.exec_budget > 0 else 0
            }

            c_suite_count = len([r for r in year_roles if r.position_type == 'C-Suite'])
            board_count = len([r for r in year_roles if r.position_type == 'Board'])
        else:
            cap_info = company.get_cap_info()
            c_suite_count = company.executive_count
            board_count = company.board_count

        companies_data.append({
            'id': company.company_id,
            'name': company.name,
            'ticker': company.ticker,
            'sector': company.sector,
            'market_cap': company.market_cap,
            'revenue': company.revenue,
            'cap_info': cap_info,
            'c_suite_count': c_suite_count,
            'board_count': board_count,
            'total_executives': c_suite_count + board_count,
            'year': year
        })

    # Sort by cap utilization
    sorted_companies = sorted(companies_data,
                              key=lambda x: x['cap_info']['utilization_pct'],
                              reverse=True)

    # Get available years for dropdown
    available_years = sorted(folder_loader.get_available_years(), reverse=True)

    return render_template('companies.html',
                           companies=sorted_companies,
                           selected_year=year,
                           available_years=available_years)


@app.route('/company/<int:company_id>')
def company_detail(company_id):
    """Team Roster & Cap Space with year filtering"""
    year = get_selected_year()
    company = league_manager.get_company(company_id)
    if not company:
        return "Company not found", 404

    # Filter roles by year
    if year:
        year_roles = [r for r in company.all_roles if str(r.year) == year]
        year_spending = sum(r.total_compensation for r in year_roles)

        cap_info = {
            'total_spent': year_spending,
            'budget': company.exec_budget,
            'remaining': company.exec_budget - year_spending,
            'utilization_pct': (year_spending / company.exec_budget * 100) if company.exec_budget > 0 else 0,
            'is_over_budget': year_spending > company.exec_budget
        }

        # Get executives for this year
        c_suite = []
        board_members = []

        for role in year_roles:
            person = league_manager.get_person(role.person_id)
            if person:
                exec_data = {
                    'person_id': person.person_id,
                    'name': person.name,
                    'title': role.title,
                    'position_type': role.position_type,
                    'contract_years': role.contract_years,
                    'age': person.age,
                    'experience': person.experience,
                    'base_salary': role.base_salary,
                    'bonus': role.bonus,
                    'stock_awards': role.stock_awards,
                    'signing_bonus': role.signing_bonus,
                    'total_compensation': role.total_compensation,
                    'cap_hit_pct': (role.total_compensation / company.exec_budget * 100),
                    'year': role.year
                }

                if role.position_type == 'C-Suite':
                    c_suite.append(exec_data)
                else:
                    board_members.append(exec_data)

        # Sort by compensation
        c_suite.sort(key=lambda x: x['total_compensation'], reverse=True)
        board_members.sort(key=lambda x: x['total_compensation'], reverse=True)

    else:
        # Use all years
        cap_info = company.get_cap_info()

        c_suite_data = company.get_executives_by_position_type('C-Suite')
        c_suite = []
        for data in c_suite_data:
            person = data['person']
            role = data['role']
            c_suite.append({
                'person_id': person.person_id,
                'name': person.name,
                'title': role.title,
                'position_type': role.position_type,
                'contract_years': role.contract_years,
                'age': person.age,
                'experience': person.experience,
                'base_salary': role.base_salary,
                'bonus': role.bonus,
                'stock_awards': role.stock_awards,
                'signing_bonus': role.signing_bonus,
                'total_compensation': role.total_compensation,
                'cap_hit_pct': data['cap_hit_pct'],
                'year': role.year
            })

        board_data = company.get_executives_by_position_type('Board')
        board_members = []
        for data in board_data:
            person = data['person']
            role = data['role']
            board_members.append({
                'person_id': person.person_id,
                'name': person.name,
                'title': role.title,
                'position_type': role.position_type,
                'contract_years': role.contract_years,
                'age': person.age,
                'experience': person.experience,
                'base_salary': role.base_salary,
                'bonus': role.bonus,
                'stock_awards': role.stock_awards,
                'signing_bonus': role.signing_bonus,
                'total_compensation': role.total_compensation,
                'cap_hit_pct': data['cap_hit_pct'],
                'year': role.year
            })

    # Prepare chart data
    all_executives = c_suite + board_members
    chart_labels = [exec['name'] for exec in all_executives]
    chart_data = [exec['total_compensation'] for exec in all_executives]

    # Get available years for this company
    company_years = set()
    for role in company.all_roles:
        company_years.add(str(role.year))
    available_years = sorted(list(company_years), reverse=True)

    return render_template(
        'company_detail.html',
        company=company.to_dict(),
        company_id=company_id,
        cap_info=cap_info,
        c_suite=c_suite,
        board_members=board_members,
        all_executives=all_executives,
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data),
        selected_year=year,
        available_years=available_years
    )


@app.route('/person/<int:person_id>')
def person_detail(person_id):
    """Player Profile with year filtering"""
    year = get_selected_year()
    person = league_manager.get_person(person_id)
    if not person:
        return "Person not found", 404

    # Get all roles for this person, optionally filtered by year
    person_roles = []
    for role in person.roles:
        if year and str(role.year) != year:
            continue

        company = league_manager.get_company(role.company_id)
        if company:
            person_roles.append({
                'company_id': company.company_id,
                'company_name': company.name,
                'company_ticker': company.ticker,
                'title': role.title,
                'position_type': role.position_type,
                'year': role.year,
                'contract_years': role.contract_years,
                'base_salary': role.base_salary,
                'bonus': role.bonus,
                'stock_awards': role.stock_awards,
                'signing_bonus': role.signing_bonus,
                'total_compensation': role.total_compensation
            })

    # Sort roles by year (most recent first)
    person_roles.sort(key=lambda x: x['year'], reverse=True)

    # Calculate career statistics
    if year:
        # Stats for specific year
        year_roles = [r for r in person.roles if str(r.year) == year]
        total_earnings = sum(r.total_compensation for r in year_roles)
        years_active = 1 if year_roles else 0
        companies_count = len(set(r.company_id for r in year_roles))
        avg_annual = total_earnings
        highest_single_year = max((r.total_compensation for r in year_roles), default=0)
    else:
        # All-time stats
        total_earnings = person.total_career_earnings
        years_active = person.years_active
        companies_count = person.companies_count
        avg_annual = person.average_annual_compensation
        highest_single_year = person.highest_single_year_compensation

    career_stats = {
        'total_earnings': total_earnings,
        'years_active': years_active,
        'companies_count': companies_count,
        'avg_annual': avg_annual,
        'highest_single_year': highest_single_year
    }

    # Get years this person has data for
    person_years = sorted(list(set(str(r.year) for r in person.roles)), reverse=True)

    # Convert person to dict for template
    person_dict = person.to_dict()

    return render_template('person_detail.html',
                           person=person_dict,
                           roles=person_roles,
                           career_stats=career_stats,
                           selected_year=year,
                           available_years=person_years)


@app.route('/free-agents')
def free_agents():
    """Available executives not currently with companies"""
    year = get_selected_year()
    free_agents_list = []

    for person in league_manager.get_free_agents():
        last_role = None
        last_comp = 0

        if person.roles:
            # Get the most recent role (or for specific year)
            if year:
                year_roles = [r for r in person.roles if str(r.year) == year]
                if year_roles:
                    last_role = max(year_roles, key=lambda x: x.total_compensation)
            else:
                last_role = max(person.roles, key=lambda x: x.year)

            if last_role:
                last_comp = last_role.total_compensation

        if last_role or not year:  # Include person if they have a role for the year, or if showing all
            free_agents_list.append({
                'person_id': person.person_id,
                'name': person.name,
                'age': person.age,
                'experience': person.experience,
                'education': person.education,
                'last_title': last_role.title if last_role else 'N/A',
                'last_compensation': last_comp,
                'previous_companies': person.previous_companies,
                'last_year': last_role.year if last_role else None
            })

    # Get available years
    available_years = sorted(folder_loader.get_available_years(), reverse=True)

    return render_template('free_agents.html',
                           free_agents=free_agents_list,
                           selected_year=year,
                           available_years=available_years)


@app.route('/refresh-data')
def refresh_data():
    """Refresh data from company folders"""
    global league_manager

    year = get_selected_year()
    load_all = request.args.get('all_years', 'false').lower() == 'true'

    if load_all:
        load_result = folder_loader.load_all_company_data(load_all_years=True)
    else:
        load_result = folder_loader.load_all_company_data(specific_year=year)

    if load_result['status'] == 'success':
        # Get the updated league manager directly
        league_manager = folder_loader.get_league_manager()

        return f"Data refreshed! Loaded {load_result['companies_count']} companies, {load_result['people_count']} people, {load_result['roles_count']} roles for year {year if not load_all else 'all years'}"
    else:
        return f"Error refreshing data: {load_result.get('message')}"


@app.route('/api/company-folders')
def list_company_folders():
    """API endpoint to list available company folders with years"""
    folders = folder_loader.list_company_folders()
    company_files = {}
    company_years = {}

    for company in folders:
        # Get years for this company
        years = folder_loader.list_years_for_company(company)
        company_years[company] = years

        # Get files for each year
        company_files[company] = {}
        for year in years:
            files = folder_loader.list_excel_files_for_company_year(company, year)
            if year in files['by_year']:
                company_files[company][year] = files['by_year'][year]

    return jsonify({
        'folders': folders,
        'company_years': company_years,
        'files_by_company_year': company_files,
        'available_years': sorted(folder_loader.get_available_years(), reverse=True)
    })


@app.route('/api/league-stats')
def league_stats():
    """API endpoint for league-wide statistics"""
    year = get_selected_year()

    if year:
        # Calculate stats for specific year
        year_roles = [r for r in league_manager.all_roles if str(r.year) == year]
        total_spending = sum(r.total_compensation for r in year_roles)
        companies_with_data = len(set(r.company_id for r in year_roles))
        people_with_roles = len(set(r.person_id for r in year_roles))

        stats = {
            'year': year,
            'total_companies': companies_with_data,
            'total_people': people_with_roles,
            'total_roles': len(year_roles),
            'total_league_spending': total_spending,
            'avg_compensation': total_spending / len(year_roles) if year_roles else 0
        }
    else:
        stats = league_manager.get_league_statistics()

    return jsonify(stats)


@app.route('/api/company/<int:company_id>')
def company_api(company_id):
    """API endpoint for company data"""
    year = get_selected_year()
    company = league_manager.get_company(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    company_data = company.to_dict()

    # Add year-specific data if requested
    if year:
        year_roles = [r for r in company.all_roles if str(r.year) == year]
        year_spending = sum(r.total_compensation for r in year_roles)

        company_data['year_data'] = {
            'year': year,
            'total_spent': year_spending,
            'role_count': len(year_roles),
            'cap_utilization': (year_spending / company.exec_budget * 100) if company.exec_budget > 0 else 0
        }

    return jsonify(company_data)


@app.route('/api/person/<int:person_id>')
def person_api(person_id):
    """API endpoint for person data"""
    year = get_selected_year()
    person = league_manager.get_person(person_id)
    if not person:
        return jsonify({'error': 'Person not found'}), 404

    # Include compensation breakdown
    person_data = person.to_dict()
    person_data['compensation_breakdown'] = person.get_compensation_breakdown()

    # Add year-specific data if requested
    if year:
        year_roles = [r for r in person.roles if str(r.year) == year]
        year_earnings = sum(r.total_compensation for r in year_roles)

        person_data['year_data'] = {
            'year': year,
            'total_earnings': year_earnings,
            'role_count': len(year_roles),
            'companies': list(set(r.company_id for r in year_roles))
        }

    return jsonify(person_data)


@app.route('/api/years')
def available_years():
    """API endpoint to get all available years"""
    years = sorted(folder_loader.get_available_years(), reverse=True)
    return jsonify({
        'years': years,
        'default_year': DEFAULT_YEAR,
        'current_selection': get_selected_year()
    })


@app.route('/api/diagnostic')
def diagnostic():
    """Diagnostic endpoint to check system status"""
    try:
        # Check GCS connection
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)

        # List files in bucket
        files = []
        companies_found = set()
        years_found = set()

        for blob in bucket.list_blobs(prefix="companies/", max_results=20):
            files.append(blob.name)
            path_parts = blob.name.split('/')
            if len(path_parts) >= 2:
                companies_found.add(path_parts[1])
            if len(path_parts) >= 3 and path_parts[2].isdigit():
                years_found.add(path_parts[2])

        # Current data status
        data_status = {
            'bucket_name': BUCKET_NAME,
            'bucket_accessible': True,
            'files_found': len(files),
            'sample_files': files[:10],
            'companies_in_bucket': list(companies_found),
            'years_in_bucket': sorted(list(years_found)),
            'companies_loaded': len(league_manager.companies),
            'people_loaded': len(league_manager.people),
            'roles_loaded': len(league_manager.all_roles),
            'default_year': DEFAULT_YEAR,
            'current_year': get_selected_year()
        }

    except Exception as e:
        data_status = {
            'bucket_name': BUCKET_NAME,
            'bucket_accessible': False,
            'error': str(e),
            'error_type': type(e).__name__
        }

    return jsonify(data_status)


if __name__ == '__main__':
    app.run(debug=True)