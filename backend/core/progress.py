"""
Progress tracking for streaming updates to frontend.
Uses in-memory storage for real-time progress updates.
Supports checkpoints for resume functionality and cancellation tokens.
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
        # New: Step tracking
        self._step_info: dict[str, dict] = {}  # {op_id: {current_step, total_steps, step_name}}
        # New: Checkpoint storage for resume functionality
        self._checkpoints: dict[str, dict] = {}
        # New: Cancellation tokens
        self._cancelled: dict[str, bool] = {}
        # New: Operation status (running, paused, quota_exceeded, completed, error)
        self._status: dict[str, str] = {}
    
    def start_operation(self, operation_id: str, operation_type: str, total_steps: int = 10):
        """Start tracking a new operation."""
        self._progress[operation_id] = []
        self._subscribers[operation_id] = []
        self._completed[operation_id] = False
        self._cancelled[operation_id] = False
        self._status[operation_id] = "running"
        self._step_info[operation_id] = {
            "current_step": 0,
            "total_steps": total_steps,
            "step_name": f"Starting {operation_type}..."
        }
        self.add_step(operation_id, "started", f"Starting {operation_type}...", {
            "type": operation_type,
            "current_step": 0,
            "total_steps": total_steps,
            "status": "running"
        })
        logger.debug(f"[ProgressTracker] Started operation: {operation_id}")
    
    def add_step(
        self, 
        operation_id: str, 
        step_type: str,
        message: str, 
        data: Optional[dict] = None,
        progress_percent: Optional[float] = None,
        current_step: Optional[int] = None,
        step_name: Optional[str] = None,
        total_steps: Optional[int] = None
    ):
        """Add a progress step and notify subscribers."""
        if operation_id not in self._progress:
            self._progress[operation_id] = []
        
        # Update step info if provided
        if operation_id in self._step_info:
            if current_step is not None:
                self._step_info[operation_id]["current_step"] = current_step
            if step_name is not None:
                self._step_info[operation_id]["step_name"] = step_name
            if total_steps is not None:
                self._step_info[operation_id]["total_steps"] = total_steps
        
        # Build step data with step info
        step_info = self._step_info.get(operation_id, {})
        step = {
            "timestamp": datetime.now().isoformat(),
            "type": step_type,  # info, success, warning, error, ai, progress, data, quota_exceeded
            "message": message,
            "data": data or {},
            "progress_percent": progress_percent,
            "current_step": step_info.get("current_step"),
            "total_steps": step_info.get("total_steps"),
            "step_name": step_info.get("step_name"),
            "status": self._status.get(operation_id, "running")
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
        self._step_info.pop(operation_id, None)
        self._checkpoints.pop(operation_id, None)
        self._cancelled.pop(operation_id, None)
        self._status.pop(operation_id, None)
    
    # ========== Step Tracking ==========
    
    def set_total_steps(self, operation_id: str, total_steps: int):
        """Set the total number of steps for an operation."""
        if operation_id not in self._step_info:
            self._step_info[operation_id] = {}
        self._step_info[operation_id]["total_steps"] = total_steps
    
    def update_step(self, operation_id: str, current_step: int, step_name: str):
        """Update current step info."""
        if operation_id not in self._step_info:
            self._step_info[operation_id] = {"total_steps": 10}
        self._step_info[operation_id]["current_step"] = current_step
        self._step_info[operation_id]["step_name"] = step_name
    
    def get_step_info(self, operation_id: str) -> dict:
        """Get current step info."""
        return self._step_info.get(operation_id, {})
    
    # ========== Checkpoint System ==========
    
    def save_checkpoint(self, operation_id: str, checkpoint_data: dict):
        """Save checkpoint data for resume functionality."""
        self._checkpoints[operation_id] = {
            "timestamp": datetime.now().isoformat(),
            "data": checkpoint_data
        }
        logger.info(f"[ProgressTracker] Saved checkpoint for {operation_id}")
    
    def get_checkpoint(self, operation_id: str) -> Optional[dict]:
        """Get checkpoint data for an operation."""
        checkpoint = self._checkpoints.get(operation_id)
        if checkpoint:
            return checkpoint.get("data")
        return None
    
    def has_checkpoint(self, operation_id: str) -> bool:
        """Check if a checkpoint exists for an operation."""
        return operation_id in self._checkpoints
    
    def clear_checkpoint(self, operation_id: str):
        """Clear checkpoint data."""
        self._checkpoints.pop(operation_id, None)
    
    # ========== Cancellation System ==========
    
    def cancel_operation(self, operation_id: str):
        """Mark an operation as cancelled."""
        self._cancelled[operation_id] = True
        self._status[operation_id] = "paused"
        self.add_step(operation_id, "paused", "Operation paused by user")
        logger.info(f"[ProgressTracker] Cancelled operation: {operation_id}")
    
    def is_cancelled(self, operation_id: str) -> bool:
        """Check if an operation has been cancelled."""
        return self._cancelled.get(operation_id, False)
    
    def reset_cancellation(self, operation_id: str):
        """Reset cancellation flag for resume."""
        self._cancelled[operation_id] = False
        self._status[operation_id] = "running"
    
    # ========== Status Management ==========
    
    def set_status(self, operation_id: str, status: str):
        """Set operation status: running, paused, quota_exceeded, completed, error."""
        self._status[operation_id] = status
        # Notify subscribers of status change
        self.add_step(operation_id, "status_change", f"Status changed to: {status}", {"status": status})
    
    def get_status(self, operation_id: str) -> str:
        """Get operation status."""
        return self._status.get(operation_id, "idle")
    
    def set_quota_exceeded(self, operation_id: str):
        """Mark operation as quota exceeded."""
        self._status[operation_id] = "quota_exceeded"
        self.add_step(
            operation_id, 
            "quota_exceeded", 
            "Gemini API quota exceeded. Please enter a new API key to continue.",
            {"status": "quota_exceeded"}
        )
        logger.warning(f"[ProgressTracker] Quota exceeded for operation: {operation_id}")
    
    def fail_operation(self, operation_id: str, error: str):
        """Mark operation as failed."""
        self._completed[operation_id] = True
        self._status[operation_id] = "error"
        self.add_step(operation_id, "error", f"Operation failed: {error}", {"status": "error"})
        
        # Signal end to all subscribers
        for queue in self._subscribers.get(operation_id, []):
            try:
                queue.put_nowait({"type": "end", "message": "Stream ended"})
            except asyncio.QueueFull:
                pass


# Global progress tracker instance
progress_tracker = ProgressTracker()
