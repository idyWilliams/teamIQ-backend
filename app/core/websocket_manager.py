from typing import Dict, List
from fastapi import WebSocket
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # mapping key 
        self.active_connections: Dict[str, List[WebSocket]] = {}
        #lock for guarding purposes
        self._lock = asyncio.Lock()

    async def connect(self, key: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            if key not in self.active_connections:
                self.active_connections[key] = []
            self.active_connections[key].append(websocket)
        logger.debug(f"WebSocket connected for {key}. Total connections: {len(self.active_connections.get(key, []))}")

    def disconnect(self, key: str, websocket: WebSocket):
        if key in self.active_connections:
            try:
                self.active_connections[key].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[key]:
                del self.active_connections[key]
        logger.debug(f"WebSocket disconnected for {key}. Remaining connections: {len(self.active_connections.get(key, [])) if key in self.active_connections else 0}")

    async def send_personal_message(self, key: str, message: dict):
      
        connections = self.active_connections.get(key, []).copy()
        if not connections:
            logger.debug(f"No active ws connections for {key}, skipping send.")
            return

        text = json.dumps(message)
        for conn in connections:
            try:
                await conn.send_text(text)
            except Exception as e:
                logger.warning(f"Error sending ws message to {key}: {e}")
                try:
                    self.disconnect(key, conn)
                except Exception:
                    pass

    async def broadcast(self, message: dict):
      
        all_keys = list(self.active_connections.keys())
        for key in all_keys:
            await self.send_personal_message(key, message)

# global instance used by the app
manager = ConnectionManager()
