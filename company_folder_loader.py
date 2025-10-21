"""Loader for company CSV datasets stored in GCS under companies/<slug>/<year>/."""

from __future__ import annotations

import csv
import io
import logging
import os
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Set

from google.cloud import storage

from models import (
    BeneficialOwnershipRecord,
    Company,
    DirectorCompensation,
    DirectorCompPolicy,
    DirectorProfile,
    ExecutiveCompensation,
    ExecutiveEquityGrant,
    LeagueManager,
    Person,
    SourceManifestEntry,
)

logger = logging.getLogger(__name__)

CSV_SUFFIX = ".csv"


def _slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unknown"


def _to_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "" or text.lower() in {"na", "n/a", "none"}:
        return 0.0
    text = text.replace(",", "").replace("$", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _to_int(value) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text == "" or text.lower() in {"na", "n/a", "none"}:
        return 0
    text = text.replace(",", "")
    try:
        return int(float(text))
    except ValueError:
        return 0


def _to_bool(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "t", "yes", "y", "1"}


def _parse_date(value: Optional[str], fallback: Optional[date] = None) -> Optional[date]:
    if not value:
        return fallback
    text = str(value).strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            try:
                return datetime.strptime(text, "%m/%d/%Y").date()
            except ValueError:
                return fallback


def _get_first(row: Dict[str, str], keys: Iterable[str], default=None):
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _get_float(row: Dict[str, str], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return _to_float(row[key])
    return default


def _get_int(row: Dict[str, str], *keys: str, default: Optional[int] = 0) -> Optional[int]:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return _to_int(row[key])
    return default


class CompanyFolderLoader:
    """Load CSV data from company/year organized folders in GCS bucket."""

    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        self.bucket_name = bucket_name
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

        self.league_manager = LeagueManager()
        self.load_warnings: List[str] = []

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def list_company_folders(self) -> List[str]:
        folders: Set[str] = set()
        for blob in self.bucket.list_blobs(prefix="companies/"):
            parts = blob.name.split("/")
            if len(parts) >= 2 and parts[0] == "companies" and parts[1]:
                folders.add(parts[1])
        return sorted(folders)

    def list_years_for_company(self, company_slug: str) -> List[str]:
        years: Set[str] = set()
        prefix = f"companies/{company_slug}/"
        for blob in self.bucket.list_blobs(prefix=prefix):
            parts = blob.name.split("/")
            if len(parts) >= 3 and parts[0] == "companies" and parts[1] == company_slug:
                year = parts[2]
                if year.isdigit() and len(year) == 4:
                    years.add(year)
        return sorted(years)

    # ------------------------------------------------------------------
    # CSV ingestion
    # ------------------------------------------------------------------

    def _read_csv_blob(self, blob_name: str) -> List[Dict[str, str]]:
        blob = self.bucket.blob(blob_name)
        try:
            try:
                contents = blob.download_as_text(encoding="utf-8")
            except UnicodeDecodeError:
                contents = blob.download_as_text(encoding="latin-1")
        except Exception as exc:
            message = f"Failed to download {blob_name}: {exc}"
            logger.warning(message)
            self.load_warnings.append(message)
            return []

        reader = csv.DictReader(io.StringIO(contents))
        rows = [
            {
                (k.strip() if isinstance(k, str) else k): (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
            }
            for row in reader
        ]
        if not rows:
            message = f"No rows found in {blob_name}"
            logger.warning(message)
            self.load_warnings.append(message)
        else:
            logger.debug("Loaded %s rows from %s", len(rows), blob_name)
        return rows

    def _ensure_company(self, company_slug: str, manifest_row: Dict[str, str], year: str) -> Company:
        company = self.league_manager.get_company(company_slug)
        fiscal_year_end = _parse_date(
            manifest_row.get("fiscal_year_end"),
            fallback=date(int(year), 12, 31),
        )

        if not company:
            company = Company(
                company_id=company_slug,
                company_name=manifest_row.get("company_name", company_slug.replace("-", " ").title()),
                ticker=manifest_row.get("ticker", manifest_row.get("stock_ticker", "UNK")),
                fiscal_year_end=fiscal_year_end or date(int(year), 12, 31),
                source_url=manifest_row.get("source_url", ""),
                notes=manifest_row.get("notes"),
                market_cap_usd=_to_float(manifest_row.get("market_cap_usd")),
                revenue_usd=_to_float(manifest_row.get("revenue_usd")),
                cap_budget_usd=_to_float(manifest_row.get("cap_budget_usd")),
                sector=manifest_row.get("sector"),
                founded_year=_to_int(manifest_row.get("founded_year")),
            )
            self.league_manager.add_company(company)
        else:
            # Update mutable fields if new information arrives
            company.company_name = manifest_row.get("company_name", company.company_name)
            company.ticker = manifest_row.get("ticker", company.ticker)
            company.fiscal_year_end = fiscal_year_end or company.fiscal_year_end
            company.source_url = manifest_row.get("source_url", company.source_url)
            company.notes = manifest_row.get("notes", company.notes)
            company.market_cap_usd = _to_float(manifest_row.get("market_cap_usd")) or company.market_cap_usd
            company.revenue_usd = _to_float(manifest_row.get("revenue_usd")) or company.revenue_usd
            company.cap_budget_usd = _to_float(manifest_row.get("cap_budget_usd")) or company.cap_budget_usd
            company.sector = manifest_row.get("sector", company.sector)
            founded_year = _to_int(manifest_row.get("founded_year"))
            company.founded_year = founded_year or company.founded_year

        return company

    def _ensure_person(
        self,
        person_id: Optional[str],
        full_name: str,
        *,
        current_title: str = "",
        is_executive: bool = False,
        is_director: bool = False,
        bio_short: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        photo_url: Optional[str] = None,
        years_experience: Optional[int] = None,
        education: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Person:
        slug = person_id or _slugify(full_name)
        person = self.league_manager.get_person(slug)
        if not person:
            person = Person(
                person_id=slug,
                full_name=full_name,
                current_title=current_title,
                is_executive=is_executive,
                is_director=is_director,
                bio_short=bio_short,
                linkedin_url=linkedin_url,
                photo_url=photo_url,
                years_experience=years_experience,
                education=education,
                status=status,
            )
            self.league_manager.add_person(person)
        else:
            if current_title:
                person.current_title = current_title
            if bio_short and not person.bio_short:
                person.bio_short = bio_short
            if linkedin_url and not person.linkedin_url:
                person.linkedin_url = linkedin_url
            if photo_url and not person.photo_url:
                person.photo_url = photo_url
            if years_experience and not person.years_experience:
                person.years_experience = years_experience
            if education and not person.education:
                person.education = education
            if status:
                person.status = status
            person.is_executive = person.is_executive or is_executive
            person.is_director = person.is_director or is_director

        return person

    def _import_manifest(self, company_slug: str, year: str, blob_name: str) -> Dict[str, str]:
        rows = self._read_csv_blob(blob_name)
        manifest = rows[0] if rows else {}
        for row in rows:
            entry = SourceManifestEntry(
                company_id=company_slug,
                file_path=row.get("file_path") or row.get("file") or "",
                description=row.get("description") or row.get("what") or "",
                last_updated=_parse_date(row.get("last_updated"), fallback=date.today()) or date.today(),
            )
            self.league_manager.add_source_manifest_entry(entry)
        manifest.setdefault("company_name", manifest.get("name"))
        manifest.setdefault("ticker", manifest.get("symbol"))
        manifest.setdefault("fiscal_year_end", manifest.get("year_end"))
        manifest.setdefault("source_url", manifest.get("source_url"))
        return manifest

    def _import_executive_compensation(
        self,
        company: Company,
        year: str,
        blob_name: str,
    ) -> None:
        rows = self._read_csv_blob(blob_name)
        for row in rows:
            full_name = _get_first(row, ["full_name", "executive_name", "name"], default="")
            if not full_name:
                continue
            person = self._ensure_person(
                row.get("person_id"),
                full_name,
                current_title=_get_first(row, ["current_title", "title", "position"], default=""),
                is_executive=True,
                bio_short=row.get("bio_short"),
                linkedin_url=row.get("linkedin_url"),
                photo_url=row.get("photo_url"),
                years_experience=_get_int(row, "years_experience", "experience_years"),
                education=_get_first(row, ["education", "education_background"]),
                status=_get_first(row, ["status", "employment_status"]),
            )
            fiscal_year = _parse_date(row.get("fiscal_year_end"), fallback=date(int(year), 12, 31))

            if row.get("company_name"):
                company.company_name = row["company_name"]
            if row.get("ticker"):
                company.ticker = row["ticker"]
            if row.get("source_url"):
                company.source_url = row["source_url"]
            fiscal_year_row = _parse_date(row.get("fiscal_year_end"))
            if fiscal_year_row:
                company.fiscal_year_end = fiscal_year_row
            salary_usd = _get_float(row, "salary_usd", "base_salary_usd", "base_salary", "salary")
            bonus_usd = _get_float(row, "bonus_usd", "cash_bonus_usd", "bonus", "cash_bonus")
            stock_awards_usd = _get_float(row, "stock_awards_usd", "stock_awards_fair_value_usd", "stock_awards", "stock_awards_value")
            option_awards_usd = _get_float(row, "option_awards_usd", "options_awards_usd", "option_awards", "options_awards")
            non_equity_usd = _get_float(row, "non_equity_incentive_usd", "non_equity_incentive_plan_usd", "non_equity_incentive")
            pension_change_usd = _get_float(row, "pension_change_usd", "change_in_pension_and_defcomp_earnings_usd", "pension_change")
            all_other_usd = _get_float(row, "all_other_comp_usd", "all_other_compensation_usd", "other_compensation_usd", "all_other_comp")
            total_comp = _get_float(row, "total_comp_usd", "total_compensation_usd", "total_compensation")
            if total_comp == 0.0:
                total_comp = (
                    salary_usd
                    + bonus_usd
                    + stock_awards_usd
                    + option_awards_usd
                    + non_equity_usd
                    + pension_change_usd
                    + all_other_usd
                )

            record = ExecutiveCompensation(
                company_id=company.company_id,
                person_id=person.person_id,
                fiscal_year_end=fiscal_year or date(int(year), 12, 31),
                salary_usd=salary_usd,
                bonus_usd=bonus_usd,
                stock_awards_usd=stock_awards_usd,
                option_awards_usd=option_awards_usd,
                non_equity_incentive_usd=non_equity_usd,
                pension_change_usd=pension_change_usd,
                all_other_comp_usd=all_other_usd,
                total_comp_usd=total_comp,
                source=row.get("source", f"{year} Proxy Statement"),
            )
            self.league_manager.add_executive_comp(record)

    def _import_equity_grants(self, company: Company, blob_name: str) -> None:
        rows = self._read_csv_blob(blob_name)
        for row in rows:
            full_name = _get_first(row, ["full_name", "executive_name", "name"], default="")
            if not full_name:
                continue
            person = self._ensure_person(
                row.get("person_id"),
                full_name,
                current_title=_get_first(row, ["current_title", "title"], default=""),
                is_executive=True,
            )
            grant_date = _parse_date(row.get("grant_date"))
            threshold_units = _get_int(row, "threshold_units")
            target_units = _get_int(row, "target_units", "rsu_units")
            max_units = _get_int(row, "max_units")
            if row.get("award_type", "").upper() == "RSU" and target_units == 0:
                target_units = _get_int(row, "rsu_units")
            record = ExecutiveEquityGrant(
                company_id=company.company_id,
                person_id=person.person_id,
                grant_date=grant_date or company.fiscal_year_end,
                award_type=row.get("type", row.get("award_type", "")),
                threshold_units=threshold_units,
                target_units=target_units,
                max_units=max_units,
                grant_date_fair_value_usd=_get_float(row, "grant_date_fair_value_usd", "grant_date_value_usd"),
                vesting_schedule_short=row.get("vesting_schedule_short", row.get("vesting_schedule")),
                source=row.get("source", f"{company.fiscal_year_end.year} Plan-Based Awards"),
            )
            self.league_manager.add_equity_grant(record)

    def _import_beneficial_ownership(self, company: Company, blob_name: str) -> None:
        rows = self._read_csv_blob(blob_name)
        for row in rows:
            full_name = _get_first(row, ["full_name", "name"], default="")
            if not full_name:
                continue
            person = self._ensure_person(
                row.get("person_id"),
                full_name,
                current_title=_get_first(row, ["current_title", "role", "title"], default=""),
                is_executive=_to_bool(row.get("is_executive")),
                is_director=_to_bool(row.get("is_director")),
            )
            record = BeneficialOwnershipRecord(
                company_id=company.company_id,
                person_id=person.person_id,
                role=_get_first(row, ["role", "title"], default=person.current_title),
                total_shares=_get_int(row, "total_shares", "total_shares_owned", "total_beneficial_ownership"),
                sole_voting_power=_get_int(row, "sole_voting_power", "direct_or_indirect_sole_voting", "ownership_of_common_stock"),
                shared_voting_power=_get_int(row, "shared_voting_power", "indirect_shared_voting", "equity_awards_exercisable_or_vesting_within_60d"),
                percent_of_class=_get_float(row, "percent_of_class", "percent_class"),
                as_of_date=_parse_date(row.get("as_of_date"), fallback=company.fiscal_year_end) or company.fiscal_year_end,
                notes=row.get("notes"),
            )
            self.league_manager.add_beneficial_ownership(record)

    def _import_director_compensation(self, company: Company, blob_name: str) -> None:
        rows = self._read_csv_blob(blob_name)
        for row in rows:
            full_name = _get_first(row, ["full_name", "director_name", "name"], default="")
            if not full_name:
                continue
            person = self._ensure_person(
                row.get("person_id"),
                full_name,
                current_title=_get_first(row, ["role", "title"], default="Director"),
                is_director=True,
            )
            fiscal_year = _parse_date(row.get("fiscal_year_end"), fallback=company.fiscal_year_end)
            record = DirectorCompensation(
                company_id=company.company_id,
                person_id=person.person_id,
                fiscal_year_end=fiscal_year or company.fiscal_year_end,
                fees_cash_usd=_get_float(row, "fees_cash_usd", "cash_fees_usd", "cash_retainers_usd"),
                stock_awards_usd=_get_float(row, "stock_awards_usd", "stock_grant_usd"),
                all_other_comp_usd=_get_float(row, "all_other_comp_usd", "all_other_compensation_usd"),
                total_usd=_get_float(row, "total_usd", "total_comp_usd", "total_compensation_usd"),
                source=row.get("source", f"{company.fiscal_year_end.year} Director Compensation"),
            )
            self.league_manager.add_director_comp(record)
    def _import_director_profiles(self, company: Company, blob_name: str) -> None:
        rows = self._read_csv_blob(blob_name)
        for row in rows:
            full_name = _get_first(row, ["full_name", "director_name", "name"], default="")
            if not full_name:
                continue
            person = self._ensure_person(
                row.get("person_id"),
                full_name,
                current_title=_get_first(row, ["role", "title"], default="Director"),
                is_director=True,
            )
            profile = DirectorProfile(
                company_id=company.company_id,
                person_id=person.person_id,
                role=_get_first(row, ["role", "title"], default=person.current_title),
                independent=_to_bool(row.get("independent", row.get("is_independent", True))),
                director_since=_get_int(row, "director_since", default=None),
                lead_independent_director=_to_bool(row.get("lead_independent_director", row.get("lead_independent", False))),
                committees=row.get("committees"),
                primary_occupation=row.get("primary_occupation", row.get("occupation")),
                other_public_boards=row.get("other_public_boards"),
            )
            self.league_manager.add_director_profile(profile)

    def _import_director_policy_file(self, company: Company, blob_name: str) -> None:
        rows = self._read_csv_blob(blob_name)
        for row in rows:
            component = _get_first(row, ["component", "policy_item"], default="")
            if not component:
                continue
            policy = DirectorCompPolicy(
                company_id=company.company_id,
                component=component,
                amount_usd=_get_float(row, "amount_usd", "value_usd"),
                unit=row.get("unit"),
                notes=row.get("notes"),
            )
            self.league_manager.add_director_policy(policy)

# ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_company_year(self, company_slug: str, year: str) -> None:
        prefix = f"companies/{company_slug}/{year}/"
        blobs = list(self.bucket.list_blobs(prefix=prefix))
        if not blobs:
            message = f"No files found for {company_slug} {year}"
            logger.info(message)
            self.load_warnings.append(message)
            return

        manifest_row: Dict[str, str] = {}
        for blob in blobs:
            filename = blob.name.split("/")[-1].lower()
            if filename.endswith("_manifest.csv"):
                manifest_row = self._import_manifest(company_slug, year, blob.name)
                break

        if not manifest_row:
            message = f"Manifest not found for {company_slug} {year}; using defaults"
            logger.warning(message)
            self.load_warnings.append(message)

        company = self._ensure_company(company_slug, manifest_row, year)

        recognized_files = 0
        for blob in blobs:
            filename = blob.name.split("/")[-1].lower()
            if not filename.endswith(CSV_SUFFIX):
                continue
            if filename.endswith("_manifest.csv"):
                continue
            if "executive_compensation" in filename:
                self._import_executive_compensation(company, year, blob.name)
                recognized_files += 1
            elif "executive_equity_grants" in filename:
                self._import_equity_grants(company, blob.name)
                recognized_files += 1
            elif "beneficial_ownership" in filename:
                self._import_beneficial_ownership(company, blob.name)
                recognized_files += 1
            elif "director_compensation" in filename:
                self._import_director_compensation(company, blob.name)
                recognized_files += 1
            elif "director_comp_policy" in filename or "director_compensation_policy" in filename:
                self._import_director_policy_file(company, blob.name)
                recognized_files += 1
            elif "directors_profiles" in filename or "director_profiles" in filename:
                self._import_director_profiles(company, blob.name)
                recognized_files += 1
            else:
                logger.debug("Skipping unrecognized file %s", blob.name)

        if recognized_files == 0:
            message = f"No recognized CSVs for {company_slug} {year}"
            logger.warning(message)
            self.load_warnings.append(message)

    def load_all_company_data(
        self,
        specific_year: Optional[str] = None,
        load_all_years: bool = False,
    ) -> Dict[str, object]:
        self.league_manager = LeagueManager()

        self.load_warnings = []

        try:
            company_slugs = self.list_company_folders()
            for company_slug in company_slugs:
                years = self.list_years_for_company(company_slug)
                if specific_year and specific_year in years:
                    target_years = [specific_year]
                elif load_all_years:
                    target_years = years
                elif years:
                    target_years = [max(years)]
                else:
                    target_years = []

                for year in target_years:
                    logger.info("Loading %s %s", company_slug, year)
                    self.load_company_year(company_slug, year)

            return {
                "status": "success",
                "companies_loaded": list(self.league_manager.companies.keys()),
                "companies_count": len(self.league_manager.companies),
                "people_count": len(self.league_manager.people),
                "executive_comp_count": len(self.league_manager.executive_comp),
                "years_loaded": [str(d.year) for d in self.league_manager.get_available_years()],
                "warnings": self.load_warnings,
                "league_manager": self.league_manager,
            }
        except Exception as exc:
            logger.exception("Failed to load company data: %s", exc)
            return {"status": "error", "message": str(exc), "warnings": self.load_warnings}

    def get_league_manager(self) -> LeagueManager:
        return self.league_manager
