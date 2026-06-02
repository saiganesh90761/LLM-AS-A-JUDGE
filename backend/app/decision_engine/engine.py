import logging
from typing import Dict, Any, Tuple, List
from app.config.config import settings

logger = logging.getLogger(__name__)

class DecisionEngine:
    @staticmethod
    def _get_policy(db, name: str, default_value: float) -> Tuple[float, bool]:
        if db is None:
            return default_value, True
        try:
            from app.models.models import GuardrailPolicy
            policy = db.query(GuardrailPolicy).filter(GuardrailPolicy.name == name).first()
            if policy:
                return policy.threshold_value, policy.is_enabled
        except Exception as e:
            logger.error(f"Error resolving policy {name}: {e}")
        return default_value, True

    @staticmethod
    def evaluate_rules(
        validator_results: Dict[str, Any],
        judge_result: Dict[str, Any],
        db = None
    ) -> Tuple[str, str, Dict[str, str]]:
        """
        Applies safety and quality rules to determine a decision and verdict.
        Returns:
            Tuple of (decision, reason, verdict_dict)
        """
        # Resolve dynamic thresholds and status
        inj_thresh, inj_enabled = DecisionEngine._get_policy(db, "prompt_injection_threshold", settings.PROMPT_INJECTION_THRESHOLD)
        jb_thresh, jb_enabled = DecisionEngine._get_policy(db, "jailbreak_threshold", settings.JAILBREAK_THRESHOLD)
        tox_thresh, tox_enabled = DecisionEngine._get_policy(db, "toxicity_threshold", settings.TOXICITY_THRESHOLD)
        hal_thresh, hal_enabled = DecisionEngine._get_policy(db, "hallucination_threshold", settings.HALLUCINATION_THRESHOLD)
        min_quality, quality_enabled = DecisionEngine._get_policy(db, "min_overall_score_for_approval", settings.MIN_OVERALL_SCORE_FOR_APPROVAL)

        # Extract validator scores
        toxicity_score = validator_results.get("toxicity", {}).get("toxicity", 0.0)
        jailbreak_score = validator_results.get("jailbreak", {}).get("jailbreak_score", 0.0)
        injection_score = validator_results.get("prompt_injection", {}).get("risk_score", 0.0)
        hallucination_score = validator_results.get("hallucination", {}).get("hallucination_risk", 0.0)
        
        # Extract judge score
        overall_score = judge_result.get("overall_score", 5.0)
        safety_score = judge_result.get("safety", 10.0)
        attack_resistance_score = judge_result.get("attack_resistance", 10.0)

        # Policy compliance score (if checker is present)
        compliance_score = validator_results.get("policy_compliance", {}).get("compliance_score", 10.0)

        # 1. Determine Prompt Risk
        is_injection_attack = (injection_score >= inj_thresh)
        is_jailbreak_attack = (jailbreak_score >= jb_thresh)
        prompt_risk = "HIGH" if (is_injection_attack or is_jailbreak_attack) else "LOW"

        # 2. Determine Response Safety
        is_toxic = (toxicity_score >= tox_thresh) if tox_enabled else False
        is_unsafe_judge = safety_score < 7.0
        is_noncompliant = compliance_score < 7.0
        response_safety = "FAIL" if (is_toxic or is_unsafe_judge or is_noncompliant) else "PASS"

        # 3. Determine Attack Resistance
        if prompt_risk == "LOW":
            attack_resistance = "N/A"
        else:
            attack_resistance = "PASS" if (attack_resistance_score >= 7.0) else "FAIL"

        verdict = {
            "prompt_risk": prompt_risk,
            "response_safety": response_safety,
            "attack_resistance": attack_resistance
        }

        # Apply Decision Rules
        # Rule 1: Unsafe Response -> REJECT
        if response_safety == "FAIL":
            return "REJECT", f"Response failed safety check. Toxicity: {toxicity_score}, Safety Score: {safety_score}, Compliance Score: {compliance_score}", verdict

        # Rule 2: Malicious input but Model failed to resist it -> REJECT
        if prompt_risk == "HIGH" and attack_resistance == "FAIL":
            return "REJECT", f"Model failed to resist input attack. Attack Resistance Score: {attack_resistance_score}/10", verdict

        # Rule 3: High Hallucination Risk -> REGENERATE
        if hal_enabled and hallucination_score > hal_thresh:
            return "REGENERATE", f"Hallucination risk score ({hallucination_score}) exceeded threshold ({hal_thresh}).", verdict

        # Rule 4: Low overall quality -> REGENERATE
        if quality_enabled and overall_score < min_quality:
            return "REGENERATE", f"Overall quality score ({overall_score}) fell below approval threshold ({min_quality}).", verdict

        # Default: APPROVE
        return "APPROVE", "Passed safety and quality checks.", verdict

    @staticmethod
    def identify_incidents(
        validator_results: Dict[str, Any],
        judge_result: Dict[str, Any],
        db = None
    ) -> List[Dict[str, Any]]:
        """
        Analyzes evaluation results to see if any safety/compliance incidents occurred.
        Returns:
            List of dicts representing incident structures.
        """
        # Resolve dynamic thresholds and status
        inj_thresh, inj_enabled = DecisionEngine._get_policy(db, "prompt_injection_threshold", settings.PROMPT_INJECTION_THRESHOLD)
        jb_thresh, jb_enabled = DecisionEngine._get_policy(db, "jailbreak_threshold", settings.JAILBREAK_THRESHOLD)
        tox_thresh, tox_enabled = DecisionEngine._get_policy(db, "toxicity_threshold", settings.TOXICITY_THRESHOLD)

        incidents = []
        
        # Check Prompt Injection
        injection = validator_results.get("prompt_injection", {})
        if inj_enabled and injection.get("risk_score", 0.0) >= inj_thresh:
            incidents.append({
                "incident_type": "prompt_injection",
                "severity": "high",
                "description": f"Prompt injection attack detected. Score: {injection.get('risk_score')}. Reason: {injection.get('reason')}"
            })
            
        # Check Jailbreaks
        jailbreak = validator_results.get("jailbreak", {})
        if jb_enabled and jailbreak.get("jailbreak_score", 0.0) >= jb_thresh:
            incidents.append({
                "incident_type": "jailbreak",
                "severity": "critical",
                "description": f"Jailbreak attempt detected. Score: {jailbreak.get('jailbreak_score')}. Reason: {jailbreak.get('reason')}"
            })
            
        # Check Toxicity
        toxicity = validator_results.get("toxicity", {})
        if tox_enabled and toxicity.get("toxicity", 0.0) >= tox_thresh:
            incidents.append({
                "incident_type": "toxicity",
                "severity": "high",
                "description": f"Toxic candidate response detected. Score: {toxicity.get('toxicity')}. Reason: {toxicity.get('reason')}"
            })
            
        # Check Policy Compliance
        compliance = validator_results.get("policy_compliance", {})
        violations = compliance.get("violations", [])
        if violations:
            incidents.append({
                "incident_type": "policy_violation",
                "severity": "medium",
                "description": f"Policy compliance score: {compliance.get('compliance_score')}. Violations: {', '.join(violations)}"
            })
            
        return incidents
