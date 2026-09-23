"""
Searching and Sorting Algorithms for Village Resources and Grievance Management.
Implements multi-attribute filtering, linear search, and custom multi-criteria sorting.
"""

from typing import List, Dict, Any, Callable
from config import PRIORITY_WEIGHTS, ALLOWED_STATUSES

# Status workflow ordering for logical sorting
STATUS_ORDER = {
    "Submitted": 1,
    "Verified": 2,
    "Assigned": 3,
    "In Progress": 4,
    "Resolved": 5,
    "Rejected": 6
}


# =====================================================================
# SEARCHING ALGORITHMS
# =====================================================================

def search_resources(resources: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Performs case-insensitive multi-attribute search over a list of village resources.
    Matches across 'name', 'category', 'location', and 'description'.
    Supports space-separated query keywords (AND matching).

    Time Complexity: O(N * M) where N is number of resources and M is text length.

    :param resources: List of resource dictionaries from SQLite
    :param query: Search string entered by villager (e.g., 'water tank', 'clinic')
    :return: Filtered list of matching resources
    """
    if not query or not query.strip():
        return resources

    keywords = query.strip().lower().split()
    results = []

    for item in resources:
        # Aggregate searchable text into a unified string
        searchable_text = " ".join([
            str(item.get("name", "")),
            str(item.get("category", "")),
            str(item.get("location", "")),
            str(item.get("description", "")),
            str(item.get("contact", ""))
        ]).lower()

        # Item must contain all keywords
        if all(kw in searchable_text for kw in keywords):
            results.append(item)

    return results


def search_grievances(grievances: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Searches grievances by grievance_code (exact or substring), subject,
    category, location, or submitter name.

    Time Complexity: O(N * M)
    """
    if not query or not query.strip():
        return grievances

    keywords = query.strip().lower().split()
    results = []

    for item in grievances:
        searchable_text = " ".join([
            str(item.get("grievance_code", "")),
            str(item.get("subject", "")),
            str(item.get("category", "")),
            str(item.get("location", "")),
            str(item.get("description", "")),
            str(item.get("submitter_name", "")),
            str(item.get("department_name", ""))
        ]).lower()

        if all(kw in searchable_text for kw in keywords):
            results.append(item)

    return results


# =====================================================================
# SORTING ALGORITHMS
# =====================================================================

def sort_grievances_by_priority(grievances: List[Dict[str, Any]], reverse: bool = False) -> List[Dict[str, Any]]:
    """
    Sorts a list of grievances by priority severity.
    Emergency (1) -> High (2) -> Medium (3) -> Low (4)

    Time Complexity: O(N log N) using Timsort.
    """
    return sorted(
        grievances,
        key=lambda g: PRIORITY_WEIGHTS.get(g.get("priority", "Medium"), 3),
        reverse=reverse
    )


def sort_grievances_by_date(grievances: List[Dict[str, Any]], reverse: bool = True) -> List[Dict[str, Any]]:
    """
    Sorts a list of grievances by created_at timestamp.
    Default reverse=True yields newest grievances first.

    Time Complexity: O(N log N).
    """
    return sorted(
        grievances,
        key=lambda g: g.get("created_at", ""),
        reverse=reverse
    )


def sort_grievances_by_status(grievances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sorts grievances according to their position in the administrative lifecycle:
    Submitted -> Verified -> Assigned -> In Progress -> Resolved -> Rejected

    Time Complexity: O(N log N).
    """
    return sorted(
        grievances,
        key=lambda g: STATUS_ORDER.get(g.get("status", "Submitted"), 99)
    )
