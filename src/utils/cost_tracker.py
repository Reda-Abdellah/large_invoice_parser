# src/utils/cost_tracker.py
class CostTracker:
    def __init__(self):
        self.costs = {}
    
    def track_usage(self, task: str, provider: str, input_tokens: int, output_tokens: int, cost: float):
        if task not in self.costs:
            self.costs[task] = {}
        
        if provider not in self.costs[task]:
            self.costs[task][provider] = {
                "total_cost": 0,
                "total_tokens": 0,
                "call_count": 0
            }
        
        self.costs[task][provider]["total_cost"] += cost
        self.costs[task][provider]["total_tokens"] += input_tokens + output_tokens
        self.costs[task][provider]["call_count"] += 1
    
    def get_report(self) -> Dict[str, Any]:
        return {
            "total_cost": sum(
                sum(provider["total_cost"] for provider in task.values())
                for task in self.costs.values()
            ),
            "by_task": self.costs
        }
