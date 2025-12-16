from typing import List, Dict, Optional, Any
from ..data.regions import ALL_REGIONS

def get_all_regions() -> List[Dict[str, Any]]:
    """
    Returns a list of all available regions with their metadata.
    Does not include full geometry to keep the list lightweight for frontend dropdowns.
    """
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "province": r.get("province")  # Only for districts
        }
        for r in ALL_REGIONS
    ]

def get_region_by_id(region_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns the full region object (including geometry) for a given ID.
    """
    for region in ALL_REGIONS:
        if region["id"] == region_id:
            return region
    return None

def get_regions_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Returns all regions belonging to a specific category.
    """
    return [r for r in ALL_REGIONS if r["category"] == category]
