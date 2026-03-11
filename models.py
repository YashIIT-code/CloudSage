from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import Enum


class ResourceType(str, Enum):
    VM = "vm"
    STORAGE = "storage"
    DATABASE = "database"
    CONTAINER = "container"


class Provider(str, Enum):
    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"


class Environment(str, Enum):
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    STAGING = "staging"


class CloudResource(BaseModel):
    resource_name: str
    type: ResourceType
    provider: Provider
    size: Optional[str] = None
    storage_gb: Optional[float] = 0.0
    region: str = "us-east-1"
    hours_per_day: float = 24.0
    environment: Environment = Environment.PRODUCTION
    cpu_utilization: Optional[float] = None
    memory_utilization: Optional[float] = None
    monthly_cost: float = 0.0


class ResourceCost(BaseModel):
    resource_name: str
    type: str
    provider: str
    monthly_cost: float
    optimized_cost: float
    saving: float


class Inefficiency(BaseModel):
    resource_name: str
    issue: str
    severity: Literal["low", "medium", "high"]
    potential_saving: float


class Recommendation(BaseModel):
    title: str
    description: str
    estimated_saving: float
    effort: Literal["low", "medium", "high"]
    priority: int
    cli_command: Optional[str] = None
    terraform_snippet: Optional[str] = None


class AnalysisResponse(BaseModel):
    current_monthly_cost: float
    optimized_monthly_cost: float
    total_savings: float
    savings_percentage: float
    efficiency_score: int
    breakdown: List[ResourceCost]
    inefficiencies: List[Inefficiency]
    analysis: str
    recommendations: List[Recommendation]


class AnalyzeRequest(BaseModel):
    resources: List[CloudResource]
