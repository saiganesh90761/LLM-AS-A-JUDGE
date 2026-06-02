from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

# User Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: str
    username: str
    created_at: datetime
    profile_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

# Evaluation Request Schemas
class EvaluateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    candidate_model: Optional[str] = None
    judge_model: Optional[str] = None
    reference_text: Optional[str] = None
    system_prompt: Optional[str] = None
    response_text: Optional[str] = None # Added for user pasted response evaluation
    run_async: Optional[bool] = False
    ecommerce_policy: Optional[str] = None
    ecommerce_action: Optional[str] = None

# Evaluation Response Schemas
class ValidatorResultSchema(BaseModel):
    score: float
    status: str
    raw_details: Dict[str, Any]

class EvaluationListItem(BaseModel):
    id: str
    prompt: str
    response: Optional[str] = None
    decision: str
    overall_score: Optional[float] = None
    created_at: datetime
    prompt_risk: Optional[str] = "LOW"
    model_name: Optional[str] = "unknown"
    safety: Optional[float] = None
    attack_resistance: Optional[float] = None
    justification: Optional[str] = None

    class Config:
        from_attributes = True

class IncidentSchema(BaseModel):
    id: str
    incident_type: str
    severity: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True

# Metrics Schema
class MetricsResponse(BaseModel):
    approval_rate: float
    rejection_rate: float
    regeneration_rate: float
    average_judge_score: float
    total_evaluations: int
    safety_incident_count: int
    latency_metrics: Dict[str, float]
    cost_metrics: Dict[str, float]
    # Attack Resistance
    attack_resistance_rate: float = 0.0
    total_attacks: int = 0
    attacks_resisted: int = 0
    # Threat Breakdown
    threat_breakdown: Dict[str, int] = {}
    # Hallucination Analytics
    hallucination_metrics: Dict[str, float] = {}
    # Model Comparison
    model_comparison: List[Dict[str, Any]] = []
    # Score Breakdown
    score_breakdown: Dict[str, float] = {}
    # Latency Breakdown
    latency_breakdown: Dict[str, float] = {}


# Policy Schemas
class PolicyResponse(BaseModel):
    id: str
    name: str
    threshold_value: float
    is_enabled: bool
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PolicyUpdate(BaseModel):
    threshold_value: float
    is_enabled: bool

# Webhook Setting Schemas
class WebhookSetting(BaseModel):
    webhook_url: Optional[str] = None

# Benchmark Schemas
class BenchmarkRequest(BaseModel):
    category: str
    target_model: str
    prompt_count: Optional[int] = 3

class BenchmarkRunSchema(BaseModel):
    id: str
    category: str
    target_model: str
    prompt_count: float
    created_at: datetime

    class Config:
        from_attributes = True

class BenchmarkDetailResponse(BaseModel):
    id: str
    category: str
    target_model: str
    prompt_count: float
    created_at: datetime
    evaluations: List[EvaluationListItem]

    class Config:
        from_attributes = True


class HallucinationVerifyRequest(BaseModel):
    prompt: str
    response: Optional[str] = None
    candidate_model: Optional[str] = None

