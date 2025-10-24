# app.py - Complete version with year-based data structure support
import json
import os
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Set

from flask import Flask, jsonify, render_template, request, url_for

from company_folder_loader import CompanyFolderLoader
from fortune10_loader import Fortune10LoadError, load_fortune10_league
from models import LeagueManager

app = Flask(__name__)

# Configuration
BUCKET_NAME = "execap"  # Your GCS bucket name
CREDENTIALS_PATH = None  # Use None for default credentials (uses Application Default Credentials)
DEFAULT_YEAR = "2024"  # Default year to load
DATA_SOURCE = os.getenv('DATA_SOURCE', 'gcs').lower()  # 'fortune10' or 'gcs'
ALLOW_SAMPLE_FALLBACK = os.getenv('ALLOW_SAMPLE_FALLBACK', 'false').lower() == 'true'

# Role archetypes for position leader board
ROLE_CATEGORY_RULES = [
    {
        'label': 'Chairman',
        'keywords': ['chairman', 'chairperson', 'chairwoman'],
    },
    {
        'label': 'Board Director',
        'keywords': ['director'],
    },
    {
        'label': 'Executive Chair',
        'keywords': ['executive chair'],
    },
    {
        'label': 'Chief Executive Officer',
        'keywords': ['chief executive officer', 'ceo'],
    },
    {
        'label': 'Chief Financial Officer',
        'keywords': ['chief financial officer', 'cfo'],
    },
    {
        'label': 'Chief Operating Officer',
        'keywords': ['chief operating officer', 'coo'],
    },
    {
        'label': 'Executive Vice President',
        'keywords': ['executive vice president', 'evp'],
    },
    {
        'label': 'Vice President',
        'keywords': ['vice president'],
    },
    {
        'label': 'President',
        'keywords': ['president'],
    }
]

# Initialize the Excel loader when using GCS
folder_loader: Optional[CompanyFolderLoader] = None
if DATA_SOURCE == 'gcs':
    print("Configured to load company data from GCS bucket")
    folder_loader = CompanyFolderLoader(BUCKET_NAME, CREDENTIALS_PATH)

FALLBACK_AVAILABLE_YEARS: Set[str] = set()
USING_SAMPLE_DATA = DATA_SOURCE == 'fortune10'


def load_fortune10_sample_dataset() -> LeagueManager:
    """Load the bundled Fortune 10 dataset as a local development fallback."""
    global FALLBACK_AVAILABLE_YEARS, USING_SAMPLE_DATA
    try:
        league, years = load_fortune10_league()
        FALLBACK_AVAILABLE_YEARS = {str(year.year) for year in years}
        USING_SAMPLE_DATA = True
        print("Loaded Fortune 10 sample dataset for local development.")
        return league
    except Fortune10LoadError as error:
        print(f"Fortune 10 sample data unavailable: {error}")
    except Exception as error:
        print(f"Unexpected error loading Fortune 10 sample data: {error}")

    FALLBACK_AVAILABLE_YEARS = {DEFAULT_YEAR}
    USING_SAMPLE_DATA = True
    return LeagueManager()


def get_available_year_options() -> List[str]:
    """Return the list of seasons available for selection."""
    if FALLBACK_AVAILABLE_YEARS:
        return sorted(FALLBACK_AVAILABLE_YEARS, reverse=True)

    manager = globals().get('league_manager')
    if manager and hasattr(manager, 'get_available_years'):
        manager_years = getattr(manager, 'get_available_years')()
        if manager_years:
            return sorted({str(year.year) for year in manager_years}, reverse=True)

    return [DEFAULT_YEAR]


# Get current year from query params or use default
def get_selected_year():
    return request.args.get('year', DEFAULT_YEAR)


def parse_year_to_date(year_str: Optional[str]) -> Optional[date]:
    if not year_str:
        return None
    try:
        return date(int(year_str), 12, 31)
    except ValueError:
        return None


def dates_share_year(value: Optional[date], target: Optional[date]) -> bool:
    if not target:
        return True
    if not value:
        return False
    return value.year == target.year


def company_to_template_dict(company) -> Dict:
    name = company.company_name or company.company_id.replace('_', ' ').title()
    ticker = company.ticker or company.company_id[:4].upper()
    return {
        'company_id': company.company_id,
        'name': name,
        'ticker': ticker,
        'ticker_display': (ticker[:2] if ticker else ''),
        'sector': company.sector or 'N/A',
        'market_cap': company.market_cap_usd or 0,
        'revenue': company.revenue_usd or 0,
        'exec_budget': company.cap_budget_usd or 0,
        'founded': company.founded_year or '—',
        'fiscal_year_end': company.fiscal_year_end,
    }


def get_board_count(manager: LeagueManager, company_id: str) -> int:
    return len(manager.get_director_profiles_for_company(company_id))


# Load initial data
print("Loading initial data...")
if DATA_SOURCE == 'fortune10':
    league_manager = load_fortune10_sample_dataset()
else:
    try:
        load_result = folder_loader.load_all_company_data(
            specific_year=DEFAULT_YEAR,  # Load specific year on startup
            load_all_years=False  # Set to True if you want to load all years at once
        )

        if load_result['status'] == 'success':
            print(f"Successfully loaded data for companies: {load_result['companies_loaded']}")
            print(
                f"Total: {load_result['companies_count']} companies, {load_result['people_count']} people, {load_result['executive_comp_count']} compensation rows")
            if load_result.get('warnings'):
                print("Warnings during load:")
                for warning in load_result['warnings']:
                    print(f" - {warning}")
            if not load_result.get('companies_count'):
                print("No companies were loaded. Verify that CSV files are present in the bucket.")

            league_manager = folder_loader.get_league_manager()
            FALLBACK_AVAILABLE_YEARS.clear()
            USING_SAMPLE_DATA = False
        else:
            message = load_result.get('message', 'Unknown error')
            print(f"Error loading data: {message}")
            if load_result.get('warnings'):
                print("Warnings during failed load:")
                for warning in load_result['warnings']:
                    print(f" - {warning}")
            if ALLOW_SAMPLE_FALLBACK:
                print("ALLOW_SAMPLE_FALLBACK is true; loading bundled Fortune 10 dataset.")
                league_manager = load_fortune10_sample_dataset()
            else:
                print("Sample fallback disabled. Continuing with empty dataset.")
                league_manager = LeagueManager()
                FALLBACK_AVAILABLE_YEARS.clear()
                USING_SAMPLE_DATA = False
    except Exception as e:
        print(f"Failed to load initial data: {str(e)}")
        print("Starting with empty data. You may need to:")
        print("1. Check your GCS bucket permissions")
        print("2. Verify the bucket name is 'execap'")
        print("3. Upload Excel files in the correct structure")
        if ALLOW_SAMPLE_FALLBACK:
            print("ALLOW_SAMPLE_FALLBACK is true; loading bundled Fortune 10 dataset.")
            league_manager = load_fortune10_sample_dataset()
        else:
            league_manager = LeagueManager()
            FALLBACK_AVAILABLE_YEARS.clear()
            USING_SAMPLE_DATA = False


@app.route('/')
def index():
    """League Overview with year selection"""
    year = get_selected_year()
    available_years = get_available_year_options()
    if year not in available_years and available_years:
        year = available_years[0]
    year_date = parse_year_to_date(year)

    company_rows = []
    total_exec_spend = 0.0
    total_director_spend = 0.0
    total_director_shares = 0
    total_exec_shares = 0

    for company in league_manager.get_league_standings():
        company_dict = company_to_template_dict(company)
        exec_records = league_manager.get_company_compensation(company.company_id, year_date)
        director_records = [
            record for record in league_manager.director_comp
            if record.company_id == company.company_id and dates_share_year(record.fiscal_year_end, year_date)
        ]
        ownership_records = [
            record for record in league_manager.beneficial_ownership
            if record.company_id == company.company_id
        ]

        if year and not exec_records and not director_records and not ownership_records:
            continue

        exec_total = sum(record.total_comp_usd for record in exec_records)
        director_total = sum(record.total_usd for record in director_records)

        experiences = []
        exec_person_ids = set()
        for record in exec_records:
            person = league_manager.get_person(record.person_id)
            if person:
                exec_person_ids.add(person.person_id)
                if person.years_experience is not None:
                    experiences.append(person.years_experience)

        avg_experience = (sum(experiences) / len(experiences)) if experiences else None
        director_count = len({record.person_id for record in director_records})

        ownership_director_shares = 0
        ownership_exec_shares = 0
        for record in ownership_records:
            person = league_manager.get_person(record.person_id)
            if not person:
                continue
            if person.is_director:
                ownership_director_shares += record.total_shares
            if person.is_executive or record.person_id in exec_person_ids:
                ownership_exec_shares += record.total_shares

        total_exec_spend += exec_total
        total_director_spend += director_total
        total_director_shares += ownership_director_shares
        total_exec_shares += ownership_exec_shares

        company_rows.append({
            'company': company_dict,
            'executive_total': exec_total,
            'director_total': director_total,
            'avg_experience': avg_experience,
            'executive_count': len(exec_records),
            'director_count': director_count,
            'ownership_director_shares': ownership_director_shares,
            'ownership_exec_shares': ownership_exec_shares,
        })

    company_rows.sort(key=lambda row: row['executive_total'], reverse=True)
    for idx, row in enumerate(company_rows, start=1):
        row['rank'] = idx

    exec_chart_labels = [row['company']['ticker'] or row['company']['name'] for row in company_rows[:8]]
    exec_chart_values = [round(row['executive_total'], 2) for row in company_rows[:8]]

    top_for_mix = company_rows[:6]
    pay_mix_chart = {
        'labels': [row['company']['ticker'] or row['company']['name'] for row in top_for_mix],
        'executive': [round(row['executive_total'], 2) for row in top_for_mix],
        'director': [round(row['director_total'], 2) for row in top_for_mix],
    }

    ownership_mix_chart = {
        'labels': [row['company']['ticker'] or row['company']['name'] for row in top_for_mix],
        'exec_shares': [row['ownership_exec_shares'] for row in top_for_mix],
        'director_shares': [row['ownership_director_shares'] for row in top_for_mix],
    }

    exec_count_by_company = {row['company']['name']: row['executive_count'] for row in company_rows}
    owner_top_execs = sorted(
        (record for record in league_manager.beneficial_ownership if (not year_date or record.as_of_date.year == year_date.year)),
        key=lambda record: record.total_shares,
        reverse=True
    )
    top_exec_owners = []
    top_director_owners = []
    for record in owner_top_execs:
        person = league_manager.get_person(record.person_id)
        company = league_manager.get_company(record.company_id)
        if not person or not company:
            continue
        owner_entry = {
            'person_id': person.person_id,
            'person_name': person.full_name,
            'company_name': company.company_name,
            'company_id': company.company_id,
            'company_ticker': company.ticker,
            'total_shares': record.total_shares,
            'percent_of_class': record.percent_of_class,
        }
        if person.is_executive and len(top_exec_owners) < 5:
            top_exec_owners.append(owner_entry)
        if person.is_director and len(top_director_owners) < 5:
            top_director_owners.append(owner_entry)
        if len(top_exec_owners) >= 5 and len(top_director_owners) >= 5:
            break

    comp_records_sorted = sorted(
        [
            (record, league_manager.get_company(record.company_id), league_manager.get_person(record.person_id))
            for record in league_manager.executive_comp
            if dates_share_year(record.fiscal_year_end, year_date)
        ],
        key=lambda triple: triple[0].total_comp_usd,
        reverse=True
    )
    top_paid_execs = [
        {
            'person_id': person.person_id,
            'person_name': person.full_name,
            'company_name': company.company_name,
            'company_id': company.company_id,
            'company_ticker': company.ticker,
            'title': person.current_title,
            'total_compensation': record.total_comp_usd,
        }
        for record, company, person in comp_records_sorted[:5]
        if company and person
    ]

    exec_distribution = {
        'labels': [row['company']['name'] for row in company_rows],
        'values': [row['executive_count'] for row in company_rows]
    }

    director_spend_chart = {
        'labels': [row['company']['name'] for row in company_rows[:8]],
        'values': [round(row['director_total'], 2) for row in company_rows[:8]]
    }

    ownership_density = {
        'labels': [row['company']['name'] for row in company_rows[:8]],
        'values': [row['ownership_director_shares'] + row['ownership_exec_shares'] for row in company_rows[:8]]
    }

    summary_metrics = {
        'companies': len(company_rows),
        'total_exec_spend': total_exec_spend,
        'total_director_spend': total_director_spend,
        'avg_exec_spend': (total_exec_spend / len(company_rows)) if company_rows else 0,
        'total_director_shares': total_director_shares,
        'total_exec_shares': total_exec_shares,
        'total_insider_shares': total_director_shares + total_exec_shares,
    }

    return render_template(
        'index.html',
        company_rows=company_rows,
        summary_metrics=summary_metrics,
        exec_chart_labels=exec_chart_labels,
        exec_chart_values=exec_chart_values,
        top_paid_execs=top_paid_execs,
        top_exec_owners=top_exec_owners,
        top_director_owners=top_director_owners,
        exec_distribution=exec_distribution,
        director_spend_chart=director_spend_chart,
        ownership_density=ownership_density,
        pay_mix_chart=pay_mix_chart,
        ownership_mix_chart=ownership_mix_chart,
        selected_year=year,
        available_years=available_years,
    )


@app.route('/companies')
def company_list():
    """All Companies with year filtering"""
    year = get_selected_year()
    available_years = get_available_year_options()
    if year not in available_years and available_years:
        year = available_years[0]
    year_date = parse_year_to_date(year)

    companies_data = []
    for company in league_manager.get_league_standings():
        company_dict = company_to_template_dict(company)
        compensation = league_manager.get_company_compensation(company.company_id, year_date)
        if year and not compensation:
            continue

        cap_info = league_manager.get_company_cap_snapshot(company.company_id, year_date)
        c_suite_count = 0
        for record in compensation:
            person = league_manager.get_person(record.person_id)
            if person and person.is_executive:
                c_suite_count += 1
        board_count = get_board_count(league_manager, company.company_id)

        companies_data.append({
            'id': company.company_id,
            'name': company_dict['name'],
            'ticker': company_dict['ticker'],
            'sector': company_dict['sector'],
            'market_cap': company_dict['market_cap'],
            'revenue': company_dict['revenue'],
            'cap_info': cap_info,
            'c_suite_count': c_suite_count,
            'board_count': board_count,
            'total_executives': c_suite_count + board_count,
            'year': year
        })

    sorted_companies = sorted(
        companies_data,
        key=lambda item: item['cap_info'].get('utilization_pct', 0),
        reverse=True,
    )

    return render_template(
        'companies.html',
        companies=sorted_companies,
        selected_year=year,
        available_years=available_years,
    )


@app.route('/company/<company_id>')
def company_detail(company_id):
    """Team Roster & Cap Space with year filtering"""
    year = get_selected_year()
    company = league_manager.get_company(company_id)
    if not company:
        return "Company not found", 404

    available_years = get_available_year_options()
    if year not in available_years and available_years:
        year = available_years[0]
    year_date = parse_year_to_date(year)

    cap_info = league_manager.get_company_cap_snapshot(company_id, year_date)
    company_dict = company_to_template_dict(company)
    revenue = company_dict['revenue'] or 0
    if revenue:
        cap_info['exec_percent_revenue'] = (cap_info.get('total_spent', 0) / revenue) * 100
    else:
        cap_info['exec_percent_revenue'] = 0

    all_compensation_records = league_manager.get_company_compensation(company_id)
    compensation_records = (
        league_manager.get_company_compensation(company_id, year_date)
        if year_date else all_compensation_records
    )

    c_suite = []
    exec_total = 0
    exec_count = 0
    exec_experience_values = []
    for record in compensation_records:
        person = league_manager.get_person(record.person_id)
        if not person:
            continue
        budget = cap_info.get('budget') or 0
        c_suite.append({
            'person_id': person.person_id,
            'name': person.full_name,
            'title': person.current_title,
            'position_type': 'C-Suite' if person.is_executive else 'Director',
            'contract_years': 1,
            'age': None,
            'experience': person.years_experience,
            'base_salary': record.salary_usd,
            'bonus': record.bonus_usd,
            'stock_awards': record.stock_awards_usd,
            'signing_bonus': record.all_other_comp_usd,
            'share_count': None,
            'total_compensation': record.total_comp_usd,
            'cap_hit_pct': (record.total_comp_usd / budget * 100) if budget else 0,
            'year': record.fiscal_year_end.year,
        })
        exec_total += record.total_comp_usd
        exec_count += 1
        if person.years_experience is not None:
            exec_experience_values.append(person.years_experience)

    board_profiles = league_manager.get_director_profiles_for_company(company_id)
    all_director_records = [
        record for record in league_manager.director_comp if record.company_id == company_id
    ]
    director_comp_records = [
        record
        for record in all_director_records
        if dates_share_year(record.fiscal_year_end, year_date)
    ]
    board_members = []
    for profile in board_profiles:
        person = league_manager.get_person(profile.person_id)
        comp_record = next((r for r in director_comp_records if r.person_id == profile.person_id), None)
        board_members.append({
            'person_id': profile.person_id,
            'name': person.full_name if person else profile.person_id,
            'title': profile.role,
            'position_type': 'Board',
            'contract_years': 1,
            'age': None,
            'experience': person.years_experience if person else None,
            'base_salary': comp_record.fees_cash_usd if comp_record else 0,
            'bonus': 0,
            'stock_awards': comp_record.stock_awards_usd if comp_record else 0,
            'signing_bonus': comp_record.all_other_comp_usd if comp_record else 0,
            'share_count': None,
            'total_compensation': comp_record.total_usd if comp_record else 0,
            'cap_hit_pct': 0,
            'year': (comp_record.fiscal_year_end.year if comp_record else (year_date.year if year_date else company.fiscal_year_end.year)),
        })

    director_policies = [
        policy for policy in league_manager.director_policies if policy.company_id == company_id
    ]

    director_comp_summary = {}
    if director_comp_records:
        board_count = len(director_comp_records)
        total_cash = sum(r.fees_cash_usd for r in director_comp_records)
        total_stock = sum(r.stock_awards_usd for r in director_comp_records)
        total_other = sum(r.all_other_comp_usd for r in director_comp_records)
        total_comp = sum(r.total_usd for r in director_comp_records)
        director_comp_summary = {
            'members': board_count,
            'avg_cash': total_cash / board_count if board_count else 0,
            'avg_stock': total_stock / board_count if board_count else 0,
            'avg_total': total_comp / board_count if board_count else 0,
            'total_cash': total_cash,
            'total_stock': total_stock,
            'total_other': total_other,
            'total_comp': total_comp,
        }

    all_executives = c_suite + board_members
    chart_labels = [item['name'] for item in c_suite]
    chart_data = [item['total_compensation'] for item in c_suite]

    company_years = {
        record.fiscal_year_end.year
        for record in all_compensation_records
        if record.fiscal_year_end
    }
    available_company_years = sorted({str(yr) for yr in company_years}, reverse=True)

    exec_avg_comp = (exec_total / exec_count) if exec_count else 0
    exec_avg_experience = (sum(exec_experience_values) / len(exec_experience_values)) if exec_experience_values else None

    director_total = sum(record.total_usd for record in director_comp_records)
    director_count = len({record.person_id for record in director_comp_records})
    director_avg_total = (director_total / director_count) if director_count else 0

    revenue = company_dict['revenue'] or 0
    market_cap = company_dict['market_cap'] or 0
    exec_to_revenue_pct = (exec_total / revenue * 100) if revenue else None
    director_to_revenue_pct = (director_total / revenue * 100) if revenue else None
    total_pay = exec_total + director_total
    total_to_revenue_pct = (total_pay / revenue * 100) if revenue else None
    revenue_per_exec = (revenue / exec_count) if exec_count and revenue else None
    comp_per_exec = (exec_total / exec_count) if exec_count else None
    market_cap_to_pay = (market_cap / total_pay) if total_pay else None

    exec_totals_by_year = defaultdict(float)
    for record in all_compensation_records:
        if record.fiscal_year_end:
            exec_totals_by_year[record.fiscal_year_end.year] += record.total_comp_usd

    director_totals_by_year = defaultdict(float)
    for record in all_director_records:
        if record.fiscal_year_end:
            director_totals_by_year[record.fiscal_year_end.year] += record.total_usd

    timeline_years = sorted(set(exec_totals_by_year.keys()) | set(director_totals_by_year.keys()))
    if not timeline_years and year_date:
        timeline_years = [year_date.year]

    ts_labels: List[str] = []
    exec_series: List[float] = []
    director_series: List[float] = []
    combined_series: List[float] = []
    budget_series: List[float] = []
    utilization_series: List[float] = []

    for yr in timeline_years:
        ts_labels.append(str(yr))
        exec_value = round(exec_totals_by_year.get(yr, 0.0), 2)
        director_value = round(director_totals_by_year.get(yr, 0.0), 2)
        exec_series.append(exec_value)
        director_series.append(director_value)
        combined_series.append(round(exec_value + director_value, 2))
        snapshot = league_manager.get_company_cap_snapshot(company_id, date(yr, 12, 31))
        budget_value = ((snapshot or {}).get('budget') or 0.0)
        utilization_value = ((snapshot or {}).get('utilization_pct') or 0.0)
        budget_series.append(round(budget_value, 2))
        utilization_series.append(round(utilization_value, 2))

    compensation_time_series = {
        'labels': ts_labels,
        'exec_totals': exec_series,
        'director_totals': director_series,
        'combined_totals': combined_series,
        'budget': budget_series,
        'utilization_pct': utilization_series,
    }

    raw_ownership_records = [
        record for record in league_manager.beneficial_ownership
        if record.company_id == company_id
    ]
    ownership_rows = []
    exec_person_ids = {item['person_id'] for item in c_suite}
    director_shares = 0
    exec_shares = 0
    as_of_dates = set()
    for record in raw_ownership_records:
        person = league_manager.get_person(record.person_id)
        if record.as_of_date:
            as_of_dates.add(record.as_of_date)
        if person and person.is_director:
            director_shares += record.total_shares
        if (person and person.is_executive) or record.person_id in exec_person_ids:
            exec_shares += record.total_shares
        ownership_rows.append({
            'holder_name': person.full_name if person else (record.person_id or '—'),
            'role': record.role,
            'total_shares': record.total_shares,
            'sole_voting_power': record.sole_voting_power,
            'shared_voting_power': record.shared_voting_power,
            'percent_of_class': record.percent_of_class,
            'as_of_date': record.as_of_date.isoformat() if record.as_of_date else '—',
            'notes': record.notes,
        })

    total_insider_shares = director_shares + exec_shares

    ownership_summary = {
        'director_shares': director_shares,
        'exec_shares': exec_shares,
        'total_shares': total_insider_shares,
        'as_of': max(as_of_dates).isoformat() if as_of_dates else '—'
    }

    company_summary = {
        'exec_total': exec_total,
        'exec_avg_comp': exec_avg_comp,
        'exec_avg_experience': exec_avg_experience,
        'exec_count': exec_count,
        'director_total': director_total,
        'director_avg_total': director_avg_total,
        'director_count': director_count,
        'revenue': revenue,
        'market_cap': market_cap,
        'exec_to_revenue_pct': exec_to_revenue_pct,
        'director_to_revenue_pct': director_to_revenue_pct,
        'total_to_revenue_pct': total_to_revenue_pct,
        'revenue_per_exec': revenue_per_exec,
        'comp_per_exec': comp_per_exec,
        'market_cap_to_pay': market_cap_to_pay,
    }

    comp_mix_chart = {
        'labels': ['Executive Payroll', 'Director Payroll'],
        'values': [round(exec_total, 2), round(director_total, 2)],
    }

    if total_insider_shares:
        exec_pct = (exec_shares / total_insider_shares) * 100
        director_pct = (director_shares / total_insider_shares) * 100
    else:
        exec_pct = director_pct = 0.0

    ownership_mix_chart = {
        'labels': ['Executive Insiders', 'Board Insiders'],
        'values': [round(exec_pct, 2), round(director_pct, 2)],
        'shares': [exec_shares, director_shares],
        'total_shares': total_insider_shares,
    }

    top_owner_rows = sorted(
        ownership_rows,
        key=lambda row: row['total_shares'],
        reverse=True
    )[:6]
    top_owner_chart = {
        'labels': [row['holder_name'] for row in top_owner_rows],
        'shares': [row['total_shares'] for row in top_owner_rows],
        'percent_of_class': [
            row['percent_of_class'] if row['percent_of_class'] is not None else 0
            for row in top_owner_rows
        ],
    }

    return render_template(
        'company_detail.html',
        company=company_dict,
        company_id=company_id,
        cap_info=cap_info,
        c_suite=c_suite,
        board_members=board_members,
        director_compensation=director_comp_records,
        director_policies=director_policies,
        director_comp_summary=director_comp_summary,
        company_summary=company_summary,
        ownership_summary=ownership_summary,
        ownership_rows=ownership_rows,
        all_executives=all_executives,
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data),
        comp_mix_chart=comp_mix_chart,
        ownership_mix_chart=ownership_mix_chart,
        top_owner_chart=top_owner_chart,
        compensation_time_series=compensation_time_series,
        selected_year=year,
        available_years=available_company_years or available_years,
    )


@app.route('/person/<person_id>')
def person_detail(person_id):
    """Player Profile with year filtering"""
    year = get_selected_year()
    person = league_manager.get_person(person_id)
    if not person:
        return "Person not found", 404

    # Get all roles for this person, optionally filtered by year
    available_years = get_available_year_options()
    if year not in available_years and available_years:
        year = available_years[0]
    year_date = parse_year_to_date(year)

    all_records = league_manager.get_compensation_for_person(person_id)
    compensation_records = (
        league_manager.get_compensation_for_person(person_id, year_date)
        if year_date else all_records
    )
    # Fallback to career view when no data exists for the requested season
    if year_date and not compensation_records:
        compensation_records = all_records
        year_date = None

    focus_year = year_date.year if year_date else None
    person_roles = []
    for record in sorted(all_records, key=lambda rec: rec.fiscal_year_end, reverse=True):
        company = league_manager.get_company(record.company_id)
        person_roles.append({
            'company_id': record.company_id,
            'company_name': company.company_name if company else record.company_id,
            'company_ticker': company.ticker if company else '',
            'title': person.current_title,
            'position_type': 'C-Suite' if person.is_executive else 'Director',
            'year': record.fiscal_year_end.year,
            'contract_years': 1,
            'base_salary': record.salary_usd,
            'bonus': record.bonus_usd,
            'stock_awards': record.stock_awards_usd,
            'signing_bonus': record.all_other_comp_usd,
            'share_count': None,
            'total_compensation': record.total_comp_usd,
            'is_focus_year': (focus_year is not None and record.fiscal_year_end.year == focus_year),
        })

    total_earnings = sum(rec.total_comp_usd for rec in all_records)
    years_active = len({rec.fiscal_year_end.year for rec in all_records})
    companies_count = len({rec.company_id for rec in all_records})
    highest_single_year = max((rec.total_comp_usd for rec in all_records), default=0)
    avg_annual = (total_earnings / years_active) if years_active else 0

    career_stats = {
        'total_earnings': total_earnings,
        'years_active': years_active,
        'companies_count': companies_count,
        'avg_annual': avg_annual,
        'highest_single_year': highest_single_year
    }

    person_years = sorted({str(rec.fiscal_year_end.year) for rec in all_records}, reverse=True)

    person_dict = {
        'person_id': person.person_id,
        'name': person.full_name,
        'current_title': person.current_title,
        'is_executive': person.is_executive,
        'is_director': person.is_director,
        'bio_short': person.bio_short,
        'linkedin_url': person.linkedin_url,
        'photo_url': person.photo_url,
        'status': person.status,
        'education': person.education,
        'years_experience': person.years_experience,
    }

    history_records = sorted(all_records, key=lambda rec: rec.fiscal_year_end)
    compensation_history_chart = {
        'labels': [str(rec.fiscal_year_end.year) for rec in history_records],
        'salary': [rec.salary_usd for rec in history_records],
        'bonus': [rec.bonus_usd for rec in history_records],
        'stock': [rec.stock_awards_usd for rec in history_records],
        'total': [rec.total_comp_usd for rec in history_records],
    }

    season_records = compensation_records if year_date else all_records
    season_year_label = str(year_date.year) if year_date else 'Career'
    season_stats = {
        'year_label': season_year_label,
        'total': sum(rec.total_comp_usd for rec in season_records),
        'avg_total': (
            sum(rec.total_comp_usd for rec in season_records) / len(season_records)
            if season_records else 0
        ),
        'salary': sum(rec.salary_usd for rec in season_records),
        'bonus': sum(rec.bonus_usd for rec in season_records),
        'stock': sum(rec.stock_awards_usd for rec in season_records),
        'records': len(season_records),
    }

    return render_template(
        'person_detail.html',
        person=person_dict,
        roles=person_roles,
        career_stats=career_stats,
        compensation_history_chart=compensation_history_chart,
        season_stats=season_stats,
        selected_year=year if year_date else 'career',
        available_years=person_years,
    )


@app.route('/free-agents')
def free_agents():
    """Available executives not currently with companies"""
    year = get_selected_year()
    available_years = get_available_year_options()
    if year not in available_years and available_years:
        year = available_years[0]

    free_agents_list = []

    for person in league_manager.get_free_agents():
        last_role = None
        last_comp = 0

        year_date = parse_year_to_date(year)
        records = league_manager.get_compensation_for_person(person.person_id, year_date)
        if not year_date:
            records = league_manager.get_compensation_for_person(person.person_id)

        if records:
            last_record = max(records, key=lambda r: r.fiscal_year_end)
            last_role = last_record
            last_comp = last_record.total_comp_usd

        if last_role or not year_date:  # Include person if they have a role for the year, or if showing all
            free_agents_list.append({
                'person_id': person.person_id,
                'name': person.full_name,
                'age': None,
                'experience': person.years_experience or 0,
                'education': person.education,
                'last_title': person.current_title if last_role else 'N/A',
                'last_compensation': last_comp,
                'share_count': None,
                'previous_companies': None,
                'last_year': last_role.fiscal_year_end.year if last_role else None
            })

    # Get available years
    return render_template('free_agents.html',
                           free_agents=free_agents_list,
                           selected_year=year,
                           available_years=available_years)


@app.route('/refresh-data')
def refresh_data():
    """Refresh data from company folders"""
    global league_manager, FALLBACK_AVAILABLE_YEARS, USING_SAMPLE_DATA

    if DATA_SOURCE == 'fortune10' or not folder_loader:
        league_manager = load_fortune10_sample_dataset()
        return "Sample Fortune 10 data reloaded. Switch DATA_SOURCE to 'gcs' once you migrate to Firebase or cloud storage."

    year = get_selected_year()
    load_all = request.args.get('all_years', 'false').lower() == 'true'

    if load_all:
        load_result = folder_loader.load_all_company_data(load_all_years=True)
    else:
        load_result = folder_loader.load_all_company_data(specific_year=year)

    if load_result['status'] == 'success':
        # Get the updated league manager directly
        league_manager = folder_loader.get_league_manager()
        FALLBACK_AVAILABLE_YEARS.clear()
        USING_SAMPLE_DATA = False

        message = (
            f"Data refreshed! Loaded {load_result['companies_count']} companies, "
            f"{load_result['people_count']} people, {load_result['executive_comp_count']} compensation rows "
            f"for year {year if not load_all else 'all years'}"
        )
        if load_result.get('warnings'):
            message += "\nWarnings:\n" + "\n".join(f" - {warning}" for warning in load_result['warnings'])
        return message
    else:
        message = f"Error refreshing data: {load_result.get('message')}"
        if load_result.get('warnings'):
            message += "\nWarnings:\n" + "\n".join(f" - {warning}" for warning in load_result['warnings'])
        if ALLOW_SAMPLE_FALLBACK:
            league_manager = load_fortune10_sample_dataset()
            return message + "\nLoaded bundled Fortune 10 sample data instead."
        return message + "\nExisting data remains unchanged."


@app.route('/api/company-folders')
def list_company_folders():
    """API endpoint to list available company folders with years"""
    if USING_SAMPLE_DATA:
        folders = [company.company_name for company in league_manager.companies.values()]
        company_years = {
            company.company_name: sorted(
                {
                    str(record.fiscal_year_end.year)
                    for record in league_manager.get_company_compensation(company.company_id)
                },
                reverse=True,
            )
            for company in league_manager.companies.values()
        }
        return jsonify({
            'folders': folders,
            'company_years': company_years,
            'files_by_company_year': {},
            'available_years': get_available_year_options()
        })

    try:
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

        response = {
            'folders': folders,
            'company_years': company_years,
            'files_by_company_year': company_files,
            'available_years': get_available_year_options()
        }
        return jsonify(response)
    except Exception as error:
        return jsonify({
            'error': str(error),
            'details': 'Unable to access bucket contents.',
            'folders': [],
            'company_years': {},
            'files_by_company_year': {},
            'available_years': get_available_year_options()
        }), 500


@app.route('/api/league-stats')
def league_stats():
    """API endpoint for league-wide statistics"""
    year = get_selected_year()
    fiscal_year = parse_year_to_date(year)
    stats = league_manager.get_league_statistics(fiscal_year)
    stats['year'] = year
    return jsonify(stats)


@app.route('/api/company/<company_id>')
def company_api(company_id):
    """API endpoint for company data"""
    year = get_selected_year()
    company = league_manager.get_company(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    company_data = company_to_template_dict(company)
    year_date = parse_year_to_date(year)
    cap_info = league_manager.get_company_cap_snapshot(company_id, year_date)

    if year:
        company_data['year_data'] = {
            'year': year,
            'cap_info': cap_info,
            'executive_count': len(league_manager.get_company_compensation(company_id, year_date)),
        }

    company_data['cap_info'] = cap_info
    return jsonify(company_data)


@app.route('/api/person/<person_id>')
def person_api(person_id):
    """API endpoint for person data"""
    year = get_selected_year()
    person = league_manager.get_person(person_id)
    if not person:
        return jsonify({'error': 'Person not found'}), 404

    records = league_manager.get_compensation_for_person(person_id)
    compensation_breakdown = {
        'salary_usd': sum(r.salary_usd for r in records),
        'bonus_usd': sum(r.bonus_usd for r in records),
        'stock_awards_usd': sum(r.stock_awards_usd for r in records),
        'all_other_comp_usd': sum(r.all_other_comp_usd for r in records),
        'total_comp_usd': sum(r.total_comp_usd for r in records),
    }

    person_data = {
        'person_id': person.person_id,
        'full_name': person.full_name,
        'current_title': person.current_title,
        'is_executive': person.is_executive,
        'is_director': person.is_director,
        'status': person.status,
        'years_experience': person.years_experience,
        'education': person.education,
        'compensation_breakdown': compensation_breakdown,
    }

    year_date = parse_year_to_date(year)
    if year:
        filtered = [r for r in records if dates_share_year(r.fiscal_year_end, year_date)]
        person_data['year_data'] = {
            'year': year,
            'total_earnings': sum(r.total_comp_usd for r in filtered),
            'role_count': len(filtered),
            'companies': list({r.company_id for r in filtered})
        }

    return jsonify(person_data)


@app.route('/api/years')
def available_years():
    """API endpoint to get all available years"""
    years = get_available_year_options()
    return jsonify({
        'years': years,
        'default_year': DEFAULT_YEAR,
        'current_selection': get_selected_year()
    })


@app.route('/api/diagnostic')
def diagnostic():
    """Diagnostic endpoint to check system status"""
    if DATA_SOURCE == 'fortune10':
        return jsonify({
            'data_source': 'fortune10',
            'companies_loaded': len(league_manager.companies),
            'people_loaded': len(league_manager.people),
            'executive_records_loaded': len(league_manager.executive_comp),
            'available_years': get_available_year_options(),
        })
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
            'executive_records_loaded': len(league_manager.executive_comp),
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
