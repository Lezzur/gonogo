import asyncio
import json
from typing import Dict, AsyncGenerator
from collections import defaultdict


class ProgressManager:
    """Manages SSE progress broadcasting for scans."""

    def __init__(self):
        self._subscribers: Dict[str, list] = defaultdict(list)
        self._latest_events: Dict[str, dict] = {}

    async def publish(self, scan_id: str, event_type: str, data: dict):
        """Publish an event to all subscribers of a scan."""
        event = {
            "event": event_type,
            "data": json.dumps(data)
        }
        self._latest_events[scan_id] = event

        for queue in self._subscribers[scan_id]:
            await queue.put(event)

    async def subscribe(self, scan_id: str) -> AsyncGenerator[dict, None]:
        """Subscribe to progress events for a scan."""
        queue = asyncio.Queue()
        self._subscribers[scan_id].append(queue)

        # Send latest event if available
        if scan_id in self._latest_events:
            yield self._latest_events[scan_id]

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event

                    # Stop on completion or error
                    if event.get("event") in ("complete", "error"):
                        break
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    yield {"event": "ping", "data": "{}"}
                    continue
        finally:
            self._subscribers[scan_id].remove(queue)
            if not self._subscribers[scan_id]:
                del self._subscribers[scan_id]

    async def send_progress(self, scan_id: str, step: str, message: str, percent: int):
        """Helper to send a progress event."""
        await self.publish(scan_id, "progress", {
            "step": step,
            "message": message,
            "percent": percent
        })

    async def send_complete(self, scan_id: str, verdict: str, overall_score: int):
        """Helper to send a completion event."""
        await self.publish(scan_id, "complete", {
            "scan_id": scan_id,
            "verdict": verdict,
            "overall_score": overall_score
        })

    async def send_error(self, scan_id: str, message: str):
        """Helper to send an error event."""
        await self.publish(scan_id, "error", {
            "message": message
        })


# Global progress manager instance
progress_manager = ProgressManager()
