import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database.db import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    profile_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    responses = relationship("Response", back_populates="prompt", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="prompt", cascade="all, delete-orphan")


class Response(Base):
    __tablename__ = "responses"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_id = Column(String(36), ForeignKey("prompts.id"), nullable=False)
    content = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=False)
    latency_ms = Column(Float, default=0.0)
    token_usage = Column(JSON, nullable=True) # e.g. {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    prompt = relationship("Prompt", back_populates="responses")
    evaluations = relationship("Evaluation", back_populates="response", cascade="all, delete-orphan")


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String(100), nullable=False) # Reasoning, Coding, Safety, Hallucination, Instruction Following
    target_model = Column(String(100), nullable=False)
    prompt_count = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    evaluations = relationship("Evaluation", back_populates="benchmark_run", cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_id = Column(String(36), ForeignKey("prompts.id"), nullable=False)
    response_id = Column(String(36), ForeignKey("responses.id"), nullable=True) # Can be null if rejected at prompt level
    benchmark_run_id = Column(String(36), ForeignKey("benchmark_runs.id"), nullable=True)
    decision = Column(String(50), nullable=False) # APPROVE, REJECT, REGENERATE
    
    # Judge scores (1-10)
    relevance = Column(Float, nullable=True)
    correctness = Column(Float, nullable=True)
    completeness = Column(Float, nullable=True)
    clarity = Column(Float, nullable=True)
    safety = Column(Float, nullable=True)
    factual_consistency = Column(Float, nullable=True)
    instruction_adherence = Column(Float, nullable=True)
    attack_resistance = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    threat_type = Column(String(100), nullable=True) # e.g. Criminal Assistance, Violence, None
    candidate_model = Column(String(100), nullable=True)
    
    # Latency metrics (ms)
    pipeline_latency_ms = Column(Float, default=0.0, nullable=True)
    prompt_analysis_latency_ms = Column(Float, default=0.0, nullable=True)
    response_analysis_latency_ms = Column(Float, default=0.0, nullable=True)
    judge_analysis_latency_ms = Column(Float, default=0.0, nullable=True)
    
    # Explainability details
    strengths = Column(JSON, nullable=True) # list of strings
    weaknesses = Column(JSON, nullable=True) # list of strings
    risks = Column(JSON, nullable=True) # list of strings
    recommendations = Column(JSON, nullable=True) # list of strings
    justification = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    prompt = relationship("Prompt", back_populates="evaluations")
    response = relationship("Response", back_populates="evaluations")
    benchmark_run = relationship("BenchmarkRun", back_populates="evaluations")
    validator_results = relationship("ValidatorResult", back_populates="evaluation", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="evaluation", cascade="all, delete-orphan")


class ValidatorResult(Base):
    __tablename__ = "validator_results"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(36), ForeignKey("evaluations.id"), nullable=False)
    validator_name = Column(String(100), nullable=False) # e.g. prompt_injection, jailbreak, toxicity, etc.
    score = Column(Float, nullable=False)
    status = Column(String(50), nullable=False) # e.g. safe, risk, high, low, etc.
    raw_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    evaluation = relationship("Evaluation", back_populates="validator_results")


class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(36), ForeignKey("evaluations.id"), nullable=False)
    incident_type = Column(String(100), nullable=False) # e.g. prompt_injection, jailbreak, toxicity, policy_violation
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False) # e.g. low, medium, high, critical
    created_at = Column(DateTime, default=datetime.utcnow)
    
    evaluation = relationship("Evaluation", back_populates="incidents")


class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class GuardrailPolicy(Base):
    __tablename__ = "guardrail_policies"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True) # e.g. toxicity_threshold, jailbreak_threshold, etc.
    threshold_value = Column(Float, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(100), unique=True, nullable=False, index=True) # e.g. webhook_url
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)



