"""
Progress tracking for streaming updates to frontend.
Uses in-memory storage for real-time progress updates.
"""
from typing import Optional, Any
from datetime import datetime
import asyncio
from loguru import logger


class ProgressTracker:
    """Tracks progress of long-running operations for streaming to frontend."""
    
    def __init__(self):
        self._progress: dict[str, list[dict]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._completed: dict[str, bool] = {}
    
    def start_operation(self, operation_id: str, operation_type: str):
        """Start tracking a new operation."""
        self._progress[operation_id] = []
        self._subscribers[operation_id] = []
        self._completed[operation_id] = False
        self.add_step(operation_id, "started", f"Starting {operation_type}...", {"type": operation_type})
        logger.debug(f"[ProgressTracker] Started operation: {operation_id}")
    
    def add_step(
        self, 
        operation_id: str, 
        step_type: str,
        message: str, 
        data: Optional[dict] = None,
        progress_percent: Optional[float] = None
    ):
        """Add a progress step and notify subscribers."""
        if operation_id not in self._progress:
            self._progress[operation_id] = []
        
        step = {
            "timestamp": datetime.now().isoformat(),
            "type": step_type,  # info, success, warning, error, ai, progress
            "message": message,
            "data": data or {},
            "progress_percent": progress_percent
        }
        
        self._progress[operation_id].append(step)
        
        # Notify all subscribers
        for queue in self._subscribers.get(operation_id, []):
            try:
                queue.put_nowait(step)
            except asyncio.QueueFull:
                pass
        
        logger.debug(f"[ProgressTracker] {operation_id}: {step_type} - {message}")
    
    def complete_operation(self, operation_id: str, result: Optional[dict] = None):
        """Mark operation as complete."""
        self._completed[operation_id] = True
        self.add_step(
            operation_id, 
            "completed", 
            "Operation completed",
            data=result,
            progress_percent=100.0
        )
        
        # Signal end to all subscribers
        for queue in self._subscribers.get(operation_id, []):
            try:
                queue.put_nowait({"type": "end", "message": "Stream ended"})
            except asyncio.QueueFull:
                pass
        
        logger.debug(f"[ProgressTracker] Completed operation: {operation_id}")
    
    def fail_operation(self, operation_id: str, error: str):
        """Mark operation as failed."""
        self._completed[operation_id] = True
        self.add_step(operation_id, "error", f"Operation failed: {error}")
        
        # Signal end to all subscribers
        for queue in self._subscribers.get(operation_id, []):
            try:
                queue.put_nowait({"type": "end", "message": "Stream ended"})
            except asyncio.QueueFull:
                pass
    
    def subscribe(self, operation_id: str) -> asyncio.Queue:
        """Subscribe to progress updates for an operation."""
        if operation_id not in self._subscribers:
            self._subscribers[operation_id] = []
        
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[operation_id].append(queue)
        
        # Send any existing progress
        for step in self._progress.get(operation_id, []):
            try:
                queue.put_nowait(step)
            except asyncio.QueueFull:
                pass
        
        return queue
    
    def unsubscribe(self, operation_id: str, queue: asyncio.Queue):
        """Unsubscribe from progress updates."""
        if operation_id in self._subscribers:
            if queue in self._subscribers[operation_id]:
                self._subscribers[operation_id].remove(queue)
    
    def is_completed(self, operation_id: str) -> bool:
        """Check if operation is completed."""
        return self._completed.get(operation_id, False)
    
    def get_progress(self, operation_id: str) -> list[dict]:
        """Get all progress steps for an operation."""
        return self._progress.get(operation_id, [])
    
    def cleanup(self, operation_id: str):
        """Clean up progress data for an operation."""
        self._progress.pop(operation_id, None)
        self._subscribers.pop(operation_id, None)
        self._completed.pop(operation_id, None)


# Global progress tracker instance
progress_tracker = ProgressTracker()
