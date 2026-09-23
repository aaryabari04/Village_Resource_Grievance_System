"""
FIFO Queue Implementation for Village Grievance Processing.
Implements First-In-First-Out (FIFO) discipline for sequential grievance review.
"""

from collections import deque
from typing import Any, List, Optional, Dict


class GrievanceQueue:
    """
    A FIFO (First-In, First-Out) Queue data structure.
    Used by administrative officers to review grievances strictly in the chronological
    order in which they were submitted by villagers.

    Time Complexities:
    - enqueue: O(1)
    - dequeue: O(1)
    - peek:    O(1)
    - size:    O(1)
    """

    def __init__(self, items: Optional[List[Dict[str, Any]]] = None):
        """Initializes an empty FIFO queue or loads an initial list of items."""
        self._queue = deque()
        if items:
            for item in items:
                self.enqueue(item)

    def enqueue(self, item: Dict[str, Any]) -> None:
        """
        Adds a grievance record to the rear of the queue.
        Time Complexity: O(1)
        """
        self._queue.append(item)

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Removes and returns the grievance record at the front of the queue.
        Returns None if queue is empty.
        Time Complexity: O(1)
        """
        if self.is_empty():
            return None
        return self._queue.popleft()

    def peek(self) -> Optional[Dict[str, Any]]:
        """
        Returns the grievance record at the front without removing it.
        Returns None if queue is empty.
        Time Complexity: O(1)
        """
        if self.is_empty():
            return None
        return self._queue[0]

    def is_empty(self) -> bool:
        """Checks whether the queue contains any items."""
        return len(self._queue) == 0

    def size(self) -> int:
        """Returns the total number of items currently in the queue."""
        return len(self._queue)

    def to_list(self) -> List[Dict[str, Any]]:
        """
        Converts the current queue into a Python list preserving FIFO order.
        Time Complexity: O(n)
        """
        return list(self._queue)

    def clear(self) -> None:
        """Empties the queue."""
        self._queue.clear()

    def __repr__(self) -> str:
        return f"<GrievanceQueue size={self.size()}>"
