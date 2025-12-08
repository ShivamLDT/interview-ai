"""
In-memory storage for interview sessions.

Note: This is suitable for development and single-instance deployments.
For production with multiple instances, migrate to Redis or a database.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict
from uuid import UUID

from app.interview.models import InterviewState


class InterviewStorage:
    """
    Thread-safe in-memory storage for interview sessions.
    
    Features:
    - Async-safe operations with locks
    - Automatic session cleanup for expired interviews
    - Session timeout configuration
    """
    
    def __init__(self, session_timeout_minutes: int = 60):
        """
        Initialize the storage.
        
        Args:
            session_timeout_minutes: Minutes after which inactive sessions expire
        """
        self._storage: Dict[UUID, InterviewState] = {}
        self._timestamps: Dict[UUID, datetime] = {}
        self._lock = asyncio.Lock()
        self._session_timeout = timedelta(minutes=session_timeout_minutes)
    
    async def create(self, interview: InterviewState) -> InterviewState:
        """
        Store a new interview session.
        
        Args:
            interview: The interview state to store
            
        Returns:
            The stored interview state
        """
        async with self._lock:
            self._storage[interview.interview_id] = interview
            self._timestamps[interview.interview_id] = datetime.utcnow()
            return interview
    
    async def get(self, interview_id: UUID) -> InterviewState | None:
        """
        Retrieve an interview session by ID.
        
        Args:
            interview_id: The unique interview identifier
            
        Returns:
            The interview state if found and not expired, None otherwise
        """
        async with self._lock:
            interview = self._storage.get(interview_id)
            
            if interview is None:
                return None
            
            # Check if session has expired
            timestamp = self._timestamps.get(interview_id)
            if timestamp and datetime.utcnow() - timestamp > self._session_timeout:
                # Session expired, clean it up
                del self._storage[interview_id]
                del self._timestamps[interview_id]
                return None
            
            # Update access timestamp
            self._timestamps[interview_id] = datetime.utcnow()
            return interview
    
    async def update(self, interview: InterviewState) -> InterviewState:
        """
        Update an existing interview session.
        
        Args:
            interview: The updated interview state
            
        Returns:
            The updated interview state
        """
        async with self._lock:
            self._storage[interview.interview_id] = interview
            self._timestamps[interview.interview_id] = datetime.utcnow()
            return interview
    
    async def delete(self, interview_id: UUID) -> bool:
        """
        Delete an interview session.
        
        Args:
            interview_id: The unique interview identifier
            
        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if interview_id in self._storage:
                del self._storage[interview_id]
                del self._timestamps[interview_id]
                return True
            return False
    
    async def exists(self, interview_id: UUID) -> bool:
        """
        Check if an interview session exists and is not expired.
        
        Args:
            interview_id: The unique interview identifier
            
        Returns:
            True if exists and not expired, False otherwise
        """
        interview = await self.get(interview_id)
        return interview is not None
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions removed
        """
        async with self._lock:
            now = datetime.utcnow()
            expired_ids = [
                interview_id
                for interview_id, timestamp in self._timestamps.items()
                if now - timestamp > self._session_timeout
            ]
            
            for interview_id in expired_ids:
                del self._storage[interview_id]
                del self._timestamps[interview_id]
            
            return len(expired_ids)
    
    async def get_active_count(self) -> int:
        """
        Get the number of active (non-expired) sessions.
        
        Returns:
            Number of active sessions
        """
        await self.cleanup_expired()
        async with self._lock:
            return len(self._storage)
    
    async def list_all(self) -> list[InterviewState]:
        """
        List all active interview sessions.
        
        Returns:
            List of all active interview states
        """
        await self.cleanup_expired()
        async with self._lock:
            return list(self._storage.values())


# Global storage instance
interview_storage = InterviewStorage(session_timeout_minutes=60)


def get_interview_storage() -> InterviewStorage:
    """Get the global interview storage instance."""
    return interview_storage

