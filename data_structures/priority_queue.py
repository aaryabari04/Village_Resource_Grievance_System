"""
Priority Queue Implementation for Village Grievances using Python's heapq module.
Allows emergency and high-priority grievances to be processed before medium/low ones.
"""

import heapq
from typing import Any, Dict, List, Optional
import itertools

# Numerical priority rank mapping: lower number means higher priority in the min-heap
# Emergency (1) > High (2) > Medium (3) > Low (4)
DEFAULT_PRIORITY_WEIGHTS = {
    "Emergency": 1,
    "High": 2,
    "Medium": 3,
    "Low": 4
}


class GrievancePriorityQueue:
    """
    Min-Heap backed Priority Queue data structure.
    Used by administrators to triage complaints so that urgent village issues
    (e.g., burst main pipelines, medical emergencies, collapsed electric poles)
    are surfaced and acted upon immediately.

    Tuple stored in heap: (priority_weight, tie_breaker_counter, grievance_dict)
    The tie_breaker_counter ensures:
      1. FIFO ordering for items having equal priority.
      2. Python never compares the grievance dictionary objects directly.

    Time Complexities:
    - push:           O(log n)
    - pop:            O(log n)
    - peek:           O(1)
    - to_sorted_list: O(n log n)
    """

    def __init__(self, priority_weights: Optional[Dict[str, int]] = None):
        self._heap = []
        self._counter = itertools.count()  # Unique sequence counter for FIFO stability
        self.priority_weights = priority_weights or DEFAULT_PRIORITY_WEIGHTS

    def push(self, grievance: Dict[str, Any]) -> None:
        """
        Inserts a grievance into the priority queue according to its urgency.
        Time Complexity: O(log n)
        """
        priority_label = grievance.get("priority", "Medium")
        # Default to 3 (Medium) if unknown priority string
        weight = self.priority_weights.get(priority_label, 3)
        count = next(self._counter)
        heapq.heappush(self._heap, (weight, count, grievance))

    def pop(self) -> Optional[Dict[str, Any]]:
        """
        Removes and returns the grievance with the highest priority (lowest weight).
        Time Complexity: O(log n)
        """
        if self.is_empty():
            return None
        weight, count, grievance = heapq.heappop(self._heap)
        return grievance

    def peek(self) -> Optional[Dict[str, Any]]:
        """
        Returns the highest priority grievance without removing it.
        Time Complexity: O(1)
        """
        if self.is_empty():
            return None
        return self._heap[0][2]

    def size(self) -> int:
        """Returns the number of elements in the priority queue."""
        return len(self._heap)

    def is_empty(self) -> bool:
        """Checks if the priority queue has no items."""
        return len(self._heap) == 0

    def to_sorted_list(self) -> List[Dict[str, Any]]:
        """
        Returns all grievances ordered from highest priority to lowest priority
        without permanently modifying the underlying queue.
        Time Complexity: O(n log n)
        """
        # Create a shallow copy of the heap list to drain
        heap_copy = list(self._heap)
        sorted_items = []
        while heap_copy:
            weight, count, grievance = heapq.heappop(heap_copy)
            sorted_items.append(grievance)
        return sorted_items

    @classmethod
    def prioritize_grievances(cls, grievances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convenience factory method: Takes a list of grievances, builds a Priority Queue,
        and returns the grievances sorted in strict priority order.
        """
        pq = cls()
        for g in grievances:
            pq.push(g)
        return pq.to_sorted_list()

    def __repr__(self) -> str:
        return f"<GrievancePriorityQueue size={self.size()}>"
