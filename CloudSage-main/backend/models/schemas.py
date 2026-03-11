"""
CloudSage – Pydantic v2 schemas for cloud resource analysis.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ─── Enums ──────────────────────────────────────────────────────────────────────

class ResourceType(str, Enum):
    vm = "vm"
    storage = "storage"
    database = "database"
    container = "container"


class Provider(str, Enum):
    aws = "aws"
    azure = "azure"
    gcp = "gcp"


class Environment(str, Enum):
    production = "production"
    development = "development"
    staging = "staging"


# ─── Core Models ────────────────────────────────────────────────────────────────

class CloudResource(BaseModel):
    resource_name: str = Field(..., description="Unique identifier for the resource")
    type: ResourceType = Field(default=ResourceType.vm, description="Type of cloud resource")
    provider: Provider = Field(default=Provider.aws, description="Cloud provider")
    region: str = Field(default="us-east-1", description="Deployment region")
    size: str = Field(default="t3.medium", description="Instance type / SKU")
    environment: Environment = Field(default=Environment.production, description="Deployment environment")
    cpu_utilization: Optional[float] = Field(default=None, ge=0, le=100, description="Average CPU utilization %")
    memory_utilization: Optional[float] = Field(default=None, ge=0, le=100, description="Average memory utilization %")
    storage_gb: float = Field(default=0.0, ge=0, description="Attached storage in GB")
    monthly_cost: float = Field(default=0.0, ge=0, description="Current monthly cost in USD")
    hours_per_day: float = Field(default=24.0, ge=0, description="Hours running per day")
    tags: str = Field(default="", description="Comma-separated tags")


class Inefficiency(BaseModel):
    rule_id: str = Field(..., description="Unique rule identifier")
    issue: str = Field(..., description="Description of the inefficiency")
    severity: str = Field(..., description="High, Medium, or Low")
    estimated_saving: float = Field(default=0.0, ge=0, description="Estimated monthly saving in USD")
    resource_id: str = Field(default="", description="Associated resource ID")


class Recommendation(BaseModel):
    title: str = Field(..., description="Recommendation title")
    description: str = Field(default="", description="Detailed description")
    estimated_saving: float = Field(default=0.0, ge=0, description="Estimated monthly saving in USD")
    effort: str = Field(default="medium", description="Implementation effort: low, medium, high")
    priority: int = Field(default=3, ge=1, le=5, description="Priority 1 (highest) to 5 (lowest)")
    cli_command: str = Field(default="", description="AWS/Azure/GCP CLI command")
    terraform_snippet: str = Field(default="", description="Terraform HCL code snippet")


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    resources: list[CloudResource] = Field(default_factory=list)
    inefficiencies: list[Inefficiency] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    efficiency_score: int = Field(default=100, ge=0, le=100, description="0–100 efficiency score")
    current_monthly_cost: float = Field(default=0.0, ge=0, alias="currentMonthlyCost")
    optimized_monthly_cost: float = Field(default=0.0, ge=0, alias="optimizedMonthlyCost")
    total_savings: float = Field(default=0.0, ge=0, alias="totalSavings")
    savings_percentage: float = Field(default=0.0, ge=0, alias="savingsPercentage")
    executive_summary: str = Field(default="", description="AI-generated executive summary")


# ─── Request / Response helpers ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: str = ""
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str


class AnalyzeRequest(BaseModel):
    resources: list[CloudResource]


class OptimizeRequest(BaseModel):
    resources: list[CloudResource]
