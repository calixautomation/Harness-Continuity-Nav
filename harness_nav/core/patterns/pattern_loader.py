"""Pattern loader for JSON-based pattern definitions."""

import json
from pathlib import Path
from typing import List, Optional
import logging

from .models import Pattern

logger = logging.getLogger(__name__)


class PatternLoader:
    """
    Loads LED patterns from JSON file.

    JSON Format:
    {
        "patterns": [
            {
                "id": "pattern_1",
                "name": "Pattern 1",
                "description": "LEDs 3, 4, 8",
                "leds": [3, 4, 8]
            }
        ]
    }
    """

    def __init__(self, patterns_file: str = "./data/patterns.json"):
        """Initialize pattern loader with JSON file path."""
        self._patterns_file = Path(patterns_file)
        self._patterns: List[Pattern] = []
        self._loaded = False

    def load(self) -> List[Pattern]:
        """
        Load all patterns from JSON file.

        Returns:
            List of Pattern objects

        Raises:
            FileNotFoundError: If patterns file doesn't exist
            ValueError: If JSON format is invalid
        """
        if not self._patterns_file.exists():
            raise FileNotFoundError(f"Patterns file not found: {self._patterns_file}")

        with open(self._patterns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'patterns' not in data:
            raise ValueError("Invalid patterns file: missing 'patterns' key")

        self._patterns = []
        for p_data in data['patterns']:
            try:
                pattern = Pattern(
                    id=p_data['id'],
                    name=p_data['name'],
                    description=p_data.get('description', ''),
                    leds=p_data['leds']
                )
                self._patterns.append(pattern)
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid pattern: {e}")
                continue

        self._loaded = True
        logger.info(f"Loaded {len(self._patterns)} patterns from {self._patterns_file}")
        return self._patterns

    def get_patterns(self) -> List[Pattern]:
        """Get all loaded patterns."""
        if not self._loaded:
            self.load()
        return self._patterns

    def get_pattern_by_id(self, pattern_id: str) -> Optional[Pattern]:
        """Get a pattern by its ID."""
        if not self._loaded:
            self.load()
        for pattern in self._patterns:
            if pattern.id == pattern_id:
                return pattern
        return None

    def get_pattern_names(self) -> List[tuple]:
        """Get list of (id, name, description) for all patterns."""
        if not self._loaded:
            self.load()
        return [(p.id, p.name, p.description) for p in self._patterns]

    def reload(self) -> List[Pattern]:
        """Force reload patterns from file."""
        self._loaded = False
        return self.load()

    @staticmethod
    def create_sample_file(output_path: str) -> None:
        """Create a sample patterns JSON file."""
        sample_data = {
            "patterns": [
                {
                    "id": "pattern_1",
                    "name": "Pattern 1",
                    "description": "LEDs 3, 4, 8",
                    "leds": [3, 4, 8]
                },
                {
                    "id": "pattern_2",
                    "name": "Pattern 2",
                    "description": "LEDs 1, 2, 5, 6",
                    "leds": [1, 2, 5, 6]
                },
                {
                    "id": "corners",
                    "name": "Corners",
                    "description": "Corner LEDs only",
                    "leds": [1, 8, 57, 64]
                }
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=4)

        logger.info(f"Created sample patterns file: {output_path}")
