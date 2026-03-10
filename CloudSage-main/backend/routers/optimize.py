"""
CloudSage – /api/optimize router.
Returns top 5 recommendations sorted by estimated savings.
"""

from fastapi import APIRouter

from backend.models.schemas import OptimizeRequest, Recommendation
from backend.services.inefficiency import detect_inefficiencies
from backend.services.pricing import calculate_resource_cost, get_optimized_cost

router = APIRouter()


@router.post("/optimize", response_model=list[Recommendation])
async def optimize(request: OptimizeRequest):
    """Analyse resources and return top 5 optimisation recommendations sorted by savings."""

    raw_recommendations: list[dict] = []

    for res in request.resources:
        cost = calculate_resource_cost(res)
        optimized = get_optimized_cost(res)
        saving = cost - optimized
        issues = detect_inefficiencies(res)

        for issue in issues:
            # Build a recommendation from each inefficiency
            provider = res.provider.value.upper()
            rid = res.resource_id

            if issue.rule_id == "DEV_247":
                cli = f"# {provider}: Schedule auto-shutdown\naws ec2 stop-instances --instance-ids {rid}" if provider == "AWS" else f"az vm deallocate --name {rid} --resource-group rg-dev" if provider == "AZURE" else f"gcloud compute instances stop {rid} --zone {res.region}"
                tf = f'resource "aws_instance" "{rid}" {{\n  tags = {{\n    AutoStop = "true"\n    Schedule = "business-hours"\n  }}\n}}'
                raw_recommendations.append({
                    "title": f"Auto-shutdown {rid} (dev/staging 24/7)",
                    "description": issue.issue,
                    "estimated_saving": issue.estimated_saving,
                    "effort": "low",
                    "priority": 1,
                    "cli_command": cli,
                    "terraform_snippet": tf,
                })

            elif issue.rule_id == "LOW_CPU":
                cli = f"aws ec2 modify-instance-attribute --instance-id {rid} --instance-type '{{\"Value\": \"t3.small\"}}'"
                tf = f'resource "aws_instance" "{rid}" {{\n  instance_type = "t3.small"  # downsized\n}}'
                raw_recommendations.append({
                    "title": f"Right-size {rid} (CPU {res.cpu_utilization:.0f}%)",
                    "description": issue.issue,
                    "estimated_saving": issue.estimated_saving,
                    "effort": "medium",
                    "priority": 1,
                    "cli_command": cli,
                    "terraform_snippet": tf,
                })

            elif issue.rule_id == "LOW_MEM":
                raw_recommendations.append({
                    "title": f"Optimise memory for {rid} (Mem {res.memory_utilization:.0f}%)",
                    "description": issue.issue,
                    "estimated_saving": issue.estimated_saving,
                    "effort": "medium",
                    "priority": 2,
                    "cli_command": f"aws ec2 modify-instance-attribute --instance-id {rid} --instance-type '{{\"Value\": \"t3.medium\"}}'",
                    "terraform_snippet": f'resource "aws_instance" "{rid}" {{\n  instance_type = "t3.medium"  # memory-optimized\n}}',
                })

            elif issue.rule_id == "LARGE_HOT_STORAGE":
                raw_recommendations.append({
                    "title": f"Archive cold data for {rid} ({res.storage_gb:.0f} GB hot)",
                    "description": issue.issue,
                    "estimated_saving": issue.estimated_saving,
                    "effort": "low",
                    "priority": 2,
                    "cli_command": f"aws s3api put-bucket-lifecycle-configuration --bucket {rid}-data --lifecycle-configuration file://lifecycle.json",
                    "terraform_snippet": f'resource "aws_s3_bucket_lifecycle_configuration" "{rid}" {{\n  rule {{\n    id     = "archive"\n    status = "Enabled"\n    transition {{\n      days          = 30\n      storage_class = "GLACIER"\n    }}\n  }}\n}}',
                })

            elif issue.rule_id == "DEV_DB":
                raw_recommendations.append({
                    "title": f"Switch {rid} to serverless DB tier",
                    "description": issue.issue,
                    "estimated_saving": issue.estimated_saving,
                    "effort": "medium",
                    "priority": 1,
                    "cli_command": f"aws rds modify-db-instance --db-instance-identifier {rid} --db-instance-class db.t3.micro --apply-immediately",
                    "terraform_snippet": f'resource "aws_db_instance" "{rid}" {{\n  instance_class = "db.t3.micro"  # cost-optimised for dev\n  engine         = "postgres"\n}}',
                })

            elif issue.rule_id == "NO_RI":
                raw_recommendations.append({
                    "title": f"Purchase Reserved Instance for {rid}",
                    "description": issue.issue,
                    "estimated_saving": issue.estimated_saving,
                    "effort": "low",
                    "priority": 3,
                    "cli_command": f"aws ec2 purchase-reserved-instances-offering --reserved-instances-offering-id <offering-id> --instance-count 1",
                    "terraform_snippet": f"# Reserved Instances are purchased via the AWS console or CLI\n# Not directly managed by Terraform",
                })

            else:
                raw_recommendations.append({
                    "title": f"Optimise {rid}: {issue.rule_id}",
                    "description": issue.issue,
                    "estimated_saving": issue.estimated_saving,
                    "effort": "medium",
                    "priority": 3,
                    "cli_command": "",
                    "terraform_snippet": "",
                })

    # Sort by saving descending and take top 5
    raw_recommendations.sort(key=lambda r: r["estimated_saving"], reverse=True)
    top5 = raw_recommendations[:5]

    return [Recommendation(**r) for r in top5]
