"""
Trigger Lambda — invoked by EventBridge Scheduler to start the Bedrock Flow.

EventBridge Scheduler → this Lambda → bedrock-agent-runtime.invoke_flow()
"""

import json
import os
import time
from typing import Any

import boto3
from botocore.config import Config

FLOW_ID = os.environ["FLOW_ID"]
FLOW_ALIAS_ID = os.environ["FLOW_ALIAS_ID"]

bedrock_runtime = boto3.client(
    "bedrock-agent-runtime",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    config=Config(
        read_timeout=840,        # 14 min — just under the Lambda timeout
        connect_timeout=10,
        retries={"max_attempts": 0},
    ),
)


def handler(event: dict, context: Any) -> dict:
    execution_id = f"run-{int(time.time())}"
    print(f"[trigger] Starting flow {FLOW_ID}/{FLOW_ALIAS_ID}, execution={execution_id}")

    response = bedrock_runtime.invoke_flow(
        flowIdentifier=FLOW_ID,
        flowAliasIdentifier=FLOW_ALIAS_ID,
        inputs=[
            {
                "content": {"document": {"executionId": execution_id}},
                "nodeName": "FlowInputNode",
                "nodeOutputName": "document",
            }
        ],
    )

    # Stream the response events
    output_chunks = []
    event_stream = response.get("responseStream", [])

    for flow_event in event_stream:
        if "flowOutputEvent" in flow_event:
            content = flow_event["flowOutputEvent"].get("content", {})
            doc = content.get("document")
            if doc is not None:
                output_chunks.append(doc)
                print(f"[trigger] Flow output: {json.dumps(doc)[:500]}")

        elif "flowCompletionEvent" in flow_event:
            status = flow_event["flowCompletionEvent"].get("completionReason", "UNKNOWN")
            print(f"[trigger] Flow completed. Status: {status}")

        elif "flowTraceEvent" in flow_event:
            trace = flow_event["flowTraceEvent"].get("trace", {})
            if "nodeInputTrace" in trace:
                node = trace["nodeInputTrace"].get("nodeName", "?")
                print(f"[trace] → {node} starting")
            elif "nodeOutputTrace" in trace:
                node = trace["nodeOutputTrace"].get("nodeName", "?")
                print(f"[trace] ✓ {node} complete")

        elif "internalServerException" in flow_event:
            raise RuntimeError(f"Flow internal error: {flow_event['internalServerException']}")

        elif "validationException" in flow_event:
            raise ValueError(f"Flow validation error: {flow_event['validationException']}")

        elif "serviceQuotaExceededException" in flow_event:
            raise RuntimeError(f"Flow quota exceeded: {flow_event['serviceQuotaExceededException']}")

    print(f"[trigger] Done. {len(output_chunks)} output chunk(s)")
    return {
        "statusCode": 200,
        "flowId": FLOW_ID,
        "flowAliasId": FLOW_ALIAS_ID,
        "executionId": execution_id,
        "outputCount": len(output_chunks),
    }
