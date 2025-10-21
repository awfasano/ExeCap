"""Adapters that convert the curated Fortune 10 dataset into the normalized models."""

from __future__ import annotations

import re
from datetime import date
from typing import Dict, Iterable, List, Optional, Set, Tuple

from fortune10_exec_data import (
    Company as SourceCompany,
    Person as SourcePerson,
    Role as SourceRole,
    build_data,
)
from models import (
    Company,
    DirectorCompensation,
    DirectorCompPolicy,
    DirectorProfile,
    ExecutiveCompensation,
    LeagueManager,
    Person,
)

# Financial context used to populate market caps and executive cap budgets.
_FINANCIAL_SNAPSHOT: Dict[str, Dict[str, float]] = {
    "Walmart Inc.": {"market_cap": 450_000_000_000, "revenue": 648_100_000_000, "exec_budget": 125_000_000},
    "Amazon.com, Inc.": {"market_cap": 1_650_000_000_000, "revenue": 554_000_000_000, "exec_budget": 150_000_000},
    "UnitedHealth Group Incorporated": {"market_cap": 460_000_000_000, "revenue": 371_600_000_000, "exec_budget": 120_000_000},
    "Apple Inc.": {"market_cap": 2_680_000_000_000, "revenue": 383_300_000_000, "exec_budget": 220_000_000},
    "CVS Health Corporation": {"market_cap": 96_000_000_000, "revenue": 357_800_000_000, "exec_budget": 110_000_000},
    "Berkshire Hathaway Inc.": {"market_cap": 875_000_000_000, "revenue": 364_500_000_000, "exec_budget": 90_000_000},
    "Exxon Mobil Corporation": {"market_cap": 420_000_000_000, "revenue": 344_600_000_000, "exec_budget": 140_000_000},
    "Alphabet Inc.": {"market_cap": 1_940_000_000_000, "revenue": 307_400_000_000, "exec_budget": 180_000_000},
    "McKesson Corporation": {"market_cap": 75_000_000_000, "revenue": 301_500_000_000, "exec_budget": 95_000_000},
    "Chevron Corporation": {"market_cap": 290_000_000_000, "revenue": 246_300_000_000, "exec_budget": 135_000_000},
}

DEFAULT_SOURCE_URL = "https://www.sec.gov/edgar/browse/"


class Fortune10LoadError(RuntimeError):
    """Raised when the curated dataset cannot be converted into league models."""


def _slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "unknown"


def _infer_fiscal_year_end(company: SourceCompany) -> date:
    years = [
        role.year
        for executive in company.executives
        for role in executive.roles
    ]
    fiscal_year = max(years) if years else date.today().year
    return date(fiscal_year, 12, 31)


def _convert_company(source: SourceCompany) -> Company:
    slug = _slugify(source.name)
    fiscal_year_end = _infer_fiscal_year_end(source)
    snapshot = _FINANCIAL_SNAPSHOT.get(source.name, {})

    return Company(
        company_id=slug,
        company_name=source.name,
        ticker=source.ticker,
        fiscal_year_end=fiscal_year_end,
        source_url=DEFAULT_SOURCE_URL,
        market_cap_usd=snapshot.get("market_cap"),
        revenue_usd=snapshot.get("revenue"),
        cap_budget_usd=snapshot.get("exec_budget"),
        notes=None,
        sector=getattr(source, "sector", None),
        founded_year=getattr(source, "founded", None),
    )


def _convert_person(source: SourcePerson, is_director: bool = False) -> Person:
    slug = _slugify(source.name)
    return Person(
        person_id=slug,
        full_name=source.name,
        current_title=source.roles[-1].title if source.roles else source.name,
        is_executive=not is_director,
        is_director=is_director,
        years_experience=None,
        education=source.education,
        status=source.status,
    )


def _convert_role_to_compensation(
    company_id: str,
    person_id: str,
    role: SourceRole,
) -> ExecutiveCompensation:
    fiscal_year_end = date(role.year, 12, 31)
    total_comp = role.total_compensation()

    return ExecutiveCompensation(
        company_id=company_id,
        person_id=person_id,
        fiscal_year_end=fiscal_year_end,
        salary_usd=role.base_salary,
        bonus_usd=role.bonus,
        stock_awards_usd=role.stock_awards,
        option_awards_usd=0.0,
        non_equity_incentive_usd=0.0,
        pension_change_usd=0.0,
        all_other_comp_usd=role.signing_bonus,
        total_comp_usd=total_comp,
        source=f"{role.year} Proxy Statement",
    )


def _attach_board_members(
    league: LeagueManager,
    company: SourceCompany,
    company_id: str,
    fiscal_year_end: date,
) -> None:
    cash_retainer = 150_000
    stock_grant = 175_000
    policy_entries_added = False

    for idx, member_name in enumerate(company.board_members):
        slug = _slugify(member_name)
        if slug in league.people:
            continue

        person = Person(
            person_id=slug,
            full_name=member_name,
            current_title="Director",
            is_director=True,
            status="Active",
        )
        league.add_person(person)
        profile = DirectorProfile(
            company_id=company_id,
            person_id=slug,
            role="Director",
            independent=True,
            director_since=None,
            lead_independent_director=False,
            committees=None,
            primary_occupation=None,
            other_public_boards=None,
        )
        league.add_director_profile(profile)

        director_comp = DirectorCompensation(
            company_id=company_id,
            person_id=slug,
            fiscal_year_end=fiscal_year_end,
            fees_cash_usd=cash_retainer,
            stock_awards_usd=stock_grant,
            all_other_comp_usd=25_000 if idx % 3 == 0 else 0,
            total_usd=cash_retainer + stock_grant + (25_000 if idx % 3 == 0 else 0),
            source=f"{fiscal_year_end.year} Proxy Statement (illustrative)",
        )
        league.add_director_comp(director_comp)

        if not policy_entries_added:
            league.add_director_policy(DirectorCompPolicy(
                company_id=company_id,
                component="Annual Cash Retainer",
                amount_usd=cash_retainer,
                unit="USD",
                notes="Paid quarterly to independent directors.",
            ))
            league.add_director_policy(DirectorCompPolicy(
                company_id=company_id,
                component="Annual RSU Grant",
                amount_usd=stock_grant,
                unit="RSU",
                notes="Vests on the first anniversary of the grant date.",
            ))
            policy_entries_added = True


def _extract_years(compensation: Iterable[ExecutiveCompensation]) -> Set[date]:
    return {record.fiscal_year_end for record in compensation}


def load_fortune10_league() -> Tuple[LeagueManager, Set[date]]:
    """Populate a LeagueManager with the curated Fortune 10 dataset."""

    source_companies = build_data()
    if not source_companies:
        raise Fortune10LoadError("fortune10_exec_data.build_data() returned no companies.")

    league = LeagueManager()

    for source_company in source_companies:
        league_company = _convert_company(source_company)
        league.add_company(league_company)

        for source_person in source_company.executives:
            person = _convert_person(source_person)
            league.add_person(person)

            for role in source_person.roles:
                compensation = _convert_role_to_compensation(
                    company_id=league_company.company_id,
                    person_id=person.person_id,
                    role=role,
                )
                league.add_executive_comp(compensation)

        _attach_board_members(league, source_company, league_company.company_id, league_company.fiscal_year_end)

    available_years = _extract_years(league.executive_comp)
    return league, available_years


__all__ = ["load_fortune10_league", "Fortune10LoadError"]
