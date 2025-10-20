"""Utilities for loading the curated Fortune 10 executive dataset into the core league models."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Set, Tuple

from models import LeagueManager, Company as LeagueCompany, Person as LeaguePerson, Role as LeagueRole
from fortune10_exec_data import build_data, Company as SourceCompany, Person as SourcePerson, Role as SourceRole

# Rough market-cap and revenue snapshots (USD) to make league standings meaningful.
_FINANCIAL_SNAPSHOT = {
    "Walmart Inc.": {"market_cap": 450_000_000_000, "revenue": 648_100_000_000, "exec_budget": 125_000_000},
    "Amazon.com, Inc.": {"market_cap": 1_650_000_000_000, "revenue": 554_000_000_000, "exec_budget": 150_000_000},
    "UnitedHealth Group Incorporated": {"market_cap": 460_000_000_000, "revenue": 371_600_000_000},
    "Apple Inc.": {"market_cap": 2_680_000_000_000, "revenue": 383_300_000_000, "exec_budget": 220_000_000},
    "CVS Health Corporation": {"market_cap": 96_000_000_000, "revenue": 357_800_000_000},
    "Berkshire Hathaway Inc.": {"market_cap": 875_000_000_000, "revenue": 364_500_000_000, "exec_budget": 90_000_000},
    "Exxon Mobil Corporation": {"market_cap": 420_000_000_000, "revenue": 344_600_000_000},
    "Alphabet Inc.": {"market_cap": 1_940_000_000_000, "revenue": 307_400_000_000, "exec_budget": 180_000_000},
    "McKesson Corporation": {"market_cap": 75_000_000_000, "revenue": 301_500_000_000},
    "Chevron Corporation": {"market_cap": 290_000_000_000, "revenue": 246_300_000_000},
}


class Fortune10LoadError(RuntimeError):
    """Raised when the curated dataset cannot be converted into league models."""


def _extract_years(source_companies: Iterable[SourceCompany]) -> Set[int]:
    years: Set[int] = set()
    for company in source_companies:
        for executive in company.executives:
            for role in executive.roles:
                years.add(role.year)
    if not years:
        years.add(2024)
    return years


def _position_type_for_role(source_role: SourceRole) -> str:
    title = (source_role.title or "").lower()
    source_type = (source_role.position_type or "").lower()

    board_keywords = ("chair", "director", "board")
    if any(keyword in title for keyword in board_keywords):
        return "Board"
    if source_type in {"board", "director"}:
        return "Board"
    return "C-Suite"


def _estimate_exec_budget(company_name: str, total_comp: float) -> float:
    snapshot = _FINANCIAL_SNAPSHOT.get(company_name, {})
    if snapshot.get("exec_budget"):
        return float(snapshot["exec_budget"])

    if total_comp <= 0:
        return 50_000_000.0

    # Give every team at least a 10% buffer above current spending.
    return round(total_comp * 1.15, -3)


def _parse_experience(raw_experience: Optional[str]) -> int:
    if raw_experience is None:
        return 15
    if isinstance(raw_experience, (int, float)):
        return int(raw_experience)

    match = re.search(r"(\d+)", raw_experience)
    if match:
        return int(match.group(1))

    return 15


def _sanitize_status(status: Optional[str]) -> str:
    if not status:
        return "Active"
    status_normalized = status.strip().lower()
    if status_normalized in {"retired", "inactive"}:
        return "Retired"
    return "Active"


def _ensure_person(
    league: LeagueManager,
    source_person: SourcePerson,
    default_age: int,
) -> LeaguePerson:
    if source_person.person_id in league.people:
        return league.people[source_person.person_id]

    person = LeaguePerson(
        person_id=source_person.person_id,
        name=source_person.name,
        age=source_person.age or default_age,
        experience=_parse_experience(source_person.experience),
        education=source_person.education or "MBA",
        status=_sanitize_status(source_person.status),
        previous_companies=source_person.previous_companies or [],
    )
    league.add_person(person)
    return person


def _add_roles_for_person(
    league: LeagueManager,
    league_company: LeagueCompany,
    league_person: LeaguePerson,
    source_person: SourcePerson,
) -> None:
    for source_role in source_person.roles:
        league_role = LeagueRole(
            person_id=league_person.person_id,
            company_id=league_company.company_id,
            title=source_role.title,
            position_type=_position_type_for_role(source_role),
            year=source_role.year,
            contract_years=source_role.contract_years,
            base_salary=source_role.base_salary,
            bonus=source_role.bonus,
            stock_awards=source_role.stock_awards,
            signing_bonus=source_role.signing_bonus,
        )
        league.add_role(league_role)


def _add_board_members(
    league: LeagueManager,
    league_company: LeagueCompany,
    board_members: List[str],
    next_person_id: int,
    default_year: int,
) -> int:
    existing_company_names = {person.name for person in league_company.board_members}
    existing_league_names = {person.name for person in league.people.values()}

    for member_name in board_members:
        clean_name = member_name.strip()
        if clean_name in existing_company_names or clean_name in existing_league_names:
            continue

        person = LeaguePerson(
            person_id=next_person_id,
            name=clean_name,
            age=58,
            experience=25,
            education="Board Certified",
            status="Active",
            previous_companies=[],
        )
        league.add_person(person)

        role = LeagueRole(
            person_id=person.person_id,
            company_id=league_company.company_id,
            title="Board Director",
            position_type="Board",
            year=default_year,
            contract_years=1,
            base_salary=0,
            bonus=0,
            stock_awards=0,
            signing_bonus=0,
        )
        league.add_role(role)

        next_person_id += 1
        existing_company_names.add(clean_name)
        existing_league_names.add(clean_name)

    return next_person_id


def load_fortune10_league() -> Tuple[LeagueManager, Set[int]]:
    """Return a LeagueManager populated with the curated Fortune 10 executives."""
    source_companies = build_data()
    if not source_companies:
        raise Fortune10LoadError("fortune10_exec_data.build_data() returned no companies.")

    league = LeagueManager()
    available_years = _extract_years(source_companies)

    max_existing_id = 0
    for company in source_companies:
        for executive in company.executives:
            max_existing_id = max(max_existing_id, executive.person_id)

    next_person_id = max_existing_id + 1 or 1

    for source_company in source_companies:
        total_comp = sum(
            role.total_compensation()
            for executive in source_company.executives
            for role in executive.roles
        )

        financials = _FINANCIAL_SNAPSHOT.get(source_company.name, {})
        company = LeagueCompany(
            company_id=source_company.company_id,
            name=source_company.name,
            ticker=source_company.ticker or "UNK",
            sector=source_company.sector or "Unknown",
            market_cap=financials.get("market_cap", source_company.market_cap or 0),
            revenue=financials.get("revenue", source_company.revenue or 0),
            exec_budget=_estimate_exec_budget(source_company.name, total_comp),
            founded=source_company.founded or 2000,
        )
        league.add_company(company)

        default_age = 52
        for source_person in source_company.executives:
            league_person = _ensure_person(league, source_person, default_age)
            _add_roles_for_person(league, company, league_person, source_person)

        next_person_id = _add_board_members(
            league,
            company,
            source_company.board_members,
            next_person_id,
            max(available_years) if available_years else 2024,
        )

    return league, available_years


__all__ = ["load_fortune10_league", "Fortune10LoadError"]
