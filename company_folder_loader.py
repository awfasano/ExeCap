# company_folder_loader.py - Updated for companies/<company>/<year>/files structure
import pandas as pd
from google.cloud import storage
import os
from pathlib import Path
import logging
from typing import Dict, List, Optional, Set
from models import Company, Person, Role, LeagueManager

logger = logging.getLogger(__name__)


class CompanyFolderLoader:
    """Load Excel data from company/year organized folders in GCS bucket"""

    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        self.bucket_name = bucket_name

        # Initialize GCS client
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

        # Local cache directory
        self.cache_dir = Path("excel_cache")
        self.cache_dir.mkdir(exist_ok=True)

        # League manager to hold all data
        self.league_manager = LeagueManager()

        # Legacy data containers (for backward compatibility)
        self.companies_data = {}
        self.people_data = {}
        self.roles_data = []

    def list_company_folders(self) -> List[str]:
        """List all company folders in the bucket"""
        folders = set()
        blobs = self.bucket.list_blobs(prefix="companies/")

        for blob in blobs:
            # Extract company name from path like "companies/walmart/2024/file.xlsx"
            path_parts = blob.name.split('/')
            if len(path_parts) >= 2 and path_parts[0] == "companies":
                company_name = path_parts[1]
                folders.add(company_name)

        logger.info(f"Found company folders: {list(folders)}")
        return list(folders)

    def list_years_for_company(self, company_name: str) -> List[str]:
        """List all years available for a specific company"""
        years = set()
        prefix = f"companies/{company_name}/"
        blobs = self.bucket.list_blobs(prefix=prefix)

        for blob in blobs:
            # Extract year from path like "companies/walmart/2024/file.xlsx"
            path_parts = blob.name.split('/')
            if len(path_parts) >= 3 and path_parts[0] == "companies" and path_parts[1] == company_name:
                year = path_parts[2]
                # Check if it's a valid year (4 digits)
                if year.isdigit() and len(year) == 4:
                    years.add(year)

        return sorted(list(years))

    def list_excel_files_for_company_year(self, company_name: str, year: str = None) -> Dict[str, List[str]]:
        """
        List Excel files for a specific company and year, categorized by type.
        If year is None, gets files from all years.
        """
        if year:
            prefix = f"companies/{company_name}/{year}/"
        else:
            prefix = f"companies/{company_name}/"

        blobs = self.bucket.list_blobs(prefix=prefix)

        files = {
            'company_info': [],
            'people': [],
            'executive_pay': [],
            'other': [],
            'by_year': {}  # Store files organized by year
        }

        for blob in blobs:
            if any(blob.name.lower().endswith(ext) for ext in ['.xlsx', '.xls', '.xlsm']):
                # Extract year from path
                path_parts = blob.name.split('/')
                file_year = None
                if len(path_parts) >= 4 and path_parts[2].isdigit():
                    file_year = path_parts[2]

                filename_lower = blob.name.lower()

                # Store by year
                if file_year:
                    if file_year not in files['by_year']:
                        files['by_year'][file_year] = {
                            'company_info': [],
                            'people': [],
                            'executive_pay': [],
                            'other': []
                        }

                    year_files = files['by_year'][file_year]
                else:
                    year_files = files

                # Categorize files based on filename
                if any(keyword in filename_lower for keyword in ['company', 'info', 'information', 'details']):
                    files['company_info'].append(blob.name)
                    if file_year:
                        year_files['company_info'].append(blob.name)
                elif any(keyword in filename_lower for keyword in ['people', 'executives', 'personnel', 'employees']):
                    files['people'].append(blob.name)
                    if file_year:
                        year_files['people'].append(blob.name)
                elif any(keyword in filename_lower for keyword in ['pay', 'compensation', 'salary', 'executive']):
                    files['executive_pay'].append(blob.name)
                    if file_year:
                        year_files['executive_pay'].append(blob.name)
                else:
                    files['other'].append(blob.name)
                    if file_year:
                        year_files['other'].append(blob.name)

        return files

    def download_excel_file(self, blob_name: str) -> Path:
        """Download Excel file from GCS"""
        blob = self.bucket.blob(blob_name)

        # Create nested directory structure for cache
        path_parts = blob_name.split('/')
        if len(path_parts) >= 4:  # companies/company/year/file.xlsx
            company = path_parts[1]
            year = path_parts[2]
            filename = path_parts[-1]
            local_file = self.cache_dir / company / year / filename
        else:
            local_file = self.cache_dir / Path(blob_name).name

        # Create parent directories if needed
        local_file.parent.mkdir(parents=True, exist_ok=True)

        blob.download_to_filename(str(local_file))
        logger.info(f"Downloaded {blob_name}")
        return local_file

    def load_company_from_file(self, file_path: str, company_name: str, year: str = None) -> Optional[Company]:
        """Load company information from Excel file and create Company instance"""
        try:
            local_file = self.download_excel_file(file_path)

            # Try different sheet names
            df = None
            excel_file = pd.ExcelFile(local_file)
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(local_file, sheet_name=sheet_name)
                    if len(df) > 0:
                        break
                except:
                    continue

            if df is None or len(df) == 0:
                logger.warning(f"No data found in {file_path}")
                return None

            # Filter by year if specified and year column exists
            if year and 'year' in df.columns:
                year_int = int(year)
                df_year = df[df['year'] == year_int]
                if len(df_year) > 0:
                    row = df_year.iloc[0]
                else:
                    row = df.iloc[0]
            else:
                row = df.iloc[0]

            # Try to find row for this company if multiple companies in file
            if 'name' in df.columns or 'company_name' in df.columns:
                name_col = 'name' if 'name' in df.columns else 'company_name'
                company_rows = df[df[name_col].str.contains(company_name, case=False, na=False)]
                if len(company_rows) > 0:
                    row = company_rows.iloc[0]

            # Generate unique company ID based on company name
            company_id = abs(hash(company_name.lower())) % 1000 + 100

            # Create Company instance
            company = Company(
                company_id=company_id,
                name=str(row.get('name', row.get('company_name', company_name.title()))),
                ticker=str(row.get('ticker', row.get('symbol', 'UNK'))),
                sector=str(row.get('sector', row.get('industry', 'Technology'))),
                market_cap=float(row.get('market_cap', row.get('market_capitalization', 0))),
                revenue=float(row.get('revenue', row.get('annual_revenue', 0))),
                exec_budget=float(row.get('exec_budget', row.get('executive_budget', 50000000))),
                founded=int(row.get('founded', row.get('year_founded', 2000)))
            )

            # Add to league manager
            self.league_manager.add_company(company)

            # Store in legacy format for backward compatibility
            self.companies_data[company_id] = company.to_dict()

            logger.info(f"Loaded company: {company.name} (year: {year or 'all'})")
            return company

        except Exception as e:
            logger.error(f"Error loading company data from {file_path}: {e}")
            return None

    def load_people_from_file(self, file_path: str, company_name: str, year: str = None) -> List[Person]:
        """Load people data from Excel file and create Person instances"""
        try:
            local_file = self.download_excel_file(file_path)

            # Try different sheet names
            df = None
            excel_file = pd.ExcelFile(local_file)
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(local_file, sheet_name=sheet_name)
                    if len(df) > 0:
                        break
                except:
                    continue

            if df is None:
                return []

            # Filter by year if specified and year column exists
            if year and 'year' in df.columns:
                year_int = int(year)
                df = df[df['year'] == year_int]

            people_list = []
            for index, row in df.iterrows():
                # Generate unique person ID
                person_name = str(row.get('name', row.get('full_name', f'Person {index}')))
                person_id = abs(hash(f"{company_name}_{person_name}".lower())) % 10000 + 1

                # Check if person already exists
                existing_person = self.league_manager.get_person(person_id)
                if existing_person:
                    # Update existing person if needed
                    people_list.append(existing_person)
                    continue

                # Handle previous companies
                prev_companies = row.get('previous_companies', '')
                if isinstance(prev_companies, str) and prev_companies:
                    prev_companies_list = [c.strip() for c in prev_companies.split(',')]
                else:
                    prev_companies_list = []

                # Create Person instance
                person = Person(
                    person_id=person_id,
                    name=person_name,
                    age=int(row.get('age', 45)) if pd.notna(row.get('age')) else 45,
                    experience=int(row.get('experience', row.get('years_experience', 10)))
                    if pd.notna(row.get('experience', row.get('years_experience'))) else 10,
                    education=str(row.get('education', row.get('degree', 'MBA'))),
                    status=str(row.get('status', 'Active')),
                    previous_companies=prev_companies_list
                )

                # Add to league manager
                self.league_manager.add_person(person)
                people_list.append(person)

                # Store in legacy format
                self.people_data[person_id] = person.to_dict()

            logger.info(f"Loaded {len(people_list)} people for {company_name} (year: {year or 'all'})")
            return people_list

        except Exception as e:
            logger.error(f"Error loading people data from {file_path}: {e}")
            return []

    def load_roles_from_file(self, file_path: str, company_name: str, year: str = None) -> List[Role]:
        """Load executive compensation data from Excel file and create Role instances"""
        try:
            local_file = self.download_excel_file(file_path)

            # Try different sheet names
            df = None
            excel_file = pd.ExcelFile(local_file)
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(local_file, sheet_name=sheet_name)
                    if len(df) > 0:
                        break
                except:
                    continue

            if df is None:
                return []

            # Get company ID
            company_id = abs(hash(company_name.lower())) % 1000 + 100

            # Determine year from file path or dataframe
            if year:
                file_year = int(year)
            elif 'year' in df.columns and pd.notna(df['year'].iloc[0]):
                file_year = int(df['year'].iloc[0])
            else:
                # Try to extract from file path
                path_parts = file_path.split('/')
                file_year = 2024  # Default
                for part in path_parts:
                    if part.isdigit() and len(part) == 4:
                        file_year = int(part)
                        break

            roles_list = []
            for index, row in df.iterrows():
                # Generate person ID from name if not provided
                if 'person_id' in row and pd.notna(row['person_id']):
                    person_id = int(row['person_id'])
                else:
                    person_name = str(row.get('name', row.get('executive_name', f'Person {index}')))
                    person_id = abs(hash(f"{company_name}_{person_name}".lower())) % 10000 + 1

                # Use year from row if available, otherwise use file year
                role_year = int(row.get('year', file_year)) if pd.notna(row.get('year')) else file_year

                # Create Role instance
                role = Role(
                    person_id=person_id,
                    company_id=company_id,
                    title=str(row.get('title', row.get('position', 'Executive'))),
                    position_type=str(row.get('position_type', row.get('type', 'C-Suite'))),
                    year=role_year,
                    contract_years=int(row.get('contract_years', row.get('contract_length', 3)))
                    if pd.notna(row.get('contract_years', row.get('contract_length'))) else 3,
                    base_salary=float(row.get('base_salary', row.get('salary', 1000000)))
                    if pd.notna(row.get('base_salary', row.get('salary'))) else 1000000,
                    bonus=float(row.get('bonus', 0)) if pd.notna(row.get('bonus')) else 0,
                    stock_awards=float(row.get('stock_awards', row.get('equity', 0)))
                    if pd.notna(row.get('stock_awards', row.get('equity'))) else 0,
                    signing_bonus=float(row.get('signing_bonus', 0))
                    if pd.notna(row.get('signing_bonus')) else 0
                )

                # Add to league manager (this will link to person and company)
                self.league_manager.add_role(role)
                roles_list.append(role)

                # Store in legacy format
                self.roles_data.append(role.to_dict())

            logger.info(f"Loaded {len(roles_list)} roles for {company_name} (year: {year or file_year})")
            return roles_list

        except Exception as e:
            logger.error(f"Error loading executive pay from {file_path}: {e}")
            return []

    def load_company_data_for_year(self, company_name: str, year: str) -> Dict:
        """Load all data for a specific company and year"""
        logger.info(f"Loading data for {company_name} - Year {year}")

        # Get files for this company and year
        company_files = self.list_excel_files_for_company_year(company_name, year)

        results = {
            'company': None,
            'people': [],
            'roles': []
        }

        # Check if this year has files
        if year in company_files['by_year']:
            year_files = company_files['by_year'][year]

            # Load company information
            if year_files['company_info']:
                results['company'] = self.load_company_from_file(
                    year_files['company_info'][0], company_name, year)

            # Load people data
            if year_files['people']:
                results['people'] = self.load_people_from_file(
                    year_files['people'][0], company_name, year)

            # Load executive pay data
            if year_files['executive_pay']:
                results['roles'] = self.load_roles_from_file(
                    year_files['executive_pay'][0], company_name, year)

            # Try loading from 'other' files if main categories are empty
            if not (year_files['company_info'] or year_files['people'] or year_files['executive_pay']):
                for other_file in year_files['other']:
                    logger.info(f"Trying to load from other file: {other_file}")
                    try:
                        roles = self.load_roles_from_file(other_file, company_name, year)
                        if roles:
                            results['roles'].extend(roles)
                    except:
                        pass

        return results

    def load_all_company_data(self, company_names: List[str] = None,
                              specific_year: str = None,
                              load_all_years: bool = True) -> Dict:
        """
        Load data for all companies or specified companies.

        Args:
            company_names: List of company names to load (None = all)
            specific_year: Load only this year (e.g., '2024')
            load_all_years: If True, load all available years for each company
        """
        try:
            # Reset league manager
            self.league_manager = LeagueManager()
            self.companies_data = {}
            self.people_data = {}
            self.roles_data = []

            # Get all company folders if none specified
            if company_names is None:
                company_names = self.list_company_folders()

            for company_name in company_names:
                logger.info(f"Loading data for {company_name}")

                if specific_year:
                    # Load only specific year
                    self.load_company_data_for_year(company_name, specific_year)
                elif load_all_years:
                    # Load all available years
                    years = self.list_years_for_company(company_name)
                    if years:
                        for year in years:
                            self.load_company_data_for_year(company_name, year)
                    else:
                        # No year folders, try loading from root company folder
                        logger.info(f"No year folders found for {company_name}, checking root folder")
                        company_files = self.list_excel_files_for_company_year(company_name)

                        # Load from non-year-specific files
                        if company_files['company_info']:
                            self.load_company_from_file(company_files['company_info'][0], company_name)
                        if company_files['people']:
                            self.load_people_from_file(company_files['people'][0], company_name)
                        if company_files['executive_pay']:
                            self.load_roles_from_file(company_files['executive_pay'][0], company_name)
                else:
                    # Load most recent year only
                    years = self.list_years_for_company(company_name)
                    if years:
                        most_recent_year = max(years)
                        self.load_company_data_for_year(company_name, most_recent_year)

            return {
                'status': 'success',
                'companies_loaded': list(company_names),
                'companies_count': len(self.league_manager.companies),
                'people_count': len(self.league_manager.people),
                'roles_count': len(self.league_manager.all_roles),
                'league_manager': self.league_manager
            }

        except Exception as e:
            logger.error(f"Error loading company data: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_league_manager(self) -> LeagueManager:
        """Get the populated league manager"""
        return self.league_manager

    def get_companies(self) -> Dict:
        """Get loaded companies data (legacy format for backward compatibility)"""
        return self.companies_data

    def get_people(self) -> Dict:
        """Get loaded people data (legacy format for backward compatibility)"""
        return self.people_data

    def get_roles(self) -> List:
        """Get loaded roles data (legacy format for backward compatibility)"""
        return self.roles_data

    def get_available_years(self) -> Set[str]:
        """Get all unique years across all companies"""
        all_years = set()
        for company in self.list_company_folders():
            years = self.list_years_for_company(company)
            all_years.update(years)
        return all_years