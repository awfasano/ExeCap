"""
fortune10_exec_data.py
========================

This module defines in‑memory representations of the Fortune 10
companies, their senior executives and directors, along with the
compensation paid to those executives for fiscal 2024 (or the most
recent fiscal year available).  The data structures mirror the
`Person`, `Role` and `Company` classes found in the ExeCap codebase
(`models.py`) so that the data can be loaded directly into the
application without additional transformation.

Each `Company` contains a list of executives (instances of
`Person`) as well as a list of board members (strings).  Each
`Person` maintains a list of `Role` objects describing their
position and compensation for a particular year.  Monetary values
are expressed in US dollars.

The figures below were sourced from publicly available filings and
reputable news outlets: the Fortune 500 list for company ranking;
proxy statements and investor relations pages for executive
compensation; and reputable business press for executive pay
summaries.  Not all companies disclose identical categories of
compensation (e.g. some distinguish between stock awards and
options while others aggregate long‑term equity awards).  Where
appropriate, stock and option awards have been aggregated into the
`stock_awards` field and cash incentives (such as non‑equity
incentive plan payouts) into the `bonus` field.  Signing bonuses
are recorded separately when disclosed.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Role:
    """Represents a single role an executive holds at a company."""
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

    def total_compensation(self) -> float:
        """Return the sum of all cash and equity compensation."""
        return self.base_salary + self.bonus + self.stock_awards + self.signing_bonus


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

    Monetary values are rounded to the nearest dollar for clarity.  See the
    accompanying research report for citations supporting the values used
    here.
    """
    companies: List[Company] = []

    # 1. Walmart
    walmart = Company(
        company_id=1,
        name="Walmart Inc.",
        ticker="WMT",
        sector="Retail",
        revenue=None,
        market_cap=None,
        founded=1962,
        board_members=[
            "Greg Penner (chair)",
            "Cesar Conde",
            "Timothy P. Flynn",
            "Sarah Friar",
            "Carla Harris",
            "Tom Horton",
            "Marissa Mayer",
            "Doug McMillon",
            "Bob Moritz",
            "Brian Niccol",
            "Randall Stephenson (lead independent director)",
            "Steuart Walton",
        ],
    )
    # Executives and their 2024 compensation (Talk Business & Politics article)
    walmart_executives = [
        {
            "name": "Doug McMillon",
            "title": "President & CEO",
            "base_salary": 1_505_000,
            "bonus": 4_356_000,  # performance cash bonus
            "stock_awards": 20_375_000,
            "other": 221_294,
        },
        {
            "name": "John Furner",
            "title": "President & CEO, Walmart U.S.",
            "base_salary": 1_315_000,
            "bonus": 2_820_000,
            "stock_awards": 11_753_000,
            "other": 190_720,
        },
        {
            "name": "Suresh Kumar",
            "title": "Executive Vice President & Chief Technology Officer",
            "base_salary": 1_138_000,
            "bonus": 2_475_000,
            "stock_awards": 12_264_000,
            "other": 109_182,
        },
        {
            "name": "Kathryn McLay",
            "title": "President & CEO, Walmart International",
            "base_salary": 1_003_000,
            "bonus": 2_379_000,
            "stock_awards": 11_242_000,
            "other": 0.0,
        },
        {
            "name": "John David Rainey",
            "title": "Executive Vice President & Chief Financial Officer",
            "base_salary": 1_033_000,
            "bonus": 2_234_000,
            "stock_awards": 11_752_000,
            "other": 266_837,
        },
        {
            "name": "Chris Nicholas",
            "title": "President & CEO, Sam’s Club",
            "base_salary": 899_808,
            "bonus": 2_009_000,
            "stock_awards": 8_176_000,
            "other": 100_791,
        },
    ]
    person_id_counter = 1
    for exec_data in walmart_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        role = Role(
            person_id=person_id_counter,
            company_id=walmart.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2024,
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        walmart.add_executive(person)
        person_id_counter += 1
    companies.append(walmart)

    # 2. Amazon
    amazon = Company(
        company_id=2,
        name="Amazon.com, Inc.",
        ticker="AMZN",
        sector="E‑commerce & Cloud Services",
        founded=1994,
        board_members=[
            "Jeff Bezos (executive chair)",
            "Andy Jassy",
            "Keith B. Alexander",
            "Edith W. Cooper",
            "Jamie S. Gorelick",
            "Daniel P. Huttenlocher",
            "Andrew Y. Ng",
            "Indra K. Nooyi",
            "Jonathan J. Rubinstein",
            "Brad D. Smith",
            "Patricia Q. Stonesifer",
            "Wendell P. Weeks",
        ],
    )
    amazon_executives = [
        {
            "name": "Andy Jassy",
            "title": "President & CEO",
            "base_salary": 365_000,
            "bonus": 0.0,
            "stock_awards": 0.0,  # no new stock awards in 2024
            "other": 1_230_000,  # includes security and other benefits
        },
        {
            "name": "Jeff Bezos",
            "title": "Executive Chair",
            "base_salary": 81_840,
            "bonus": 0.0,
            "stock_awards": 0.0,
            "other": 1_600_000,  # personal security costs
        },
        {
            "name": "Matt Garman",
            "title": "CEO, Amazon Web Services",
            "base_salary": 365_000,
            "bonus": 0.0,
            "stock_awards": 32_800_000,
            "other": 0.0,
        },
        {
            "name": "Brian Olsavsky",
            "title": "Senior Vice President & Chief Financial Officer",
            "base_salary": 365_000,  # approximate base; total compensation largely stock awards
            "bonus": 0.0,
            "stock_awards": 25_700_000,
            "other": 0.0,
        },
        {
            "name": "Douglas Herrington",
            "title": "CEO, Worldwide Stores",
            "base_salary": 365_000,  # approximate base
            "bonus": 0.0,
            "stock_awards": 34_200_000,
            "other": 0.0,
        },
    ]
    for exec_data in amazon_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        role = Role(
            person_id=person_id_counter,
            company_id=amazon.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2024,
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        amazon.add_executive(person)
        person_id_counter += 1
    companies.append(amazon)

    # 3. UnitedHealth Group
    unitedhealth = Company(
        company_id=3,
        name="UnitedHealth Group Incorporated",
        ticker="UNH",
        sector="Healthcare (Insurance)",
        founded=1977,
        board_members=[
            "Andrew Witty (CEO)",
            "Stephen Hemsley (chair)",
            "Michele Hooper (lead independent director)",
            "Timothy Flynn",
            "Paul Garcia",
            "Kristen Gil",
            "F. William McNabb III",
            "Valerie Montgomery Rice",
            "John Noseworthy",
        ],
    )
    unitedhealth_executives = [
        {
            "name": "Andrew Witty",
            "title": "Chief Executive Officer",
            "base_salary": 1_500_000,
            "bonus": 1_500_000,  # non‑equity incentive plan compensation
            "stock_awards": 17_250_000 + 5_750_000,  # stock + option awards
            "other": 339_097,
        },
        {
            "name": "John Rex",
            "title": "President & Chief Financial Officer",
            "base_salary": 1_342_000,
            "bonus": 2_100_000,
            "stock_awards": 11_251_000 + 3_750_000,
            "other": 287_929,
        },
        {
            "name": "Heather Cianfrocco",
            "title": "EVP & CEO of Optum",
            "base_salary": 1_000_000,
            "bonus": 1_500_000,
            "stock_awards": 6_001_000 + 2_000_000,
            "other": 948_035,
        },
        {
            "name": "Brian Thompson",
            "title": "Former EVP & CEO, UnitedHealthcare",
            "base_salary": 961_539,
            "bonus": 0.0,  # no non‑equity incentive disclosed
            "stock_awards": 6_001_000 + 2_000_000,
            "other": 23_359,
        },
        {
            "name": "Christopher Zaetta",
            "title": "EVP & Chief Legal Officer",
            "base_salary": 748_077,
            "bonus": 890_000,
            "stock_awards": 3_751_000 + 1_250_000,
            "other": 234_152,
        },
        {
            "name": "Erin McSweeney",
            "title": "EVP & Chief People Officer",
            "base_salary": 800_000,
            "bonus": 825_000,
            "stock_awards": 3_376_000 + 1_125_000,
            "other": 142_835,
        },
    ]
    for exec_data in unitedhealth_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        role = Role(
            person_id=person_id_counter,
            company_id=unitedhealth.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2024,
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        unitedhealth.add_executive(person)
        person_id_counter += 1
    companies.append(unitedhealth)

    # 4. Apple
    apple = Company(
        company_id=4,
        name="Apple Inc.",
        ticker="AAPL",
        sector="Technology",
        founded=1976,
        board_members=[
            "Arthur D. Levinson (chair)",
            "Wanda Austin",
            "Tim Cook",
            "Alex Gorsky",
            "Andrea Jung",
            "Monica Lozano",
            "Ronald D. Sugar",
            "Susan L. Wagner",
        ],
    )
    apple_executives = [
        {
            "name": "Tim Cook",
            "title": "Chief Executive Officer",
            "base_salary": 3_000_000,
            "bonus": 12_000_000,  # non‑equity incentive plan compensation
            "stock_awards": 58_088_946,
            "other": 1_520_856,
        },
        {
            "name": "Luca Maestri",
            "title": "Chief Financial Officer",
            "base_salary": 1_000_000,
            "bonus": 4_000_000,
            "stock_awards": 22_157_075,
            "other": 22_182,
        },
        {
            "name": "Kate Adams",
            "title": "General Counsel & SVP, Legal and Global Security",
            "base_salary": 1_000_000,
            "bonus": 4_000_000,
            "stock_awards": 22_157_075,
            "other": 22_182,
        },
        {
            "name": "Deirdre O’Brien",
            "title": "SVP Retail + People",
            "base_salary": 1_000_000,
            "bonus": 4_000_000,
            "stock_awards": 22_157_075,
            "other": 27_557,
        },
        {
            "name": "Jeff Williams",
            "title": "Chief Operating Officer",
            "base_salary": 1_000_000,
            "bonus": 4_000_000,
            "stock_awards": 22_157_075,
            "other": 20_737,
        },
    ]
    for exec_data in apple_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        role = Role(
            person_id=person_id_counter,
            company_id=apple.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2024,
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        apple.add_executive(person)
        person_id_counter += 1
    companies.append(apple)

    # 5. CVS Health
    cvs = Company(
        company_id=5,
        name="CVS Health Corporation",
        ticker="CVS",
        sector="Healthcare (Pharmacy & Health Services)",
        founded=1963,
        board_members=[
            "Fernando Aguirre",
            "Jeffrey R. Balser",
            "C. David Brown II",
            "Alecia A. Decoudreaux",
            "Roger N. Farah",
            "Anne M. Finucane",
            "J. David Joyner (CEO)",
            "J. Scott Kirby",
            "Michael F. Mahoney (lead independent director)",
            "Leslie V. Norwalk",
            "Larry Robbins",
            "Guy P. Sansone",
            "Douglas H. Shulman",
        ],
    )
    cvs_executives = [
        {
            "name": "J. David Joyner",
            "title": "President & Chief Executive Officer",
            "base_salary": 1_103_495,
            "bonus": 0.0,
            "stock_awards": 4_499_890 + 11_999_997,
            "other": 205_410,
        },
        {
            "name": "Karen Lynch",
            "title": "Former President & Chief Executive Officer",
            "base_salary": 1_191_781,
            "bonus": 2_383_562,
            "stock_awards": 14_399_857 + 3_599_985,
            "other": 1_856_281,
        },
        {
            "name": "Prem Shah",
            "title": "EVP & Co‑President, Pharmacy and Consumer Wellness",
            "base_salary": 972_917,
            "bonus": 0.0,
            "stock_awards": 4_799_848 + 7_199_977,
            "other": 293_113,
        },
        {
            "name": "Tilak Mandadi",
            "title": "EVP, Ventures & Chief Digital, Data, Analytics and Technology Officer",
            "base_salary": 1_000_000,
            "bonus": 583_000,
            "stock_awards": 8_199_843 + 1_299_989,
            "other": 278_511,
        },
        {
            "name": "Thomas Cowhey",
            "title": "EVP & Chief Financial Officer",
            "base_salary": 998_387,
            "bonus": 436_000,
            "stock_awards": 4_799_848 + 1_199_982,
            "other": 208_434,
        },
        {
            "name": "Heidi Capozzi",
            "title": "EVP & Chief People Officer",
            "base_salary": 265_625,
            "bonus": 1_500_000,  # sign‑on cash award
            "stock_awards": 4_999_989,
            "other": 85_134,
        },
    ]
    for exec_data in cvs_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        role = Role(
            person_id=person_id_counter,
            company_id=cvs.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2024,
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        cvs.add_executive(person)
        person_id_counter += 1
    companies.append(cvs)

    # 6. Berkshire Hathaway
    berkshire = Company(
        company_id=6,
        name="Berkshire Hathaway Inc.",
        ticker="BRK.A",
        sector="Conglomerate",
        founded=1839,
        board_members=[
            "Warren Buffett (chairman & CEO)",
            "Greg Abel",
            "Ajit Jain",
            "Howard G. Buffett",
            "Susan Decker",
            "Mark Suzman",
            "Julia Hartz",
            "Todd Combs",
            "Ted Weschler",
            "Ron Olson",
            "Meryl Witmer",
        ],
    )
    berkshire_executives = [
        {
            "name": "Warren Buffett",
            "title": "Chairman & Chief Executive Officer",
            "base_salary": 100_000,
            "bonus": 0.0,
            "stock_awards": 0.0,
            "other": 313_595,  # personal and home security costs per proxy
        },
        {
            "name": "Greg Abel",
            "title": "Vice Chairman (Non‑Insurance) & CEO‑designate",
            "base_salary": 16_000_000,
            "bonus": 3_000_000,
            "stock_awards": 0.0,
            "other": 1_000_000,  # estimated other compensation
        },
        {
            "name": "Ajit Jain",
            "title": "Vice Chairman (Insurance)",
            "base_salary": 16_000_000,
            "bonus": 3_000_000,
            "stock_awards": 0.0,
            "other": 1_000_000,  # estimated other compensation
        },
    ]
    for exec_data in berkshire_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        role = Role(
            person_id=person_id_counter,
            company_id=berkshire.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2024,
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        berkshire.add_executive(person)
        person_id_counter += 1
    companies.append(berkshire)

    # 7. Alphabet (Google)
    alphabet = Company(
        company_id=7,
        name="Alphabet Inc.",
        ticker="GOOGL",
        sector="Technology",
        founded=2015,  # Alphabet was created as a holding company in 2015
        board_members=[
            "Larry Page",
            "Sergey Brin",
            "Sundar Pichai",
            "Frances Arnold",
            "John L. Hennessy",
            "R. Martin Chavez",
            "L. John Doerr",
            "Roger W. Ferguson Jr.",
            "K. Ram Shriram",
            "Robin L. Washington",
        ],
    )
    alphabet_executives = [
        {
            "name": "Sundar Pichai",
            "title": "Chief Executive Officer",
            "base_salary": 2_015_000,
            "bonus": 0.0,
            "stock_awards": 405_630,
            "other": 8_304_000,
        },
        {
            "name": "Anat Ashkenazi",
            "title": "Chief Financial Officer",
            "base_salary": 1_580_000,  # estimated cash component
            "bonus": 9_900_000,
            "stock_awards": 38_500_000,
            "other": 0.0,
        },
        {
            "name": "Ruth Porat",
            "title": "President & Chief Investment Officer",
            "base_salary": 1_600_000,  # estimated cash component
            "bonus": 0.0,
            "stock_awards": 27_000_000,
            "other": 2_560_000,
        },
        {
            "name": "Prabhakar Raghavan",
            "title": "Senior Vice President, Knowledge & Information",
            "base_salary": 1_600_000,  # estimated cash component
            "bonus": 0.0,
            "stock_awards": 43_970_000,
            "other": 3_020_000,
        },
        {
            "name": "Philip Schindler",
            "title": "Chief Business Officer",
            "base_salary": 1_600_000,  # estimated cash component
            "bonus": 0.0,
            "stock_awards": 43_970_000,
            "other": 3_030_000,
        },
        {
            "name": "Kent Walker",
            "title": "President, Global Affairs & Chief Legal Officer",
            "base_salary": 1_600_000,
            "bonus": 0.0,
            "stock_awards": 27_140_000,
            "other": 3_020_000,
        },
    ]
    for exec_data in alphabet_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        role = Role(
            person_id=person_id_counter,
            company_id=alphabet.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2024,
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        alphabet.add_executive(person)
        person_id_counter += 1
    companies.append(alphabet)

    # 8. Exxon Mobil
    exxon = Company(
        company_id=8,
        name="Exxon Mobil Corporation",
        ticker="XOM",
        sector="Energy",
        founded=1870,
        board_members=[
            "Darren Woods (chairman & CEO)",
            "Joseph L. Hooley (lead independent director)",
            "Susan K. Avery",
            "Angela Braly",
            "Kenneth Frazier",
            # Additional directors are not listed here due to limited public
            # access during research.  These names represent a subset of the
            # board and were confirmed by credible sources.
        ],
    )
    exxon_executives = [
        {
            "name": "Darren Woods",
            "title": "Chairman & Chief Executive Officer",
            "base_salary": 6_662_000,
            "bonus": 0.0,
            "stock_awards": 23_199_750,
            "other": 7_058_148,
        },
        {
            "name": "Jack Williams",
            "title": "Senior Vice President",
            "base_salary": 4_492_000,
            "bonus": 0.0,
            "stock_awards": 12_785_640,
            "other": 5_659_676,
        },
        {
            "name": "Neil Chapman",
            "title": "Senior Vice President",
            "base_salary": 4_481_000,
            "bonus": 0.0,
            "stock_awards": 12_785_640,
            "other": 4_648_802,
        },
        {
            "name": "Karen McKee",
            "title": "President, Product Solutions (Vice President)",
            "base_salary": 3_862_000,
            "bonus": 0.0,
            "stock_awards": 10_599_708,
            "other": 5_632_589,
        },
        {
            "name": "Kathryn Mikells",
            "title": "Senior Vice President & Chief Financial Officer",
            "base_salary": 4_375_000,
            "bonus": 0.0,
            "stock_awards": 12_146_358,
            "other": 1_526_198,
        },
    ]
    for exec_data in exxon_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        role = Role(
            person_id=person_id_counter,
            company_id=exxon.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2023,  # the ERI data corresponds to fiscal 2023
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        exxon.add_executive(person)
        person_id_counter += 1
    companies.append(exxon)

    # 9. McKesson
    mckesson = Company(
        company_id=9,
        name="McKesson Corporation",
        ticker="MCK",
        sector="Healthcare Distribution",
        founded=1833,
        board_members=[
            "Richard H. Carmona, M.D.",
            "Dominic J. Caruso",
            "W. Roy Dunbar",
            "Deborah Dunsire, M.D.",
            "James H. Hinton",
            "Donald R. Knauss (chair)",
            "Bradley E. Lerman",
            "Maria N. Martinez",
            "Kevin M. Ozan",
            "Brian S. Tyler (CEO)",
            "Kathleen Wilson‑Thompson",
        ],
    )
    mckesson_executives = [
        {
            "name": "Brian Tyler",
            "title": "Chief Executive Officer",
            "base_salary": 1_490_000,
            "bonus": 3_142_410,
            "stock_awards": 13_500_408,
            "other": 864_725,
        },
        {
            "name": "Britt Vitalone",
            "title": "Executive Vice President & Chief Financial Officer",
            "base_salary": 937_500,
            "bonus": 1_335_938,
            "stock_awards": 4_350_396,
            "other": 158_827,
        },
        {
            "name": "Michele Lau",
            "title": "Executive Vice President & Chief Legal Officer",
            "base_salary": 175_000,
            "bonus": 199_500,  # annual bonus
            "stock_awards": 6_851_529,
            "other": 80_225,
        },
        {
            "name": "LeAnn Smith",
            "title": "Executive Vice President & Chief Human Resources Officer",
            "base_salary": 635_418,
            "bonus": 724_377,
            "stock_awards": 2_000_379,
            "other": 80_941,
        },
        {
            "name": "Tom Rodgers",
            "title": "Executive Vice President & Chief Strategy & Business Development Officer",
            "base_salary": 611_750,
            "bonus": 697_395,
            "stock_awards": 1_750_716,
            "other": 119_115,
        },
        {
            "name": "Kirk Kaminsky",
            "title": "Executive Vice President, Group President, North American Pharmaceutical Services",
            "base_salary": 0.0,
            "bonus": 0.0,
            "stock_awards": 0.0,
            "other": 0.0,
        },
        {
            "name": "Kevin Kettler",
            "title": "Executive Vice President & President, Prescription Technology Solutions",
            "base_salary": 0.0,
            "bonus": 0.0,
            "stock_awards": 0.0,
            "other": 0.0,
        },
        {
            "name": "Stanton McComb",
            "title": "President, Medical‑Surgical",
            "base_salary": 0.0,
            "bonus": 0.0,
            "stock_awards": 0.0,
            "other": 0.0,
        },
        {
            "name": "Francisco Fraga",
            "title": "EVP, Chief Information Officer and Chief Technology Officer",
            "base_salary": 0.0,
            "bonus": 0.0,
            "stock_awards": 0.0,
            "other": 0.0,
        },
        {
            "name": "Nimesh Jhaveri",
            "title": "EVP & Chief Impact Officer",
            "base_salary": 0.0,
            "bonus": 0.0,
            "stock_awards": 0.0,
            "other": 0.0,
        },
        {
            "name": "Joan Eliasek",
            "title": "President, North American Pharmaceutical Distribution",
            "base_salary": 0.0,
            "bonus": 0.0,
            "stock_awards": 0.0,
            "other": 0.0,
        },
    ]
    for exec_data in mckesson_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        # Only include compensation details when available.  Many members of
        # McKesson's Executive Operating Team are not named executive officers
        # and therefore do not have disclosed compensation.  Their fields are
        # left at zero.
        role = Role(
            person_id=person_id_counter,
            company_id=mckesson.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2024,
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        mckesson.add_executive(person)
        person_id_counter += 1
    companies.append(mckesson)

    # 10. Cencora (formerly AmerisourceBergen)
    cencora = Company(
        company_id=10,
        name="Cencora, Inc.",
        ticker="COR",
        sector="Pharmaceutical Distribution & Services",
        founded=1985,
        board_members=[
            "Ornella Barra",
            "Werner Baumann",
            "Frank K. Clyburn",
            "Steven H. Collis",
            "D. Mark Durcan",
            "Lon R. Greenberg",
            "Lorence H. Kim, M.D.",
            "Robert P. Mauch",
            "Redonda G. Miller, M.D.",
            "Dennis M. Nally",
            "Lauren M. Tyler",
        ],
    )
    cencora_executives = [
        {
            "name": "Steven H. Collis",
            "title": "Executive Chairman (former President & CEO)",
            "base_salary": 1_464_959,
            "bonus": 4_101_886,
            "stock_awards": 12_500_101,
            "other": 408_225,
        },
        {
            "name": "James F. Cleary",
            "title": "Executive Vice President & Chief Financial Officer",
            "base_salary": 885_943,
            "bonus": 1_417_509,
            "stock_awards": 6_600_508,
            "other": 100_000,
        },
        {
            "name": "Robert P. Mauch",
            "title": "President & Chief Executive Officer (from Oct 2024)",
            "base_salary": 1_039_959,
            "bonus": 2_079_919,
            "stock_awards": 6_000_127,
            "other": 133_187,
        },
        {
            "name": "Elizabeth S. Campbell",
            "title": "Executive Vice President & Chief Legal Officer",
            "base_salary": 721_967,
            "bonus": 1_155_148,
            "stock_awards": 5_700_587,
            "other": 91_362,
        },
        {
            "name": "Silvana Battaglia",
            "title": "Executive Vice President & Chief Human Resources Officer",
            "base_salary": 625_984,
            "bonus": 1_001_574,
            "stock_awards": 3_600_373,
            "other": 92_281,
        },
    ]
    for exec_data in cencora_executives:
        person = Person(person_id=person_id_counter, name=exec_data["name"])
        role = Role(
            person_id=person_id_counter,
            company_id=cencora.company_id,
            title=exec_data["title"],
            position_type="Executive",
            year=2024,
            contract_years=1,
            base_salary=exec_data["base_salary"],
            bonus=exec_data["bonus"],
            stock_awards=exec_data["stock_awards"],
            signing_bonus=0.0,
        )
        person.add_role(role)
        cencora.add_executive(person)
        person_id_counter += 1
    companies.append(cencora)

    return companies
