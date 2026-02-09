from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from typing import Optional
from config import settings
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_client = None


def get_col():
    return db_client[settings.MONGO_DB][settings.MONGO_COLLECTION]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_client
    logger.info(f"Connecting to MongoDB...")
    logger.info(f"  DB: {settings.MONGO_DB} | Collection: {settings.MONGO_COLLECTION}")
    db_client = AsyncIOMotorClient(
        settings.MONGO_URI, maxPoolSize=10, serverSelectionTimeoutMS=5000,
    )
    try:
        await db_client.admin.command("ping")
        col = db_client[settings.MONGO_DB][settings.MONGO_COLLECTION]
        total = await col.count_documents({})
        logger.info(f"✓ Connected — {total} documents")

        # Debug: show field types of first doc
        sample = await col.find_one({})
        if sample:
            sid = sample.get("sessionId")
            logger.info(f"  sessionId example: {sid!r} (type: {type(sid).__name__})")
            la = sample.get("leadAnalysed")
            logger.info(f"  leadAnalysed example: {la!r} (type: {type(la).__name__})")
            out = sample.get("output")
            logger.info(f"  output type: {type(out).__name__}")
    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        raise
    yield
    db_client.close()


app = FastAPI(title="Lead Qualification API", version="4.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# ── Helpers ──

def serialize(obj):
    """Make any BSON type JSON-safe."""
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize(i) for i in obj]
    elif type(obj).__name__ in ("ObjectId", "Decimal128"):
        return str(obj)
    elif type(obj).__name__ == "datetime":
        return obj.isoformat()
    return obj


def flatten_lead(doc: dict) -> dict:
    doc = serialize(doc)
    doc.pop("_id", None)
    output = doc.get("output", None)
    has_output = isinstance(output, dict) and len(output) > 0

    base = {
        "sessionId": str(doc.get("sessionId", "")),
        "messageLength": doc.get("messageLength", 0) or 0,
        "analysedAt": doc.get("analysedAt", None),
        "leadAnalysed": doc.get("leadAnalysed", False),
        "hasOutput": has_output,
    }
    if has_output:
        base.update({
            "qualified": output.get("qualified", False),
            "intent": output.get("intent", "UNKNOWN"),
            "confidence": output.get("confidence", 0) or 0,
            "signals": output.get("signals", []) or [],
            "summary": output.get("summary", []) or [],
        })
    else:
        base.update({
            "qualified": False, "intent": "PENDING",
            "confidence": 0, "signals": [], "summary": [],
        })
    return base


def extract_chat(doc: dict) -> list:
    """Pull chat messages from a raw document."""
    raw = serialize(doc)
    messages = raw.get("messages", [])
    if not isinstance(messages, list):
        return []
    chat = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        msg_type = m.get("type", "unknown")
        data = m.get("data")
        content = ""
        if isinstance(data, dict):
            content = data.get("content", "")
        elif isinstance(data, str):
            content = data
        if content:
            chat.append({"type": msg_type, "content": str(content)})
    return chat


async def find_by_session(col, session_id: str):
    """
    Robust sessionId lookup — handles string, int, regex.
    This is the fix for 'detail not found'.
    """
    sid = str(session_id).strip()
    digits = "".join(c for c in sid if c.isdigit())

    # Attempt 1: exact string match
    doc = await col.find_one({"sessionId": sid})
    if doc:
        logger.info(f"  Found by exact string: {sid}")
        return doc

    # Attempt 2: as integer (MongoDB might store phone numbers as int)
    if digits:
        try:
            doc = await col.find_one({"sessionId": int(digits)})
            if doc:
                logger.info(f"  Found by int: {int(digits)}")
                return doc
        except (ValueError, OverflowError):
            pass

    # Attempt 3: regex on string
    if digits:
        doc = await col.find_one({"sessionId": {"$regex": digits}})
        if doc:
            logger.info(f"  Found by regex: {digits}")
            return doc

    # Attempt 4: scan recent docs (brute force fallback)
    cursor = col.find({}).limit(200)
    async for d in cursor:
        doc_sid = str(d.get("sessionId", ""))
        if doc_sid == sid or digits in doc_sid:
            logger.info(f"  Found by scan: {doc_sid}")
            return d

    logger.warning(f"  NOT FOUND for: {sid}")
    return None


# ══════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=(Path(__file__).parent / "dashboard.html").read_text("utf-8"))


# ══════════════════════════════════════════
# API ROUTES
# ══════════════════════════════════════════

@app.get("/api/health")
async def health():
    try:
        await db_client.admin.command("ping")
        col = get_col()
        total = await col.count_documents({})
        with_output = 0
        async for doc in col.find({}).limit(500):
            o = doc.get("output")
            if isinstance(o, dict) and len(o) > 0:
                with_output += 1
        return {
            "status": "ok", "database": settings.MONGO_DB,
            "collection": settings.MONGO_COLLECTION,
            "totalDocuments": total, "withAnalysis": with_output,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/leads")
async def list_leads(
    search: Optional[str] = Query(None),
    intent: Optional[str] = Query(None),
    qualified: Optional[bool] = Query(None),
    sort: str = Query("desc", regex="^(asc|desc)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    col = get_col()
    mongo_query = {}

    if search:
        digits = "".join(c for c in search if c.isdigit())
        if digits:
            mongo_query["sessionId"] = {"$regex": digits}

    sort_dir = -1 if sort == "desc" else 1
    all_leads = []

    async for doc in col.find(mongo_query).sort("analysedAt", sort_dir).limit(500):
        lead = flatten_lead(doc)
        if not lead["hasOutput"]:
            continue
        if intent and lead["intent"] != intent.upper():
            continue
        if qualified is not None and lead["qualified"] != qualified:
            continue
        all_leads.append(lead)

    total = len(all_leads)
    return {
        "leads": all_leads[skip: skip + limit],
        "total": total, "skip": skip, "limit": limit,
        "hasMore": (skip + limit) < total,
    }


@app.get("/api/leads/{session_id}")
async def get_lead(session_id: str):
    """Get single lead + chat. Uses robust matching."""
    logger.info(f"GET /api/leads/{session_id}")
    col = get_col()

    doc = await find_by_session(col, session_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Lead '{session_id}' not found")

    lead = flatten_lead(doc)
    lead["chat"] = extract_chat(doc)
    return lead


@app.get("/api/stats")
async def get_stats():
    col = get_col()
    total = 0
    qualified_count = 0
    confidence_sum = 0
    message_sum = 0
    intent_counts = {}

    async for doc in col.find({}).limit(1000):
        lead = flatten_lead(doc)
        if not lead["hasOutput"]:
            continue
        total += 1
        if lead["qualified"]:
            qualified_count += 1
        confidence_sum += lead.get("confidence", 0) or 0
        message_sum += lead.get("messageLength", 0) or 0
        intent = lead.get("intent", "UNKNOWN")
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    if total == 0:
        return {
            "total": 0, "qualified": 0, "notQualified": 0,
            "qualificationRate": 0, "avgConfidence": 0,
            "avgMessages": 0, "intentBreakdown": {},
        }
    return {
        "total": total, "qualified": qualified_count,
        "notQualified": total - qualified_count,
        "qualificationRate": round(qualified_count / total, 3),
        "avgConfidence": round(confidence_sum / total, 3),
        "avgMessages": round(message_sum / total, 1),
        "intentBreakdown": intent_counts,
    }