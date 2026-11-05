import json

import httpx2


def fake_warehouse_agent(request: httpx2.Request) -> httpx2.Response:
    """Small stand in for the Warehouse Agent: same response shape, no LLM."""
    body = json.loads(request.content)
    message = body.get("message", "")
    session_id = body.get("sessionId") or "sess-001"
    if "ORD-2001" in message:
        return httpx2.Response(
            200,
            json={
                "sessionId": session_id,
                "answer": "Human approval is required before shipment release.",
                "status": "awaiting_approval",
                "toolCalls": [{"name": "get_order"}, {"name": "submit_for_human_approval"}],
                "approval": {"id": "APR-001", "status": "pending"},
                "requestId": "REQ-001",
            },
        )
    return httpx2.Response(
        200,
        json={
            "sessionId": session_id,
            "answer": "Manual review required: Missing required field: orderNumber",
            "status": "manual_review",
            "toolCalls": [],
            "approval": None,
            "requestId": None,
        },
    )


VALID_DOCUMENT = "Invoice No: INV-1001\nOrder No: ORD-2001\nQuantity: 10"
INVALID_DOCUMENT = "Invoice No: INV-1001\nQuantity: 10"
