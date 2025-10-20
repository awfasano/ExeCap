"""
fortune10_exec_data_with_shares.py
=================================

This module extends the original Fortune 10 executive dataset by
introducing an optional ``share_count`` attribute to the ``Role``
dataclass.  In many proxy statements, stock and option awards are
reported both as a fair‑value dollar figure and as the number of
shares or share units granted.  Recording share counts alongside
monetary values makes it possible to re‑value awards if a company’s
share price changes after the grant date.

The data structures mirror those in ``fortune10_exec_data.py`` with
the addition of ``share_count``.  Where share counts were not
disclosed or collected, the field is left as ``None``.  This file
does not attempt to calculate current values of stock awards.

"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Role:
    """Represents a single role an executive holds at a company.

    The ``share_count`` field is optional and represents the number of
    shares (or RSUs/options) granted for equity awards.  When share
    counts were not disclosed in the source materials, this field is
    set to ``None``.
    """
    person_id: int
    company_id: int
    title: str
    position_type: str  # e.g. "CEO", "CFO", "COO", etc.
    year: int
    contract_years: int
    base_salary: float
    bonus: float
    stock_awards: float
    signing_bonus: float = 0.0
    share_count: Optional[float] = None

    def total_compensation(self) -> float:
        """Return the sum of all cash and equity compensation."""
        return (
            self.base_salary
            + self.bonus
            + self.stock_awards
            + self.signing_bonus
        )


@dataclass
class Person:
    """Represents an individual executive and their career history."""
    person_id: int
    name: str
    age: Optional[int] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    status: str = "active"
    previous_companies: Optional[List[str]] = None
    roles: List[Role] = field(default_factory=list)

    def add_role(self, role: Role) -> None:
        self.roles.append(role)

    def career_earnings(self) -> float:
        return sum(r.total_compensation() for r in self.roles)


@dataclass
class Company:
    """Represents a company in the Fortune 10 list."""
    company_id: int
    name: str
    ticker: str
    sector: str
    market_cap: Optional[float] = None
    revenue: Optional[float] = None
    exec_budget: Optional[float] = None
    founded: Optional[int] = None
    executives: List[Person] = field(default_factory=list)
    board_members: List[str] = field(default_factory=list)

    def add_executive(self, person: Person) -> None:
        self.executives.append(person)


def build_data() -> List[Company]:
    """Build and return a list of Company objects populated with executives and directors.

    The data are identical to those in ``fortune10_exec_data.py`` but include a
    ``share_count`` field for equity awards.  Because share counts were not
    collected during initial research, the field is left as ``None`` in every
    entry.  Users can update these values if share counts become available.
    """
    from fortune10_exec_data import build_data as build_original

    original_companies = build_original()
    # Convert original data to include share_count=None
    new_companies: List[Company] = []
    for orig in original_companies:
        new_company = Company(
            company_id=orig.company_id,
            name=orig.name,
            ticker=orig.ticker,
            sector=orig.sector,
            market_cap=orig.market_cap,
            revenue=orig.revenue,
            exec_budget=orig.exec_budget,
            founded=orig.founded,
            board_members=list(orig.board_members),
        )
        # Copy executives and their roles
        for person in orig.executives:
            new_person = Person(
                person_id=person.person_id,
                name=person.name,
                age=person.age,
                experience=person.experience,
                education=person.education,
                status=person.status,
                previous_companies=person.previous_companies,
            )
            for role in person.roles:
                # Set share_count to None by default.  For certain Walmart executives
                # we provide the number of unvested and unearned shares disclosed in
                # Walmart’s 2024 proxy statement (see the "Outstanding Equity Awards
                # at Fiscal 2024 Year‑End" table).  The share_count represents the
                # sum of service‑based restricted stock units that have not vested
                # and performance‑based units that have not yet been earned.
                share_count = None
                if orig.name == "Walmart Inc.":
                    # assign share counts based on the executive's name
                    if person.name == "Doug McMillon":
                        share_count = 1_552_575  # 1,070,625 unvested + 481,950 unearned
                    elif person.name == "John David Rainey":
                        share_count = 910_038  # 713,361 unvested + 196,677 unearned
                    elif person.name == "Suresh Kumar":
                        share_count = 831_276  # 597,387 + 233,889
                    elif person.name == "John Furner":
                        share_count = 831_276  # 597,387 + 233,889
                    elif person.name == "Kathryn McLay":
                        share_count = 699_144  # 475,884 + 223,260
                    elif person.name == "Chris Nicholas":
                        share_count = 452_939  # 304,100 + 148,839
                new_role = Role(
                    person_id=role.person_id,
                    company_id=role.company_id,
                    title=role.title,
                    position_type=role.position_type,
                    year=role.year,
                    contract_years=role.contract_years,
                    base_salary=role.base_salary,
                    bonus=role.bonus,
                    stock_awards=role.stock_awards,
                    signing_bonus=role.signing_bonus,
                    share_count=share_count,
                )
                new_person.add_role(new_role)
            new_company.add_executive(new_person)
        new_companies.append(new_company)
    return new_companies


if __name__ == "__main__":
    # Print a summary of the data with share_count placeholder
    data = build_data()
    for company in data:
        print(
            f"{company.name} ({company.ticker}) – Executives:{len(company.executives)}; "
            f"Board members:{len(company.board_members)}"
        )
