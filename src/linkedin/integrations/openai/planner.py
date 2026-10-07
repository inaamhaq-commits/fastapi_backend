from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from linkedin.integrations.openai.client import get_openai_client


@dataclass(slots=True)
class PlannedActorTask:
    normalized_query: str
    actor_key: str
    actor_input: dict[str, Any]


GLASSDOOR_PLANNER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "normalized_query": {"type": "string"},
        "actor_key": {
            "type": "string",
            "enum": ["glassdoor_jobs"],
        },
        "actor_input": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "keywords": {"type": "string"},
                "location": {"type": "string"},
                "daysOld": {"type": "integer"},
                "easyApply": {"type": "boolean"},
                "remoteWorkType": {"type": "boolean"},
                "minRating": {"type": "number"},
                "radius": {"type": "string"},
                "employerSizes": {"type": "string"},
                "sortBy": {
                    "type": "string",
                    "enum": ["relevant_desc", "date_desc"],
                },
                "limit": {"type": "integer"},
                "urlParam": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "key": {"type": "string"},
                            "value": {"type": "string"},
                        },
                        "required": ["key", "value"],
                    },
                },
                "excludeJobIds": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "keywords",
                "location",
                "daysOld",
                "easyApply",
                "remoteWorkType",
                "minRating",
                "radius",
                "employerSizes",
                "sortBy",
                "limit",
                "urlParam",
                "excludeJobIds",
            ],
        },
    },
    "required": ["normalized_query", "actor_key", "actor_input"],
}


def _normalize_glassdoor_actor_input(actor_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "keywords": str(actor_input.get("keywords", "")).strip(),
        "location": str(actor_input.get("location", "")).strip(),
        "daysOld": int(actor_input.get("daysOld", 30)),
        "easyApply": bool(actor_input.get("easyApply", False)),
        "remoteWorkType": bool(actor_input.get("remoteWorkType", False)),
        "minRating": float(actor_input.get("minRating", 0)),
        "radius": str(actor_input.get("radius", "25")),
        "employerSizes": str(actor_input.get("employerSizes", "")),
        "sortBy": str(actor_input.get("sortBy", "relevant_desc")),
        "limit": int(actor_input.get("limit", 100)),
        "urlParam": list(actor_input.get("urlParam", [])),
        "excludeJobIds": [str(item) for item in actor_input.get("excludeJobIds", [])],
    }


def generate_glassdoor_actor_task(user_message: str) -> PlannedActorTask:
    client = get_openai_client()

    response = client.responses.create(
        model="gpt-5.6-terra",
        reasoning={"effort": "low"},
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are a planner that converts a user's job-search message "
                            "into valid Apify Glassdoor actor input. "
                            "Return only fields supported by the provided schema. "
                            "Use actor_key glassdoor_jobs. "
                            "Use safe defaults when the user message is missing values: "
                            "daysOld=30, easyApply=false, remoteWorkType=false, "
                            "minRating=0, radius='25', employerSizes='', "
                            "sortBy='relevant_desc', limit=100, urlParam=[], "
                            "excludeJobIds=[]. "
                            "Prefer clear, normalized job-title keywords. "
                            "If the user requests remote jobs, preserve that intent."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_message}],
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "glassdoor_actor_task",
                "schema": GLASSDOOR_PLANNER_SCHEMA,
                "strict": True,
            }
        },
    )

    payload = json.loads(response.output_text)
    normalized_query = str(payload["normalized_query"]).strip()
    actor_key = str(payload["actor_key"]).strip()
    actor_input = _normalize_glassdoor_actor_input(payload["actor_input"])

    if not actor_input["keywords"]:
        actor_input["keywords"] = normalized_query or user_message.strip()
    if not normalized_query:
        normalized_query = actor_input["keywords"]

    return PlannedActorTask(
        normalized_query=normalized_query,
        actor_key=actor_key,
        actor_input=actor_input,
    )


def _is_remote_glassdoor_search(planned_task: PlannedActorTask) -> bool:
    location = str(planned_task.actor_input.get("location", "")).strip().lower()
    normalized_query = planned_task.normalized_query.lower()
    return bool(
        planned_task.actor_input.get("remoteWorkType")
        or location == "remote"
        or "remote" in normalized_query
    )


def _derive_query_text(planned_glassdoor_task: PlannedActorTask) -> str:
    return planned_glassdoor_task.normalized_query or str(
        planned_glassdoor_task.actor_input.get("keywords", "")
    ).strip()


def _derive_location_text(planned_glassdoor_task: PlannedActorTask) -> str:
    location = str(planned_glassdoor_task.actor_input.get("location", "")).strip()
    if not location or location.lower() == "remote":
        return "United States"
    return location


def generate_wellfound_actor_task(
    planned_glassdoor_task: PlannedActorTask,
) -> PlannedActorTask:
    normalized_query = planned_glassdoor_task.normalized_query
    query = _derive_query_text(planned_glassdoor_task)
    limit = max(1, int(planned_glassdoor_task.actor_input.get("limit", 100)))
    max_pages = min(10, max(1, math.ceil(limit / 25)))

    actor_input = {
        "query": query,
        "remote": _is_remote_glassdoor_search(planned_glassdoor_task),
        "radiusMiles": 0,
        "radiusKm": 0,
        "salaryMin": 0,
        "salaryMax": 0,
        "equityMin": 0,
        "maxAgeMinutes": 0,
        "maxResults": limit,
        "maxPages": max_pages,
        "enrichDetail": False,
        "enrichCompany": False,
        "companyOnlyMode": False,
        "descriptionMaxLength": 0,
        "compact": False,
        "incrementalMode": False,
        "emitUnchanged": False,
        "emitExpired": False,
        "skipReposts": False,
        "notificationLimit": 5,
        "includeRunMetadata": True,
        "notifyOnlyChanges": True,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
            "apifyProxyCountry": "US",
        },
        "descriptionFormat": "all",
        "excludeEmptyFields": False,
        "includeDetails": False,
    }

    return PlannedActorTask(
        normalized_query=normalized_query,
        actor_key="wellfound_jobs",
        actor_input=actor_input,
    )


def generate_workable_actor_task(
    planned_glassdoor_task: PlannedActorTask,
) -> PlannedActorTask:
    normalized_query = planned_glassdoor_task.normalized_query
    query = _derive_query_text(planned_glassdoor_task)
    limit = max(1, int(planned_glassdoor_task.actor_input.get("limit", 20)))

    actor_input = {
        "startUrls": [],
        "keyword": query,
        "location": _derive_location_text(planned_glassdoor_task),
        "posted_date": "anytime",
        "results_wanted": limit,
        "proxyConfiguration": {
            "useApifyProxy": False,
        },
    }

    return PlannedActorTask(
        normalized_query=normalized_query,
        actor_key="workable_jobs",
        actor_input=actor_input,
    )


def generate_actor_tasks(user_message: str) -> list[PlannedActorTask]:
    glassdoor_task = generate_glassdoor_actor_task(user_message)
    wellfound_task = generate_wellfound_actor_task(glassdoor_task)
    workable_task = generate_workable_actor_task(glassdoor_task)
    return [glassdoor_task, wellfound_task, workable_task]
