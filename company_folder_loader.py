# File 1: company_folder_loader.py
import pandas as pd
from google.cloud import storage
import os
from pathlib import Path
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class CompanyFolderLoader:
    """Load Excel data from company-organized folders in GCS bucket"""

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

        # Data containers
        self.companies_data = {}
        self.people_data = {}
        self.roles_data = []

    def list_company_folders(self) -> List[str]:
        """List all company folders in the bucket"""
        folders = set()
        blobs = self.bucket.list_blobs(prefix="companies/")

        for blob in blobs:
            # Extract company name from path like "companies/walmart/file.xlsx"
            path_parts = blob.name.split('/')
            if len(path_parts) >= 3 and path_parts[0] == "companies":
                company_name = path_parts[1]
                folders.add(company_name)

        logger.info(f"Found company folders: {list(folders)}")
        return list(folders)

    def list_excel_files_for_company(self, company_name: str) -> Dict[str, List[str]]:
        """List Excel files for a specific company, categorized by type"""
        prefix = f"companies/{company_name}/"
        blobs = self.bucket.list_blobs(prefix=prefix)

        files = {
            'company_info': [],
            'people': [],
            'executive_pay': [],
            'other': []
        }

        for blob in blobs:
            if any(blob.name.lower().endswith(ext) for ext in ['.xlsx', '.xls', '.xlsm']):
                filename_lower = blob.name.lower()

                # Categorize files based on filename
                if any(keyword in filename_lower for keyword in ['company', 'info', 'information', 'details']):
                    files['company_info'].append(blob.name)
                elif any(keyword in filename_lower for keyword in ['people', 'executives', 'personnel', 'employees']):
                    files['people'].append(blob.name)
                elif any(keyword in filename_lower for keyword in ['pay', 'compensation', 'salary', 'executive']):
                    files['executive_pay'].append(blob.name)
                else:
                    files['other'].append(blob.name)

        return files

    def download_excel_file(self, blob_name: str) -> Path:
        """Download Excel file from GCS"""
        blob = self.bucket.blob(blob_name)
        local_file = self.cache_dir / Path(blob_name).name

        # Create company subdirectory if needed
        local_file.parent.mkdir(parents=True, exist_ok=True)

        blob.download_to_filename(str(local_file))
        logger.info(f"Downloaded {blob_name}")
        return local_file

    def load_company_data_from_file(self, file_path: str, company_name: str) -> Dict:
        """Load company information from Excel file"""
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
                return {}

            # Use first row of data or look for specific company
            row = df.iloc[0]  # Default to first row

            # Try to find row for this company if multiple companies in file
            if 'name' in df.columns or 'company_name' in df.columns:
                name_col = 'name' if 'name' in df.columns else 'company_name'
                company_rows = df[df[name_col].str.contains(company_name, case=False, na=False)]
                if len(company_rows) > 0:
                    row = company_rows.iloc[0]

            # Generate unique company ID based on company name
            company_id = abs(hash(company_name.lower())) % 1000 + 100

            company_data = {
                'name': str(row.get('name', row.get('company_name', company_name.title()))),
                'ticker': str(row.get('ticker', row.get('symbol', 'UNK'))),
                'sector': str(row.get('sector', row.get('industry', 'Technology'))),
                'market_cap': int(row.get('market_cap', row.get('market_capitalization', 0))),
                'revenue': int(row.get('revenue', row.get('annual_revenue', 0))),
                'exec_budget': int(row.get('exec_budget', row.get('executive_budget', 50000000))),
                'founded': int(row.get('founded', row.get('year_founded', 2000)))
            }

            logger.info(f"Loaded company data for {company_name}")
            return {company_id: company_data}

        except Exception as e:
            logger.error(f"Error loading company data from {file_path}: {e}")
            return {}

    def load_people_data_from_file(self, file_path: str, company_name: str) -> Dict:
        """Load people data from Excel file"""
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
                return {}

            people = {}
            for index, row in df.iterrows():
                # Generate unique person ID
                person_name = str(row.get('name', row.get('full_name', f'Person {index}')))
                person_id = abs(hash(f"{company_name}_{person_name}".lower())) % 10000 + 1

                # Handle previous companies
                prev_companies = row.get('previous_companies', '')
                if isinstance(prev_companies, str) and prev_companies:
                    prev_companies_list = [c.strip() for c in prev_companies.split(',')]
                else:
                    prev_companies_list = []

                people[person_id] = {
                    'name': person_name,
                    'status': str(row.get('status', 'Active')),
                    'age': int(row.get('age', 45)) if pd.notna(row.get('age')) else 45,
                    'experience': int(row.get('experience', row.get('years_experience', 10))) if pd.notna(
                        row.get('experience', row.get('years_experience'))) else 10,
                    'education': str(row.get('education', row.get('degree', 'MBA'))),
                    'previous_companies': prev_companies_list
                }

            logger.info(f"Loaded {len(people)} people for {company_name}")
            return people

        except Exception as e:
            logger.error(f"Error loading people data from {file_path}: {e}")
            return {}

    def load_executive_pay_from_file(self, file_path: str, company_name: str) -> List:
        """Load executive compensation data from Excel file"""
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

            roles = []
            for index, row in df.iterrows():
                # Generate person ID from name if not provided
                if 'person_id' in row and pd.notna(row['person_id']):
                    person_id = int(row['person_id'])
                else:
                    person_name = str(row.get('name', row.get('executive_name', f'Person {index}')))
                    person_id = abs(hash(f"{company_name}_{person_name}".lower())) % 10000 + 1

                role = {
                    'person_id': person_id,
                    'company_id': company_id,
                    'title': str(row.get('title', row.get('position', 'Executive'))),
                    'position_type': str(row.get('position_type', row.get('type', 'C-Suite'))),
                    'year': int(row.get('year', 2024)) if pd.notna(row.get('year')) else 2024,
                    'contract_years': int(row.get('contract_years', row.get('contract_length', 3))) if pd.notna(
                        row.get('contract_years', row.get('contract_length'))) else 3,
                    'base_salary': int(row.get('base_salary', row.get('salary', 1000000))) if pd.notna(
                        row.get('base_salary', row.get('salary'))) else 1000000,
                    'bonus': int(row.get('bonus', 0)) if pd.notna(row.get('bonus')) else 0,
                    'stock_awards': int(row.get('stock_awards', row.get('equity', 0))) if pd.notna(
                        row.get('stock_awards', row.get('equity'))) else 0,
                    'signing_bonus': int(row.get('signing_bonus', 0)) if pd.notna(row.get('signing_bonus')) else 0
                }
                roles.append(role)

            logger.info(f"Loaded {len(roles)} roles for {company_name}")
            return roles

        except Exception as e:
            logger.error(f"Error loading executive pay from {file_path}: {e}")
            return []

    def load_all_company_data(self, company_names: List[str] = None) -> Dict:
        """Load data for all companies or specified companies"""
        try:
            # Get all company folders if none specified
            if company_names is None:
                company_names = self.list_company_folders()

            all_companies = {}
            all_people = {}
            all_roles = []

            for company_name in company_names:
                logger.info(f"Loading data for {company_name}")

                # Get files for this company
                company_files = self.list_excel_files_for_company(company_name)

                # Load company information
                if company_files['company_info']:
                    company_data = self.load_company_data_from_file(company_files['company_info'][0], company_name)
                    all_companies.update(company_data)

                # Load people data
                if company_files['people']:
                    people_data = self.load_people_data_from_file(company_files['people'][0], company_name)
                    all_people.update(people_data)

                # Load executive pay data
                if company_files['executive_pay']:
                    roles_data = self.load_executive_pay_from_file(company_files['executive_pay'][0], company_name)
                    all_roles.extend(roles_data)

                # Try loading from 'other' files if main categories are empty
                if not (company_files['company_info'] or company_files['people'] or company_files['executive_pay']):
                    for other_file in company_files['other']:
                        logger.info(f"Trying to load from other file: {other_file}")
                        # Attempt to load as executive pay (most common)
                        try:
                            roles_data = self.load_executive_pay_from_file(other_file, company_name)
                            if roles_data:
                                all_roles.extend(roles_data)
                        except:
                            pass

            # Store loaded data
            self.companies_data = all_companies
            self.people_data = all_people
            self.roles_data = all_roles

            return {
                'status': 'success',
                'companies_loaded': list(company_names),
                'companies_count': len(all_companies),
                'people_count': len(all_people),
                'roles_count': len(all_roles)
            }

        except Exception as e:
            logger.error(f"Error loading company data: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_companies(self) -> Dict:
        """Get loaded companies data"""
        return self.companies_data

    def get_people(self) -> Dict:
        """Get loaded people data"""
        return self.people_data

    def get_roles(self) -> List:
        """Get loaded roles data"""
        return self.roles_data
