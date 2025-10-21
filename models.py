# models.py - normalized core schema for ExecuCap
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Core Entities
# ---------------------------------------------------------------------------


@dataclass
class Company:
    """Represents a public company covered by the dataset."""

    company_id: str  # slug-like ID (e.g., walmart, amazon)
    company_name: str
    ticker: str
    fiscal_year_end: date
    source_url: str
    notes: Optional[str] = None
    market_cap_usd: Optional[float] = None
    revenue_usd: Optional[float] = None
    cap_budget_usd: Optional[float] = None
    sector: Optional[str] = None
    founded_year: Optional[int] = None


@dataclass
class Person:
    """Represents an executive or director."""

    person_id: str  # slug-like ID (e.g., c_douglas_mcmillon)
    full_name: str
    current_title: str
    is_executive: bool = False
    is_director: bool = False
    bio_short: Optional[str] = None
    linkedin_url: Optional[str] = None
    photo_url: Optional[str] = None
    years_experience: Optional[int] = None
    education: Optional[str] = None
    status: Optional[str] = None  # Active, Retired, etc.


# ---------------------------------------------------------------------------
# Compensation & Ownership Tables
# ---------------------------------------------------------------------------


@dataclass
class ExecutiveCompensation:
    """Summary Compensation Table entry for a named executive officer."""

    company_id: str
    person_id: str
    fiscal_year_end: date
    salary_usd: float = 0.0
    bonus_usd: float = 0.0
    stock_awards_usd: float = 0.0
    option_awards_usd: float = 0.0
    non_equity_incentive_usd: float = 0.0
    pension_change_usd: float = 0.0
    all_other_comp_usd: float = 0.0
    total_comp_usd: float = 0.0
    source: str = ""


@dataclass
class ExecutiveEquityGrant:
    """Plan-based award (RSU/PSU/Option) issued to an executive."""

    company_id: str
    person_id: str
    grant_date: date
    award_type: str
    threshold_units: Optional[int] = None
    target_units: Optional[int] = None
    max_units: Optional[int] = None
    grant_date_fair_value_usd: Optional[float] = None
    vesting_schedule_short: Optional[str] = None
    source: str = ""


@dataclass
class BeneficialOwnershipRecord:
    """Ownership disclosure from the proxy statement."""

    company_id: str
    person_id: str
    role: str
    total_shares: int
    sole_voting_power: Optional[int] = None
    shared_voting_power: Optional[int] = None
    percent_of_class: Optional[float] = None
    as_of_date: date = field(default_factory=date.today)
    notes: Optional[str] = None


@dataclass
class DirectorCompensation:
    """Director compensation table entry."""

    company_id: str
    person_id: str
    fiscal_year_end: date
    fees_cash_usd: float = 0.0
    stock_awards_usd: float = 0.0
    all_other_comp_usd: float = 0.0
    total_usd: float = 0.0
    source: str = ""


@dataclass
class DirectorProfile:
    """Director biography and governance metadata."""

    company_id: str
    person_id: str
    role: str
    independent: bool
    director_since: Optional[int] = None
    lead_independent_director: bool = False
    committees: Optional[str] = None
    primary_occupation: Optional[str] = None
    other_public_boards: Optional[str] = None


@dataclass
class DirectorCompPolicy:
    """Board compensation policy components."""

    company_id: str
    component: str
    amount_usd: Optional[float] = None
    unit: Optional[str] = None  # USD, RSU, etc.
    notes: Optional[str] = None


@dataclass
class SourceManifestEntry:
    """Metadata about source files used to populate the dataset."""

    company_id: str
    file_path: str
    description: str
    last_updated: date


# ---------------------------------------------------------------------------
# Aggregate / Repository
# ---------------------------------------------------------------------------


class LeagueManager:
    """
    Central repository for ExecuCap data. Stores normalized entities and provides
    helper methods for querying across compensation, equity, and board tables.
    """

    def __init__(self):
        self.companies: Dict[str, Company] = {}
        self.people: Dict[str, Person] = {}

        # Compensation datasets
        self.executive_comp: List[ExecutiveCompensation] = []
        self.equity_grants: List[ExecutiveEquityGrant] = []
        self.director_comp: List[DirectorCompensation] = []
        self.beneficial_ownership: List[BeneficialOwnershipRecord] = []
        self.director_profiles: List[DirectorProfile] = []
        self.director_policies: List[DirectorCompPolicy] = []
        self.source_manifest: List[SourceManifestEntry] = []

        # Derived indexes for quick lookups
        self._exec_comp_index: Dict[Tuple[str, str, date], ExecutiveCompensation] = {}

    # ------------------------------------------------------------------
    # Entity registration helpers
    # ------------------------------------------------------------------

    def add_company(self, company: Company) -> None:
        self.companies[company.company_id] = company

    def add_person(self, person: Person) -> None:
        self.people[person.person_id] = person

    def add_executive_comp(self, record: ExecutiveCompensation) -> None:
        key = (record.company_id, record.person_id, record.fiscal_year_end)
        existing = self._exec_comp_index.get(key)
        if existing:
            self.executive_comp = [
                r
                for r in self.executive_comp
                if not (r.company_id == record.company_id and r.person_id == record.person_id and r.fiscal_year_end == record.fiscal_year_end)
            ]
        self._exec_comp_index[key] = record
        self.executive_comp.append(record)

    def add_equity_grant(self, record: ExecutiveEquityGrant) -> None:
        self.equity_grants.append(record)

    def add_beneficial_ownership(self, record: BeneficialOwnershipRecord) -> None:
        self.beneficial_ownership.append(record)

    def add_director_comp(self, record: DirectorCompensation) -> None:
        self.director_comp.append(record)

    def add_director_profile(self, profile: DirectorProfile) -> None:
        self.director_profiles.append(profile)

    def add_director_policy(self, policy: DirectorCompPolicy) -> None:
        self.director_policies.append(policy)

    def add_source_manifest_entry(self, entry: SourceManifestEntry) -> None:
        self.source_manifest.append(entry)

    # ------------------------------------------------------------------
    # Query helpers used by the web layer
    # ------------------------------------------------------------------

    def get_company(self, company_id: str) -> Optional[Company]:
        return self.companies.get(company_id)

    def get_person(self, person_id: str) -> Optional[Person]:
        return self.people.get(person_id)

    def get_compensation_for_person(
        self,
        person_id: str,
        fiscal_year: Optional[date] = None,
    ) -> List[ExecutiveCompensation]:
        records = [r for r in self.executive_comp if r.person_id == person_id]
        if fiscal_year:
            records = [r for r in records if r.fiscal_year_end == fiscal_year]
        return sorted(records, key=lambda r: r.fiscal_year_end, reverse=True)

    def get_company_compensation(
        self,
        company_id: str,
        fiscal_year: Optional[date] = None,
    ) -> List[ExecutiveCompensation]:
        records = [r for r in self.executive_comp if r.company_id == company_id]
        if fiscal_year:
            records = [r for r in records if r.fiscal_year_end == fiscal_year]
        return sorted(records, key=lambda r: r.total_comp_usd, reverse=True)

    def get_top_earners(
        self,
        fiscal_year: Optional[date] = None,
        limit: int = 10,
    ) -> List[ExecutiveCompensation]:
        records = self.executive_comp
        if fiscal_year:
            records = [r for r in records if r.fiscal_year_end == fiscal_year]
        return sorted(records, key=lambda r: r.total_comp_usd, reverse=True)[:limit]

    def get_available_years(self) -> List[date]:
        return sorted({record.fiscal_year_end for record in self.executive_comp}, reverse=True)

    def get_director_profiles_for_company(self, company_id: str) -> List[DirectorProfile]:
        return [profile for profile in self.director_profiles if profile.company_id == company_id]

    def get_top_earners_league_wide(
        self,
        limit: int = 10,
        fiscal_year: Optional[date] = None,
    ) -> List[Tuple[ExecutiveCompensation, Company, Person]]:
        records = self.get_top_earners(fiscal_year=fiscal_year, limit=limit)
        result: List[Tuple[ExecutiveCompensation, Company, Person]] = []
        for record in records:
            company = self.get_company(record.company_id)
            person = self.get_person(record.person_id)
            if company and person:
                result.append((record, company, person))
        return result

    def get_company_cap_snapshot(
        self,
        company_id: str,
        fiscal_year: Optional[date] = None,
    ) -> Dict[str, float]:
        company = self.get_company(company_id)
        if not company:
            return {}

        compensation = self.get_company_compensation(company_id, fiscal_year)
        total_spent = sum(record.total_comp_usd for record in compensation)
        budget = company.cap_budget_usd or total_spent
        remaining = (budget - total_spent) if budget is not None else 0.0
        utilization = (total_spent / budget * 100) if budget else 100.0

        return {
            "total_spent": total_spent,
            "budget": budget,
            "remaining": remaining,
            "utilization_pct": utilization,
        }

    def get_league_standings(self) -> List[Company]:
        return sorted(
            self.companies.values(),
            key=lambda company: company.market_cap_usd or 0,
            reverse=True,
        )

    def get_companies_over_budget(self, fiscal_year: Optional[date] = None) -> List[Company]:
        over_budget = []
        for company in self.companies.values():
            cap = self.get_company_cap_snapshot(company.company_id, fiscal_year)
            if cap and cap["budget"] and cap["remaining"] < 0:
                over_budget.append(company)
        return over_budget

    def get_league_statistics(self, fiscal_year: Optional[date] = None) -> Dict[str, float]:
        records = self.executive_comp
        if fiscal_year:
            records = [r for r in records if r.fiscal_year_end == fiscal_year]

        total_spent = sum(r.total_comp_usd for r in records)
        budgets = [
            self.get_company_cap_snapshot(r.company_id, fiscal_year)["budget"]
            for r in records
            if self.get_company_cap_snapshot(r.company_id, fiscal_year).get("budget")
        ]
        total_budget = sum(budgets) if budgets else 0.0
        avg_utilization = (total_spent / total_budget * 100) if total_budget else 100.0

        return {
            "total_companies": len(self.companies),
            "total_people": len(self.people),
            "total_roles": len(self.executive_comp),
            "free_agents_count": len(self.get_free_agents()),
            "companies_over_budget": len(self.get_companies_over_budget(fiscal_year)),
            "total_league_spending": total_spent,
            "total_league_budget": total_budget,
            "avg_cap_utilization": avg_utilization,
        }

    def get_free_agents(self) -> List[Person]:
        return [
            person
            for person in self.people.values()
            if (person.is_executive or person.is_director)
            and (person.status or "").lower() == "retired"
        ]


__all__ = [
    "Company",
    "Person",
    "ExecutiveCompensation",
    "ExecutiveEquityGrant",
    "BeneficialOwnershipRecord",
    "DirectorCompensation",
    "DirectorProfile",
    "DirectorCompPolicy",
    "SourceManifestEntry",
    "LeagueManager",
]
