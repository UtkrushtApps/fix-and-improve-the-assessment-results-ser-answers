"""Domain models for the Assessment Results Service."""
import datetime
from dataclasses import dataclass, field


@dataclass
class AssessmentResult:
    candidate_id: str
    skill_name: str
    score: int
    max_score: int
    status: str = "completed"
    submitted_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "skill_name": self.skill_name,
            "score": self.score,
            "max_score": self.max_score,
            "status": self.status,
            "submitted_at": self.submitted_at,
        }
