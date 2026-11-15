"""
app/models.py
Typed model for one AapleSeva notified service record.

The six target fields are the project's canonical schema. Which of them is
populated depends on which document the record came from, because the state
publishes its notified services in two different shapes:

``NS_Service_List.pdf`` (parsed by ``app/ingest.py``) is the statewide list of
all 1058 notified services. It has five columns and carries no time limit and
no officer names, so records from it populate three of the six fields:

    service_name, department, source_url

Each department also issues its own notification under Section 3(1) of the
Act, and those tabulate exactly what the statewide list omits. Records from
those (parsed by ``app/proforma.py``) populate all six:

    service_name, department, source_url,
    time_limit_days, designated_officer, first_appellate_officer

Where a source is silent the field stays None rather than being guessed, so a
null in data/records.json always means "this document does not say", never
"we failed to parse it". Use ``is_complete()`` / ``missing_fields()`` to tell
the two kinds of record apart.
"""

from dataclasses import dataclass, asdict, fields


@dataclass
class Record:
    """One notified public service under the Maharashtra Right to Service Act."""

    # --- the six target fields ---
    service_name: str
    department: str | None = None
    time_limit_days: int | None = None
    designated_officer: str | None = None
    first_appellate_officer: str | None = None
    source_url: str = ""

    # --- extra columns the sources genuinely publish ---
    # `id` mirrors the statewide PDF's serial number (अ.क्र) and keeps
    # records.json compatible with app.records.get_by_id().
    id: int | None = None
    sub_department: str | None = None
    available_on_portal: bool | None = None

    # The department proformas also name a second appellate authority, and
    # state the time limit in prose that does not always reduce to one number
    # ("30 Days if home visit is required otherwise 03 Working Days"), so the
    # wording is kept alongside the parsed integer.
    second_appellate_officer: str | None = None
    time_limit_text: str | None = None

    # Provenance: which document and which page of it this row came from.
    source_page: int | None = None
    text_quality: str | None = None

    def __post_init__(self):
        """Normalise and validate the fields. Raises ValueError on a bad row."""
        # service_name is the one field a record cannot be without.
        self.service_name = _clean_text(self.service_name) or ""
        if not self.service_name:
            raise ValueError("service_name must not be empty")

        self.department = _clean_text(self.department)
        self.designated_officer = _clean_text(self.designated_officer)
        self.first_appellate_officer = _clean_text(self.first_appellate_officer)
        self.second_appellate_officer = _clean_text(self.second_appellate_officer)
        self.sub_department = _clean_text(self.sub_department)
        self.time_limit_text = _clean_text(self.time_limit_text)
        self.source_url = _clean_text(self.source_url) or ""

        if self.source_page is not None:
            try:
                self.source_page = int(self.source_page)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"source_page must be a whole number, got {self.source_page!r}"
                ) from exc

        if self.time_limit_days is not None:
            try:
                self.time_limit_days = int(self.time_limit_days)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"time_limit_days must be a whole number of days, "
                    f"got {self.time_limit_days!r}"
                ) from exc
            if self.time_limit_days < 0:
                raise ValueError(
                    f"time_limit_days must not be negative, got {self.time_limit_days}"
                )

        if self.id is not None:
            try:
                self.id = int(self.id)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"id must be a whole number, got {self.id!r}") from exc

    def to_dict(self) -> dict:
        """Return the record as a plain dict, ready for json.dump()."""
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "Record":
        """
        Build a Record from a dict, ignoring unknown keys.

        Lets data/records.json be read back without exploding if the file was
        written by a newer version of the schema.
        """
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def is_complete(self) -> bool:
        """True if every one of the six target fields is populated."""
        return all(
            getattr(self, name) is not None and getattr(self, name) != ""
            for name in (
                "service_name",
                "department",
                "time_limit_days",
                "designated_officer",
                "first_appellate_officer",
                "source_url",
            )
        )

    def missing_fields(self) -> list[str]:
        """Names of the target fields the source did not supply."""
        out = []
        for name in (
            "service_name",
            "department",
            "time_limit_days",
            "designated_officer",
            "first_appellate_officer",
            "source_url",
        ):
            value = getattr(self, name)
            if value is None or value == "":
                out.append(name)
        return out


def _clean_text(value) -> str | None:
    """
    Collapse whitespace in a cell and turn blanks into None.

    PDF cells arrive with hard line breaks, runs of padding spaces and
    non-breaking spaces, all of which should not survive into the JSON.
    """
    if value is None:
        return None
    text = str(value).replace("\u00a0", " ")
    text = " ".join(text.split())
    return text or None
