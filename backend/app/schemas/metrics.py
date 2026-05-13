from pydantic import BaseModel


class MetricsSummary(BaseModel):
    total_reviews: int
    total_comments: int
    acceptance_rate: float
    avg_quality_score: float


class TrendPoint(BaseModel):
    date: str
    avg_quality: float
    count: int


class EngineerMetric(BaseModel):
    engineer: str
    total_reviews: int
    avg_quality_score: float
    recent_30d_quality: float
    previous_30d_quality: float
    quality_delta: float
    acceptance_rate: float


class FeedbackLearningSignal(BaseModel):
    category: str
    accepted: int
    rejected: int
    acceptance_rate: float
