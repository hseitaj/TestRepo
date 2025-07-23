def _add_source_name_as_author_to_report(report: dict) -> Optional[dict]:
    """
    1. Look for report["authors"] or fall back to feedly extensions.
    2. Take the first name, sanitize it, build a STIX Identity,
       set report["created_by_ref"], report["author(s)"].
    3. Return the new Identity object for later injection into the bundle.
    """
    # 1) Try standard STIX property
    authors = report.get("authors") or []

    # 2) Fallback to Feedly custom fields
    if not authors:
        for ext in ("x_opencti_report_creator", "x_opencti_source_name"):
            val = report.get(ext)
            if isinstance(val, str) and val.strip():
                authors = [val.strip()]
                break

    if not authors:
        return None

    raw = str(authors[0]).strip()
    clean = _process_authors(raw)

    # Build the identity object
    identity_obj = _make_source_identity_object(clean)

    # Rewrite the report in place
    report["authors"]        = [clean]
    report["author"]         = clean
    report["created_by_ref"] = identity_obj["id"]

    return identity_obj

def _add_source_name_as_author_to_all_reports(bundle: dict) -> None:
    """
    For each STIX Report in bundle["objects"], extract its author
    and collect the new Identity objects to append at the end.
    """
    new_identities = []
    for o in bundle.get("objects", []):
        if o.get("type") == "report":
            id_obj = _add_source_name_as_author_to_report(o)
            if id_obj:
                new_identities.append(id_obj)

    # Inject all new identities into the bundle
    if new_identities:
        bundle["objects"].extend(new_identities)
