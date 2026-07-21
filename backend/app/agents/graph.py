from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.nodes import PlannedOutageAgentNodes
from app.agents.state import PlannedOutageState
from app.utils.time import ist_now


class PlannedOutageAgentGraph:
    """LangGraph workflow for Phase 1 planned outage communication."""

    def __init__(self, db: Session) -> None:
        self.nodes = PlannedOutageAgentNodes(db)
        self.graph = self.build_graph()

    def build_graph(self):
        builder = StateGraph(PlannedOutageState)
        builder.add_node("validate_outage", self.nodes.validate_outage)
        builder.add_node("identify_customers", self.nodes.identify_customers)
        builder.add_node("dispatch_notifications", self.nodes.dispatch_notifications)

        builder.add_edge(START, "validate_outage")
        builder.add_edge("validate_outage", "identify_customers")
        builder.add_edge("identify_customers", "dispatch_notifications")
        builder.add_edge("dispatch_notifications", END)
        return builder.compile()

    def run(self, outage_id: str, notification_type: str) -> dict[str, object]:
        state: PlannedOutageState = {"outage_id": outage_id, "notification_type": notification_type}
        result = self.graph.invoke(state)
        return {
            "outage_id": outage_id,
            "notification_type": notification_type,
            "affected_customers": int(result.get("affected_count", 0)),
            "notifications_created": int(result.get("notifications_created", 0)),
            "notifications_delivered": int(result.get("notifications_delivered", 0)),
            "notifications_failed": int(result.get("notifications_failed", 0)),
            "medical_baseline_customers": int(result.get("medical_baseline_customers", 0)),
            "processed_at": ist_now().isoformat(),
        }
