UNKNOWN_REGION = "unknown-region"


def _normalize(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def extract_region(data):
    """Extract the ChirpStack region while tolerating legacy tag whitespace."""
    region = _normalize(
        data.get("regionConfigId") or data.get("region_config_id")
    )
    if region:
        return region

    tags = data.get("deviceInfo", {}).get("tags", {})
    if isinstance(tags, dict):
        for key, value in tags.items():
            if _normalize(key) == "region_name":
                region = _normalize(value)
                if region:
                    return region

    return UNKNOWN_REGION
