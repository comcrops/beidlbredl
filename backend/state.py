from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KioskState:
    active_app_id: Optional[str] = None
    open_app_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'active_app_id': self.active_app_id,
            'open_app_ids': self.open_app_ids,
        }


kiosk_state = KioskState()
