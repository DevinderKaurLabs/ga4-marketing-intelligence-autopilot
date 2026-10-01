"""The contract the LLM must fill. Anything else is rejected and retried."""
from typing import List, Literal

from pydantic import BaseModel, Field

OWNERS = ["Performance marketing", "SEO & content", "CRM & retention", "E-commerce & CRO",
          "Merchandising", "Analytics & tracking"]
Owner = Literal["Performance marketing", "SEO & content", "CRM & retention", "E-commerce & CRO",
                "Merchandising", "Analytics & tracking"]


class Change(BaseModel):
    title: str
    detail: str
    severity: Literal["critical", "warning", "watch", "positive"]


class Action(BaseModel):
    action: str
    why: str
    owner: Owner
    priority: Literal["high", "medium", "low"]
    evidence: str


class Brief(BaseModel):
    headline: str
    executive_summary: List[str] = Field(min_length=2, max_length=4)
    what_changed: List[Change] = Field(min_length=1, max_length=5)
    likely_drivers: List[str] = Field(default_factory=list, max_length=4)
    risks: List[str] = Field(default_factory=list, max_length=4)
    actions: List[Action] = Field(min_length=1, max_length=3)
    data_caveats: List[str] = Field(default_factory=list, max_length=4)


OWNER_KEYWORDS = [
    ("track", "Analytics & tracking"), ("analytic", "Analytics & tracking"), ("data", "Analytics & tracking"),
    ("crm", "CRM & retention"), ("retention", "CRM & retention"), ("loyal", "CRM & retention"),
    ("email", "CRM & retention"), ("seo", "SEO & content"), ("content", "SEO & content"),
    ("merch", "Merchandising"), ("product", "Merchandising"), ("cro", "E-commerce & CRO"),
    ("e-commerce", "E-commerce & CRO"), ("ecommerce", "E-commerce & CRO"), ("checkout", "E-commerce & CRO"),
    ("paid", "Performance marketing"), ("performance", "Performance marketing"), ("media", "Performance marketing"),
]


SEVERITY_MAP = {"high": "critical", "severe": "critical", "major": "critical", "medium": "warning",
                "moderate": "warning", "low": "watch", "info": "watch", "minor": "watch", "neutral": "watch",
                "good": "positive", "upside": "positive", "opportunity": "positive", "gain": "positive"}
PRIORITY_MAP = {"critical": "high", "urgent": "high", "p1": "high", "normal": "medium", "p2": "medium",
                "p3": "low", "minor": "low"}
LIST_LIMITS = {"executive_summary": 4, "what_changed": 5, "likely_drivers": 4, "risks": 4,
               "actions": 3, "data_caveats": 4}


def _as_text(item):
    if isinstance(item, dict):
        return " ".join(str(v) for v in item.values())
    return str(item)


def normalise(data: dict) -> dict:
    """Forgive formatting slips before strict validation: wording of owners/severities, list lengths,
    objects where plain sentences were expected. Numbers are never touched."""
    for key in ("executive_summary", "likely_drivers", "risks", "data_caveats"):
        val = data.get(key)
        if isinstance(val, str):
            val = [val]
        if isinstance(val, list):
            data[key] = [_as_text(v) for v in val]
    for key, limit in LIST_LIMITS.items():
        if isinstance(data.get(key), list):
            data[key] = data[key][:limit]
    for a in data.get("actions", []) or []:
        owner = str(a.get("owner", ""))
        if owner not in OWNERS:
            low = owner.lower()
            a["owner"] = next((o for k, o in OWNER_KEYWORDS if k in low), owner)
        pr = str(a.get("priority", "")).lower().strip()
        a["priority"] = PRIORITY_MAP.get(pr, pr)
    for c in data.get("what_changed", []) or []:
        sev = str(c.get("severity", "")).lower().strip()
        c["severity"] = SEVERITY_MAP.get(sev, sev)
    return data
