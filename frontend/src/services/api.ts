const API_BASE_URL = 'http://localhost:8000/api';

export interface EvaluateRequest {
  prompt: string;
  candidate_model?: string;
  judge_model?: string;
  reference_text?: string;
  system_prompt?: string;
  response_text?: string;
  run_async?: boolean;
  ecommerce_policy?: string;
  ecommerce_action?: string;
}

export interface HallucinationVerifyRequest {
  prompt: string;
  response?: string;
  candidate_model?: string;
}

export interface HallucinationClaim {
  claim: string;
  search_query: string;
  search_results: Array<{
    title: string;
    snippet: string;
    link: string;
  }>;
  status: 'SUPPORTED' | 'REFUTED' | 'UNVERIFIED';
  reasoning: string;
  citations: number[];
}

export interface HallucinationReport {
  groundedness_score: number;
  claims: HallucinationClaim[];
  latency_ms: number;
  summary: string;
  response: string;
}

export interface Metric {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
}

export interface ValidatorResult {
  score: number;
  status: string;
  raw_details: Record<string, any>;
}

export interface EvaluationDetail {
  evaluation_id: string;
  prompt: string;
  response: string | null;
  candidate_model: string;
  decision: 'APPROVE' | 'REJECT' | 'REGENERATE';
  created_at: string;
  verdict?: {
    prompt_risk: string;
    response_safety: string;
    attack_resistance: string;
  };
  judge: {
    relevance: number;
    correctness: number;
    completeness: number;
    clarity: number;
    safety: number;
    factual_consistency: number;
    instruction_adherence: number;
    attack_resistance?: number;
    overall_score: number;
    strengths: string[];
    weaknesses: string[];
    risks: string[];
    recommendations: string[];
    justification: string;
  };
  validators: Record<string, ValidatorResult>;
  incidents: Array<{
    incident_type: string;
    severity: string;
    description: string;
  }>;
  threat_type?: string;
  metrics?: {
    pipeline_latency_ms: number;
    generation_latency_ms: number;
    prompt_analysis_latency_ms: number;
    response_analysis_latency_ms: number;
    judge_analysis_latency_ms: number;
    candidate_cost: number;
    token_usage: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
}

export interface EvaluationListItem {
  id: string;
  prompt: string;
  response: string | null;
  decision: 'APPROVE' | 'REJECT' | 'REGENERATE';
  overall_score: number | null;
  created_at: string;
  prompt_risk?: string;
  model_name?: string;
  safety?: number;
  attack_resistance?: number;
}

export interface Incident {
  id: string;
  incident_type: string;
  severity: string;
  description: string;
  created_at: string;
}

export interface DashboardMetrics {
  approval_rate: number;
  rejection_rate: number;
  regeneration_rate: number;
  average_judge_score: number;
  total_evaluations: number;
  safety_incident_count: number;
  latency_metrics: {
    api_latency_ms: number;
    llm_latency_ms: number;
  };
  cost_metrics: {
    candidate_cost: number;
    total_accumulated_cost: number;
  };
  // Attack Resistance
  attack_resistance_rate: number;
  total_attacks: number;
  attacks_resisted: number;
  // Threat Breakdown
  threat_breakdown: Record<string, number>;
  // Hallucination Analytics
  hallucination_metrics: {
    incident_count: number;
    average_risk: number;
  };
  // Model Comparison
  model_comparison: Array<{
    model: string;
    safety: number;
    attack_resistance: number;
    quality: number;
    evaluations: number;
  }>;
  // Score Breakdown
  score_breakdown: {
    avg_quality: number;
    avg_safety: number;
    avg_attack_resistance: number;
  };
  // Latency Breakdown
  latency_breakdown: {
    model_generation: number;
    prompt_analysis: number;
    response_analysis: number;
    judge_analysis: number;
  };
}

export interface Policy {
  id: string;
  name: string;
  threshold_value: number;
  is_enabled: boolean;
  description: string | null;
  created_at: string;
}

export interface WebhookConfig {
  webhook_url: string | null;
}

class ApiService {
  private getToken(): string | null {
    return localStorage.getItem('token');
  }

  setToken(token: string) {
    localStorage.setItem('token', token);
  }

  clearToken() {
    localStorage.removeItem('token');
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  private async fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    const response = await fetch(url, options);
    if (response.status === 401) {
      this.clearToken();
      window.location.reload();
    }
    return response;
  }

  private getHeaders(isJson = true): HeadersInit {
    const headers: Record<string, string> = {};
    if (isJson) {
      headers['Content-Type'] = 'application/json';
    }
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  async register(username: string, password: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Registration failed');
    }
    return response.json();
  }

  async login(username: string, password: string): Promise<string> {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Login failed');
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data.access_token;
  }

  async getMe(): Promise<any> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/auth/me`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch user profile');
    }
    return response.json();
  }


  async evaluate(req: EvaluateRequest): Promise<any> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/evaluate`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(req),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Evaluation failed');
    }
    return response.json();
  }

  async getEvaluations(skip = 0, limit = 50, decision?: string): Promise<EvaluationListItem[]> {
    let url = `${API_BASE_URL}/evaluations?skip=${skip}&limit=${limit}`;
    if (decision) {
      url += `&decision=${decision}`;
    }

    const response = await this.fetchWithAuth(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch evaluations');
    }
    return response.json();
  }

  async getEvaluationDetail(id: string): Promise<EvaluationDetail> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/evaluation/${id}`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch evaluation details');
    }
    return response.json();
  }

  async getIncidents(skip = 0, limit = 50, severity?: string): Promise<Incident[]> {
    let url = `${API_BASE_URL}/incidents?skip=${skip}&limit=${limit}`;
    if (severity) {
      url += `&severity=${severity}`;
    }

    const response = await this.fetchWithAuth(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch incidents');
    }
    return response.json();
  }

  async getMetrics(): Promise<DashboardMetrics> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/metrics`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch metrics');
    }
    return response.json();
  }

  async getPolicies(): Promise<Policy[]> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/policies`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch guardrail policies');
    }
    return response.json();
  }

  async updatePolicy(id: string, threshold_value: number, is_enabled: boolean): Promise<Policy> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/policy/${id}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify({ threshold_value, is_enabled }),
    });
    if (!response.ok) {
      throw new Error('Failed to update guardrail policy');
    }
    return response.json();
  }

  async getWebhook(): Promise<WebhookConfig> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/settings/webhook`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch webhook configuration');
    }
    return response.json();
  }

  async updateWebhook(webhook_url: string | null): Promise<WebhookConfig> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/settings/webhook`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ webhook_url }),
    });
    if (!response.ok) {
      throw new Error('Failed to update webhook configuration');
    }
    return response.json();
  }

  async evaluateStream(
    req: EvaluateRequest,
    onEvent: (event: string, data: any) => void
  ): Promise<any> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/evaluate/stream`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(req),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Evaluation stream failed' }));
      throw new Error(err.detail || 'Evaluation stream failed');
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Readable stream not supported');
    }

    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('event:')) {
          currentEvent = trimmed.slice(6).trim();
        } else if (trimmed.startsWith('data:')) {
          const rawData = trimmed.slice(5).trim();
          try {
            const data = JSON.parse(rawData);
            onEvent(currentEvent, data);
          } catch (e) {
            console.error('Failed to parse stream data:', e, rawData);
          }
          currentEvent = '';
        }
      }
    }
  }

  async testWebhook(): Promise<any> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/settings/webhook/test`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Failed to test webhook' }));
      throw new Error(err.detail || 'Failed to test webhook');
    }
    return response.json();
  }

  async getStressTestMatrix(): Promise<any> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/evaluate/stress_test`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to execute adversarial stress test matrix');
    }
    return response.json();
  }

  async runBenchmark(category: string, targetModel: string, promptCount = 3): Promise<any> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/benchmark/run`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ category, target_model: targetModel, prompt_count: promptCount }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Benchmark execution failed' }));
      throw new Error(err.detail || 'Benchmark execution failed');
    }
    return response.json();
  }

  async getBenchmarks(): Promise<any[]> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/benchmarks`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch benchmark runs');
    }
    return response.json();
  }

  async getBenchmarkDetail(id: string): Promise<any> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/benchmark/${id}`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch benchmark run details');
    }
    return response.json();
  }

  async verifyHallucination(req: HallucinationVerifyRequest): Promise<HallucinationReport> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/hallucination/verify`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(req),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Hallucination verification failed' }));
      throw new Error(err.detail || 'Hallucination verification failed');
    }
    return response.json();
  }
}

export const api = new ApiService();
