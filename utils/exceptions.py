"""
MEMO Exception Hierarchy
Custom exceptions for better error handling and user feedback.
"""


class MEMOException(Exception):
    """Base exception for all MEMO errors."""
    
    def __init__(self, message: str, recoverable: bool = False):
        """
        Initialize MEMO exception.
        
        Args:
            message: Error description
            recoverable: Whether the system can continue operating
        """
        self.message = message
        self.recoverable = recoverable
        super().__init__(self.message)


class CameraError(MEMOException):
    """Camera initialization or capture errors."""
    
    def __init__(self, message: str, source: str = "unknown"):
        self.source = source
        super().__init__(f"Camera Error ({source}): {message}", recoverable=False)


class ModelError(MEMOException):
    """Model loading or inference errors."""
    
    def __init__(self, message: str, model_name: str = "unknown"):
        self.model_name = model_name
        super().__init__(f"Model Error ({model_name}): {message}", recoverable=True)


class HardwareError(MEMOException):
    """Hardware component errors (servos, LEDs, sensors)."""
    
    def __init__(self, message: str, device: str = "unknown"):
        self.device = device
        super().__init__(f"Hardware Error ({device}): {message}", recoverable=True)


class ConfigurationError(MEMOException):
    """Configuration file or validation errors."""
    
    def __init__(self, message: str, config_key: str = None):
        self.config_key = config_key
        if config_key:
            super().__init__(f"Configuration Error ({config_key}): {message}", recoverable=False)
        else:
            super().__init__(f"Configuration Error: {message}", recoverable=False)


class VoiceInputError(MEMOException):
    """Voice/audio input errors."""
    
    def __init__(self, message: str):
        super().__init__(f"Voice Input Error: {message}", recoverable=True)


class DashboardError(MEMOException):
    """Web dashboard errors."""
    
    def __init__(self, message: str):
        super().__init__(f"Dashboard Error: {message}", recoverable=True)
