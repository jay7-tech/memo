"""
Context Manager
Provides time-based and situational context awareness.
"""

from datetime import datetime, time as dt_time
from typing import Optional, Dict
from enum import Enum


class TimeOfDay(Enum):
    """Time periods for contextual responses."""
    EARLY_MORNING = "early_morning"  # 5:00 - 7:00
    MORNING = "morning"              # 7:00 - 12:00
    AFTERNOON = "afternoon"          # 12:00 - 17:00
    EVENING = "evening"              # 17:00 - 21:00
    NIGHT = "night"                  # 21:00 - 23:00
    LATE_NIGHT = "late_night"        # 23:00 - 5:00


class UserState(Enum):
    """User presence states."""
    JUST_ARRIVED = "just_arrived"
    PRESENT = "present"
    RETURNED = "returned"  # After absence
    ABSENT = "absent"
    LONG_ABSENT = "long_absent"  # >1 hour


class ContextManager:
    """Manages contextual information for personalized interactions."""
    
    def __init__(self):
        self.last_seen_time: Optional[datetime] = None
        self.last_greeting_time: Optional[datetime] = None
        self.session_start: Optional[datetime] = None
        self.absence_threshold_minutes = 5  # Consider absent after 5 min
        self.long_absence_threshold_minutes = 60
        self.greeting_cooldown_minutes = 30  # Don't re-greet within 30 min
    
    def get_time_of_day(self, hour: Optional[int] = None) -> TimeOfDay:
        """
        Get current time period.
        
        Args:
            hour: Hour to check (optional, defaults to now)
            
        Returns:
            TimeOfDay enum value
        """
        if hour is None:
            hour = datetime.now().hour
        
        if 5 <= hour < 7:
            return TimeOfDay.EARLY_MORNING
        elif 7 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 21:
            return TimeOfDay.EVENING
        elif 21 <= hour < 23:
            return TimeOfDay.NIGHT
        else:
            return TimeOfDay.LATE_NIGHT
    
    def get_greeting(self, name: str = "there") -> str:
        """
        Get time-appropriate greeting.
        
        Args:
            name: User's name
            
        Returns:
            Contextual greeting message
        """
        time_period = self.get_time_of_day()
        user_state = self.get_user_state()
        
        # Check if we should greet
        if not self._should_greet():
            return None
        
        # Time-based greetings
        greetings = {
            TimeOfDay.EARLY_MORNING: [
                f"Good morning, {name}! You're up early.",
                f"Rise and shine, {name}!",
                f"Early bird, {name}!"
            ],
            TimeOfDay.MORNING: [
                f"Good morning, {name}!",
                f"Morning, {name}! Ready to be productive?",
                f"Hello {name}, have a great day!"
            ],
            TimeOfDay.AFTERNOON: [
                f"Good afternoon, {name}!",
                f"Hi {name}, hope you're having a good day!",
                f"Afternoon, {name}!"
            ],
            TimeOfDay.EVENING: [
                f"Good evening, {name}!",
                f"Evening, {name}! How was your day?",
                f"Welcome back, {name}!"
            ],
            TimeOfDay.NIGHT: [
                f"Good evening, {name}!",
                f"Hello {name}, still working?",
                f"Evening, {name}!"
            ],
            TimeOfDay.LATE_NIGHT: [
                f"Working late, {name}?",
                f"Hello {name}. It's getting late!",
                f"Night owl hours, {name}?"
            ]
        }
        
        # Modify based on user state
        if user_state == UserState.JUST_ARRIVED:
            prefix = "Welcome, "
        elif user_state == UserState.RETURNED:
            prefix = "Welcome back, "
        else:
            prefix = ""
        
        # Select greeting
        import random
        base_greeting = random.choice(greetings[time_period])
        
        # Add prefix if applicable
        if prefix and ", " in base_greeting:
            base_greeting = base_greeting.replace(", ", " ")
            base_greeting = prefix + base_greeting.lower()
        
        # Update state
        self.last_greeting_time = datetime.now()
        
        return base_greeting
    
    def update_presence(self, user_detected: bool) -> None:
        """
        Update user presence tracking.
        
        Args:
            user_detected: Whether user is currently detected
        """
        now = datetime.now()
        
        if user_detected:
            if self.last_seen_time is None:
                # First time seeing user
                self.session_start = now
            
            self.last_seen_time = now
        # If not detected, last_seen_time stays at previous value
    
    def get_user_state(self) -> UserState:
        """
        Determine current user state.
        
        Returns:
            UserState enum value
        """
        if self.last_seen_time is None:
            return UserState.ABSENT
        
        now = datetime.now()
        minutes_since_seen = (now - self.last_seen_time).total_seconds() / 60
        
        if minutes_since_seen > self.long_absence_threshold_minutes:
            return UserState.LONG_ABSENT
        elif minutes_since_seen > self.absence_threshold_minutes:
            return UserState.ABSENT
        elif self.session_start and (now - self.session_start).total_seconds() < 60:
            return UserState.JUST_ARRIVED
        elif minutes_since_seen < self.absence_threshold_minutes and \
             self.last_greeting_time and \
             (now - self.last_greeting_time).total_seconds() > 60:
            # Was absent, now back
            return UserState.RETURNED
        else:
            return UserState.PRESENT
    
    def _should_greet(self) -> bool:
        """Check if enough time has passed to greet again."""
        if self.last_greeting_time is None:
            return True
        
        now = datetime.now()
        minutes_since_greeting = (now - self.last_greeting_time).total_seconds() / 60
        
        return minutes_since_greeting >= self.greeting_cooldown_minutes
    
    def get_context_summary(self) -> Dict[str, str]:
        """
        Get summary of current context.
        
        Returns:
            Dictionary with context information
        """
        return {
            'time_of_day': self.get_time_of_day().value,
            'user_state': self.get_user_state().value,
            'session_duration': self._get_session_duration(),
            'time_since_greeting': self._get_time_since_greeting()
        }
    
    def _get_session_duration(self) -> str:
        """Get formatted session duration."""
        if self.session_start is None:
            return "N/A"
        
        now = datetime.now()
        duration = now - self.session_start
        minutes = int(duration.total_seconds() / 60)
        
        if minutes < 1:
            return "< 1 min"
        elif minutes < 60:
            return f"{minutes} min"
        else:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"
    
    def _get_time_since_greeting(self) -> str:
        """Get formatted time since last greeting."""
        if self.last_greeting_time is None:
            return "Never"
        
        now = datetime.now()
        duration = now - self.last_greeting_time
        minutes = int(duration.total_seconds() / 60)
        
        if minutes < 1:
            return "Just now"
        elif minutes < 60:
            return f"{minutes} min ago"
        else:
            hours = minutes // 60
            return f"{hours}h ago"
    
    def reset_session(self) -> None:
        """Reset session tracking."""
        self.session_start = None
        self.last_seen_time = None
        self.last_greeting_time = None
