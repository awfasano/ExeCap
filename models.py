# models.py
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Role:
    """Represents a role/position held by a person at a company"""
    person_id: int
    company_id: int
    title: str
    position_type: str  # 'C-Suite' or 'Board'
    year: int
    contract_years: int
    base_salary: float
    bonus: float = 0
    stock_awards: float = 0
    signing_bonus: float = 0
    share_count: Optional[float] = None

    @property
    def total_compensation(self) -> float:
        """Calculate total compensation for this role"""
        return (self.base_salary + self.bonus +
                self.stock_awards + self.signing_bonus)

    def to_dict(self) -> Dict:
        """Convert role to dictionary"""
        return {
            'person_id': self.person_id,
            'company_id': self.company_id,
            'title': self.title,
            'position_type': self.position_type,
            'year': self.year,
            'contract_years': self.contract_years,
            'base_salary': self.base_salary,
            'bonus': self.bonus,
            'stock_awards': self.stock_awards,
            'signing_bonus': self.signing_bonus,
            'share_count': self.share_count,
            'total_compensation': self.total_compensation
        }


class Person:
    """Represents an executive or board member"""

    def __init__(self, person_id: int, name: str, age: int = 45,
                 experience: int = 10, education: str = "MBA",
                 status: str = "Active", previous_companies: List[str] = None):
        self.person_id = person_id
        self.name = name
        self.age = age
        self.experience = experience
        self.education = education
        self.status = status  # 'Active' or 'Retired'
        self.previous_companies = previous_companies or []
        self.roles: List[Role] = []  # All roles this person has held
        self.current_role: Optional[Role] = None

    def add_role(self, role: Role) -> None:
        """Add a role to this person's history"""
        self.roles.append(role)
        # Update current role if it's the most recent
        if not self.current_role or role.year >= self.current_role.year:
            self.current_role = role

    @property
    def is_free_agent(self) -> bool:
        """Check if person is available (retired/free agent)"""
        return self.status == "Retired"

    @property
    def total_career_earnings(self) -> float:
        """Calculate total career earnings across all roles"""
        return sum(role.total_compensation for role in self.roles)

    @property
    def years_active(self) -> int:
        """Calculate number of years active"""
        if not self.roles:
            return 0
        years = set(role.year for role in self.roles)
        return len(years)

    @property
    def average_annual_compensation(self) -> float:
        """Calculate average annual compensation"""
        if self.years_active == 0:
            return 0
        return self.total_career_earnings / self.years_active

    @property
    def highest_single_year_compensation(self) -> float:
        """Find highest single year compensation"""
        if not self.roles:
            return 0
        return max(role.total_compensation for role in self.roles)

    @property
    def companies_count(self) -> int:
        """Count unique companies worked for"""
        return len(set(role.company_id for role in self.roles))

    def get_compensation_breakdown(self) -> Dict[str, float]:
        """Get breakdown of compensation by type"""
        total_base = sum(role.base_salary for role in self.roles)
        total_bonus = sum(role.bonus for role in self.roles)
        total_stock = sum(role.stock_awards for role in self.roles)
        total_signing = sum(role.signing_bonus for role in self.roles)

        return {
            'base_salary': total_base,
            'bonus': total_bonus,
            'stock_awards': total_stock,
            'signing_bonus': total_signing,
            'total': self.total_career_earnings
        }

    def to_dict(self) -> Dict:
        """Convert person to dictionary"""
        return {
            'person_id': self.person_id,
            'name': self.name,
            'age': self.age,
            'experience': self.experience,
            'education': self.education,
            'status': self.status,
            'previous_companies': self.previous_companies,
            'total_career_earnings': self.total_career_earnings,
            'years_active': self.years_active,
            'current_role': self.current_role.to_dict() if self.current_role else None
        }


class Company:
    """Represents a company with executives and board members"""

    def __init__(self, company_id: int, name: str, ticker: str = "UNK",
                 sector: str = "Technology", market_cap: float = 0,
                 revenue: float = 0, exec_budget: float = 50000000,
                 founded: int = 2000):
        self.company_id = company_id
        self.name = name
        self.ticker = ticker
        self.sector = sector
        self.market_cap = market_cap
        self.revenue = revenue
        self.exec_budget = exec_budget
        self.founded = founded

        # Store executives and board members
        self.executives: List[Person] = []  # C-Suite executives
        self.board_members: List[Person] = []  # Board of Directors
        self.all_roles: List[Role] = []  # All roles at this company

        # Cache for quick lookups
        self._person_lookup: Dict[int, Person] = {}

    def add_person(self, person: Person, role: Role) -> None:
        """Add a person to the company with their role"""
        # Add role to company's role list
        self.all_roles.append(role)

        # Add person to appropriate list based on position type
        if role.position_type == "C-Suite":
            if person not in self.executives:
                self.executives.append(person)
        elif role.position_type == "Board":
            if person not in self.board_members:
                self.board_members.append(person)

        # Add to lookup cache
        self._person_lookup[person.person_id] = person

    def get_person_by_id(self, person_id: int) -> Optional[Person]:
        """Get a person by their ID"""
        return self._person_lookup.get(person_id)

    @property
    def total_compensation_spending(self) -> float:
        """Calculate total spending on executive compensation"""
        return sum(role.total_compensation for role in self.all_roles)

    @property
    def cap_space_remaining(self) -> float:
        """Calculate remaining budget (cap space)"""
        return self.exec_budget - self.total_compensation_spending

    @property
    def cap_utilization_percentage(self) -> float:
        """Calculate percentage of budget used"""
        if self.exec_budget == 0:
            return 0
        return (self.total_compensation_spending / self.exec_budget) * 100

    @property
    def is_over_budget(self) -> bool:
        """Check if company is over budget"""
        return self.total_compensation_spending > self.exec_budget

    @property
    def executive_count(self) -> int:
        """Count of C-Suite executives"""
        return len(self.executives)

    @property
    def board_count(self) -> int:
        """Count of board members"""
        return len(self.board_members)

    @property
    def total_roster_size(self) -> int:
        """Total count of all executives and board members"""
        return self.executive_count + self.board_count

    def get_top_earners(self, limit: int = 5) -> List[tuple[Person, Role]]:
        """Get top earning executives at this company"""
        # Sort roles by compensation
        sorted_roles = sorted(self.all_roles,
                              key=lambda r: r.total_compensation,
                              reverse=True)

        result = []
        for role in sorted_roles[:limit]:
            person = self.get_person_by_id(role.person_id)
            if person:
                result.append((person, role))

        return result

    def get_cap_info(self) -> Dict:
        """Get comprehensive cap space information"""
        return {
            'total_spent': self.total_compensation_spending,
            'budget': self.exec_budget,
            'remaining': self.cap_space_remaining,
            'utilization_pct': self.cap_utilization_percentage,
            'is_over_budget': self.is_over_budget,
            'executive_count': self.executive_count,
            'board_count': self.board_count
        }

    def get_executives_by_position_type(self, position_type: str) -> List[Dict]:
        """Get all people with specific position type with their compensation"""
        result = []
        for role in self.all_roles:
            if role.position_type == position_type:
                person = self.get_person_by_id(role.person_id)
                if person:
                    result.append({
                        'person': person,
                        'role': role,
                        'cap_hit_pct': (role.total_compensation / self.exec_budget) * 100
                    })

        # Sort by total compensation
        result.sort(key=lambda x: x['role'].total_compensation, reverse=True)
        return result

    def to_dict(self) -> Dict:
        """Convert company to dictionary"""
        return {
            'company_id': self.company_id,
            'name': self.name,
            'ticker': self.ticker,
            'sector': self.sector,
            'market_cap': self.market_cap,
            'revenue': self.revenue,
            'exec_budget': self.exec_budget,
            'founded': self.founded,
            'cap_info': self.get_cap_info(),
            'executive_count': self.executive_count,
            'board_count': self.board_count
        }


class LeagueManager:
    """Manages all companies and people in the league"""

    def __init__(self):
        self.companies: Dict[int, Company] = {}
        self.people: Dict[int, Person] = {}
        self.all_roles: List[Role] = []

    def add_company(self, company: Company) -> None:
        """Add a company to the league"""
        self.companies[company.company_id] = company

    def add_person(self, person: Person) -> None:
        """Add a person to the league"""
        self.people[person.person_id] = person

    def add_role(self, role: Role) -> None:
        """Add a role and link it to person and company"""
        self.all_roles.append(role)

        # Link to person
        if role.person_id in self.people:
            person = self.people[role.person_id]
            person.add_role(role)

            # Link to company
            if role.company_id in self.companies:
                company = self.companies[role.company_id]
                company.add_person(person, role)

    def get_company(self, company_id: int) -> Optional[Company]:
        """Get company by ID"""
        return self.companies.get(company_id)

    def get_person(self, person_id: int) -> Optional[Person]:
        """Get person by ID"""
        return self.people.get(person_id)

    def get_free_agents(self) -> List[Person]:
        """Get all free agents (retired status)"""
        return [p for p in self.people.values() if p.is_free_agent]

    def get_top_earners_league_wide(self, limit: int = 10) -> List[Dict]:
        """Get top earners across all companies"""
        earners = []
        for role in self.all_roles:
            if role.position_type == 'C-Suite':
                person = self.people.get(role.person_id)
                company = self.companies.get(role.company_id)
                if person and company:
                    earners.append({
                        'person': person,
                        'company': company,
                        'role': role,
                        'total_compensation': role.total_compensation
                    })

        # Sort by compensation
        earners.sort(key=lambda x: x['total_compensation'], reverse=True)
        return earners[:limit]

    def get_league_standings(self) -> List[Company]:
        """Get companies sorted by market cap (league standings)"""
        return sorted(self.companies.values(),
                      key=lambda c: c.market_cap,
                      reverse=True)

    def get_companies_over_budget(self) -> List[Company]:
        """Get all companies that are over budget"""
        return [c for c in self.companies.values() if c.is_over_budget]

    def get_league_statistics(self) -> Dict:
        """Get overall league statistics"""
        total_spending = sum(c.total_compensation_spending
                             for c in self.companies.values())
        total_budget = sum(c.exec_budget for c in self.companies.values())

        return {
            'total_companies': len(self.companies),
            'total_people': len(self.people),
            'total_roles': len(self.all_roles),
            'free_agents_count': len(self.get_free_agents()),
            'companies_over_budget': len(self.get_companies_over_budget()),
            'total_league_spending': total_spending,
            'total_league_budget': total_budget,
            'avg_cap_utilization': (total_spending / total_budget * 100)
            if total_budget > 0 else 0
        }


# Helper function to create instances from existing data
def create_from_loaded_data(companies_data: Dict, people_data: Dict,
                            roles_data: List) -> LeagueManager:
    """Create LeagueManager with all entities from loaded data"""
    league = LeagueManager()

    # Create all companies
    for company_id, company_info in companies_data.items():
        company = Company(
            company_id=company_id,
            name=company_info['name'],
            ticker=company_info['ticker'],
            sector=company_info['sector'],
            market_cap=company_info['market_cap'],
            revenue=company_info['revenue'],
            exec_budget=company_info['exec_budget'],
            founded=company_info['founded']
        )
        league.add_company(company)

    # Create all people
    for person_id, person_info in people_data.items():
        person = Person(
            person_id=person_id,
            name=person_info['name'],
            age=person_info['age'],
            experience=person_info['experience'],
            education=person_info['education'],
            status=person_info['status'],
            previous_companies=person_info.get('previous_companies', [])
        )
        league.add_person(person)

    # Create all roles and link them
    for role_data in roles_data:
        role = Role(
            person_id=role_data['person_id'],
            company_id=role_data['company_id'],
            title=role_data['title'],
            position_type=role_data['position_type'],
            year=role_data['year'],
            contract_years=role_data['contract_years'],
            base_salary=role_data['base_salary'],
            bonus=role_data.get('bonus', 0),
            stock_awards=role_data.get('stock_awards', 0),
            signing_bonus=role_data.get('signing_bonus', 0)
        )
        league.add_role(role)

    return league
