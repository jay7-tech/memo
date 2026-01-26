"""
MEMO Configuration Management
Centralized configuration with validation and environment variable support.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class CameraConfig:
    """Camera configuration."""
    source: int = 0  # 0 for default webcam, or IP camera URL
    width: int = 640
    height: int = 480
    rotation: int = 0  # 0, 90, 180, 270
    fps_target: int = 15


@dataclass
class PerceptionConfig:
    """Perception model configuration."""
    yolo_model: str = "yolov8n.pt"
    pose_model: str = "yolov8n-pose.pt"
    face_threshold: float = 0.6
    object_confidence: float = 0.5
    phone_confidence: float = 0.75  # Stricter for cell phone
    frame_skip: int = 3  # Process every Nth frame
    enable_emotion: bool = True
    enable_gestures: bool = True
    enable_motion: bool = True


@dataclass
class VoiceConfig:
    """Voice input/output configuration."""
    enable_voice_input: bool = True
    enable_wake_word: bool = True
    wake_words: list = field(default_factory=lambda: ["hey memo", "hello memo"])
    wake_word_threshold: float = 0.5
    tts_rate: int = 150  # Words per minute
    tts_volume: float = 1.0
    language: str = "en-US"


@dataclass
class DashboardConfig:
    """Web dashboard configuration."""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    enable_auth: bool = False
    password: Optional[str] = None


@dataclass
class HardwareConfig:
    """Hardware integration configuration."""
    enable_servos: bool = False
    enable_leds: bool = False
    enable_sensors: bool = False
    servo_i2c_address: int = 0x40
    led_pin: int = 18
    led_count: int = 16


@dataclass
class SystemConfig:
    """System behavior configuration."""
    focus_mode_default: bool = False
    greeting_enabled: bool = True
    personality_mode: str = "helpful"  # helpful, sarcastic, cute, strict
    attention_tracking: bool = True
    conversation_memory: bool = True
    logging_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_to_file: bool = True


@dataclass
class MEMOConfig:
    """Master MEMO configuration."""
    camera: CameraConfig = field(default_factory=CameraConfig)
    perception: PerceptionConfig = field(default_factory=PerceptionConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    
    @classmethod
    def from_file(cls, config_path: str = "config.json") -> 'MEMOConfig':
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            MEMOConfig instance
        """
        path = Path(config_path)
        if not path.exists():
            # Create default config
            config = cls()
            config.save(config_path)
            return config
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Parse nested configs
        config = cls(
            camera=CameraConfig(**data.get('camera', {})),
            perception=PerceptionConfig(**data.get('perception', {})),
            voice=VoiceConfig(**data.get('voice', {})),
            dashboard=DashboardConfig(**data.get('dashboard', {})),
            hardware=HardwareConfig(**data.get('hardware', {})),
            system=SystemConfig(**data.get('system', {}))
        )
        
        # Override with environment variables
        config._apply_env_overrides()
        
        return config
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Camera
        if os.getenv('MEMO_CAMERA_SOURCE'):
            try:
                self.camera.source = int(os.getenv('MEMO_CAMERA_SOURCE'))
            except ValueError:
                self.camera.source = os.getenv('MEMO_CAMERA_SOURCE')
        
        # Logging
        if os.getenv('MEMO_LOG_LEVEL'):
            self.system.logging_level = os.getenv('MEMO_LOG_LEVEL')
        
        # Dashboard
        if os.getenv('MEMO_DASHBOARD_PORT'):
            self.dashboard.port = int(os.getenv('MEMO_DASHBOARD_PORT'))
        
        # Hardware
        if os.getenv('MEMO_ENABLE_SERVOS'):
            self.hardware.enable_servos = os.getenv('MEMO_ENABLE_SERVOS').lower() == 'true'
    
    def save(self, config_path: str = "config.json") -> None:
        """
        Save configuration to JSON file.
        
        Args:
            config_path: Path to save configuration
        """
        data = {
            'camera': asdict(self.camera),
            'perception': asdict(self.perception),
            'voice': asdict(self.voice),
            'dashboard': asdict(self.dashboard),
            'hardware': asdict(self.hardware),
            'system': asdict(self.system)
        }
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def validate(self) -> list[str]:
        """
        Validate configuration values.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Camera validation
        if self.camera.rotation not in [0, 90, 180, 270]:
            errors.append(f"Invalid camera rotation: {self.camera.rotation}")
        
        if self.camera.width < 320 or self.camera.height < 240:
            errors.append("Camera resolution too low (min 320x240)")
        
        # Perception validation
        if self.perception.frame_skip < 1:
            errors.append("Frame skip must be >= 1")
        
        if not (0 <= self.perception.face_threshold <= 1):
            errors.append("Face threshold must be between 0 and 1")
        
        # Voice validation
        if not (0 <= self.voice.wake_word_threshold <= 1):
            errors.append("Wake word threshold must be between 0 and 1")
        
        # Dashboard validation
        if not (1024 <= self.dashboard.port <= 65535):
            errors.append("Dashboard port must be between 1024 and 65535")
        
        # System validation
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.system.logging_level not in valid_log_levels:
            errors.append(f"Invalid log level: {self.system.logging_level}")
        
        valid_personalities = ['helpful', 'sarcastic', 'cute', 'strict', 'casual']
        if self.system.personality_mode not in valid_personalities:
            errors.append(f"Invalid personality mode: {self.system.personality_mode}")
        
        return errors


# Global configuration instance
_config: Optional[MEMOConfig] = None


def get_config(config_path: str = "config.json") -> MEMOConfig:
    """
    Get the global configuration instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        MEMOConfig instance
    """
    global _config
    if _config is None:
        _config = MEMOConfig.from_file(config_path)
        
        # Validate
        errors = _config.validate()
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            print("Using default values for invalid settings.")
    
    return _config


def reload_config(config_path: str = "config.json") -> MEMOConfig:
    """
    Reload configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Updated MEMOConfig instance
    """
    global _config
    _config = MEMOConfig.from_file(config_path)
    return _config
