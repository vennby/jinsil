import csv
import json
from pathlib import Path

def _load_candidates(candidates_json):
    """Load candidates from a JSON file or directly from a list of candidate dictionaries."""
    if isinstance(candidates_json, (str, Path)):
        with open(candidates_json, "r", encoding="utf-8") as file:
            candidates = json.load(file)
    else:
        candidates = candidates_json

    if not isinstance(candidates, list):
        raise ValueError("Expected candidates JSON to be a list of candidate objects.")

    return candidates

def extract_candidate_years_of_experience(candidate):
    """Return one candidate's years of experience from the schema profile block."""
    try:
        return candidate["candidate_id"], float(candidate["profile"]["years_of_experience"])
    except KeyError as exc:
        raise ValueError(f"Candidate is missing required field: {exc}") from exc
    except (TypeError, ValueError) as exc:
        candidate_id = candidate.get("candidate_id", "<unknown>")
        raise ValueError(
            f"Candidate {candidate_id} has an invalid years_of_experience value."
        ) from exc

def extract_profile_completeness_score(candidate):
    """Return one candidate's profile completeness score from the schema profile block."""
    try:
        return candidate["candidate_id"], float(
            candidate["redrob_signals"]["profile_completeness_score"]
        )
    except KeyError as exc:
        raise ValueError(f"Candidate is missing required field: {exc}") from exc
    except (TypeError, ValueError) as exc:
        candidate_id = candidate.get("candidate_id", "<unknown>")
        raise ValueError(
            f"Candidate {candidate_id} has an invalid profile_completeness_score value."
        ) from exc

EXTRACTABLE_FIELDS = {
    "years_of_experience": lambda candidate: float(
        candidate["profile"]["years_of_experience"]
    ),
    "profile_completeness_score": lambda candidate: float(
        candidate["redrob_signals"]["profile_completeness_score"]
    ),
}

def _default_output_path(fields):
    """Generate a default output path based on the selected fields."""
    field_part = "_".join(fields)
    return Path(f"extracted_{field_part}.csv")

def extract_data(candidates_json, fields, output_path=None):
    """
    Extract selected fields for every candidate and write them to a CSV.

    Args:
        candidates_json: Either a path to a JSON file like sample_candidates.json,
            or an already-loaded list of candidate dictionaries.
        fields: Iterable of field names to extract. Supported values are the keys
            in EXTRACTABLE_FIELDS.
        output_path: Optional CSV path. Defaults to extracted_<field_names>.csv.

    Returns:
        list of row dictionaries written to the CSV.
    """
    candidates = _load_candidates(candidates_json)
    fields = list(fields)

    if not fields:
        raise ValueError("At least one field must be selected for extraction.")

    unknown_fields = [field for field in fields if field not in EXTRACTABLE_FIELDS]
    if unknown_fields:
        supported_fields = ", ".join(EXTRACTABLE_FIELDS)
        raise ValueError(
            f"Unsupported fields: {', '.join(unknown_fields)}. "
            f"Supported fields: {supported_fields}."
        )

    rows = []
    for candidate in candidates:
        try:
            row = {"candidate_id": candidate["candidate_id"]}
            for field in fields:
                row[field] = EXTRACTABLE_FIELDS[field](candidate)
        except KeyError as exc:
            candidate_id = candidate.get("candidate_id", "<unknown>")
            raise ValueError(
                f"Candidate {candidate_id} is missing required field: {exc}"
            ) from exc
        except (TypeError, ValueError) as exc:
            candidate_id = candidate.get("candidate_id", "<unknown>")
            raise ValueError(
                f"Candidate {candidate_id} has an invalid extractable value."
            ) from exc

        rows.append(row)

    output_path = Path(output_path) if output_path else _default_output_path(fields)
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["candidate_id", *fields])
        writer.writeheader()
        writer.writerows(rows)

    return rows

if __name__ == "__main__":
    candidates_file = "sample_candidates.json"
    selected_fields = ["years_of_experience", "profile_completeness_score"]
    extract_data(candidates_file, selected_fields)