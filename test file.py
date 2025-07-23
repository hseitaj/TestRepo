def _make_source_id(source_name: str) -> str:
    """Generate a stable STIX ID via UUID5."""
    return f"identity--{uuid5(NAMESPACE_DNS, 'feedly:source:' + source_name)}"

def _make_source_identity_object(source_name: str) -> dict:
    """Create a STIX Identity object for this author."""
    return {
        "type": "identity",
        "spec_version": "2.1",
        "id": _make_source_id(source_name),
        "name": source_name,
        "identity_class": "organization",
    }

def _process_authors(raw: str) -> str:
    """
    Strip non-alphanumeric/space chars, collapse whitespace,
    and limit to first two words.
    """
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch.isspace())
    return " ".join(cleaned.split()[:2])


def _add_source_name_as_author_to_report(report: dict) -> Optional[dict]:
    """
    1) Try report["authors"]
    2) Try custom fields: x_opencti_report_creator, x_opencti_source_name, creator
    3) Try external_references[*].source_name
    4) Build and return a STIX Identity, and set report["created_by_ref"], report["author"], report["authors"]
    """
    logging.debug(
        "Looking for author; authors=%r, x_opencti_report_creator=%r, "
        "x_opencti_source_name=%r, creator=%r, external_references=%r",
        report.get("authors"),
        report.get("x_opencti_report_creator"),
        report.get("x_opencti_source_name"),
        report.get("creator"),
        report.get("external_references"),
    )

    # 1) standard STIX extension
    authors = report.get("authors") or []

    # 2) known Feedly extension fields
    if not authors:
        for ext in ("x_opencti_report_creator", "x_opencti_source_name", "creator"):
            val = report.get(ext)
            if isinstance(val, str) and val.strip():
                authors = [val.strip()]
                break

    # 3) fallback to external_references[*].source_name
    if not authors:
        for ref in report.get("external_references", []):
            src = ref.get("source_name")
            if src and isinstance(src, str):
                authors = [src]
                break

    if not authors:
        return None

    raw = authors[0]
    clean = _process_authors(raw)
    identity_obj = _make_source_identity_object(clean)

    # rewrite the Report in place
    report["authors"]        = [clean]
    report["author"]         = clean
    report["created_by_ref"] = identity_obj["id"]

    return identity_obj


def _add_source_name_as_author_to_all_reports(bundle: dict) -> None:
    """
    Inject a STIX Identity for each report author, and append them to bundle["objects"].
    """
    new_identities = []
    for o in bundle.get("objects", []):
        if o.get("type") == "report":
            id_obj = _add_source_name_as_author_to_report(o)
            if id_obj:
                new_identities.append(id_obj)

    if new_identities:
        bundle["objects"].extend(new_identities)
