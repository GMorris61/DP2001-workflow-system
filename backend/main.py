from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt
import requests

from database import SessionLocal, engine
from models import Base, Employee, PreValidation, DP2001Request, AuditLog
from schemas import PreValidationCreate, PreValidationResponse, DP2001Create, DP2001Response
from datetime import datetime

# ---------------------------------------------------------
# OKTA CONFIGURATION
# ---------------------------------------------------------

OKTA_ISSUER = "https://integrator-5266877.okta.com/oauth2/default"
OKTA_JWKS_URL = f"{OKTA_ISSUER}/v1/keys"
OKTA_AUDIENCE = "0oa104985iff80esRT698"  # Your Client ID

security = HTTPBearer()
jwks_cache = None

def get_jwks():
    global jwks_cache
    if jwks_cache is None:
        resp = requests.get(OKTA_JWKS_URL)
        if resp.status_code != 200:
            raise Exception("Could not fetch JWKS from Okta")
        jwks_cache = resp.json()
    return jwks_cache

def verify_okta_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    jwks = get_jwks()

    # Extract header to find matching key
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
    if key is None:
        raise HTTPException(status_code=401, detail="Invalid token key")

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=OKTA_AUDIENCE,
            issuer=OKTA_ISSUER,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload  # This becomes "user" in your endpoints


# ---------------------------------------------------------
# FASTAPI APP + DATABASE
# ---------------------------------------------------------

app = FastAPI()
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# AUDIT LOGGING
# ---------------------------------------------------------

def log_action(db, action, entity_type, entity_id, old_value=None, new_value=None):
    log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/health")
def health_check(user: dict = Depends(verify_okta_token)):
    return {"status": "ok", "app": "dp2001", "env": "local"}


# ---------------------------------------------------------
# EMPLOYEES
# ---------------------------------------------------------

@app.post("/seed-employees")
def seed_employees(db: Session = Depends(get_db), user: dict = Depends(verify_okta_token)):

    dummy_data = [
        Employee(
            name="Alicia Martinez",
            title="Principal Administrative Associate",
            location="Brooklyn",
            union="Local 1180",
            salary_step="7",
            status="active"
        ),
        Employee(
            name="David Chen",
            title="Staff Analyst",
            location="Queens",
            union="DC37",
            salary_step="4",
            status="active"
        ),
        Employee(
            name="Monique Johnson",
            title="Education Analyst",
            location="Manhattan",
            union="CSA",
            salary_step="5",
            status="active"
        ),
        Employee(
            name="Robert Singh",
            title="Accountant",
            location="Bronx",
            union="DC37",
            salary_step="3",
            status="active"
        ),
        Employee(
            name="Sarah Thompson",
            title="Administrative Staff Analyst",
            location="Staten Island",
            union="Local 1180",
            salary_step="8",
            status="active"
        ),
    ]

    for emp in dummy_data:
        db.add(emp)

    db.commit()
    return {"message": "Employees seeded"}


@app.get("/employees")
def list_employees(db: Session = Depends(get_db), user: dict = Depends(verify_okta_token)):
    return db.query(Employee).all()


# ---------------------------------------------------------
# PREVALIDATION
# ---------------------------------------------------------

@app.post("/prevalidation", response_model=PreValidationResponse)
def create_prevalidation(
    data: PreValidationCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):
    pre = PreValidation(
        employee_id=data.employee_id,
        action_type=data.action_type,
        comments=data.comments,
        status="pending"
    )
    db.add(pre)
    db.commit()
    db.refresh(pre)
    return pre


@app.get("/prevalidation/{pre_id}", response_model=PreValidationResponse)
def get_prevalidation(
    pre_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):
    return db.query(PreValidation).filter(PreValidation.id == pre_id).first()


@app.patch("/prevalidation/{pre_id}/approve")
def approve_prevalidation(
    pre_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):
    pre = db.query(PreValidation).filter(PreValidation.id == pre_id).first()
    pre.status = "approved"
    db.commit()
    return {"message": "Pre-validation approved"}


@app.patch("/prevalidation/{pre_id}/reject")
def reject_prevalidation(
    pre_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):
    pre = db.query(PreValidation).filter(PreValidation.id == pre_id).first()
    pre.status = "rejected"
    db.commit()
    return {"message": "Pre-validation rejected"}


# ---------------------------------------------------------
# DP-2001 WORKFLOW
# ---------------------------------------------------------

@app.post("/dp2001", response_model=DP2001Response)
def create_dp2001(
    data: DP2001Create,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):

    pre = db.query(PreValidation).filter(PreValidation.id == data.prevalidation_id).first()
    if not pre:
        return {"error": "Pre-validation not found"}

    if pre.status != "approved":
        return {"error": "Pre-validation must be approved before submitting DP-2001"}

    dp = DP2001Request(
        employee_id=data.employee_id,
        prevalidation_id=data.prevalidation_id,
        action_type=data.action_type,
        comments=data.comments,
        status="submitted"
    )

    db.add(dp)
    db.commit()
    db.refresh(dp)
    return dp


@app.get("/dp2001/{dp_id}", response_model=DP2001Response)
def get_dp2001(
    dp_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):
    return db.query(DP2001Request).filter(DP2001Request.id == dp_id).first()


@app.patch("/dp2001/{dp_id}/process")
def process_dp2001(
    dp_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):
    dp = db.query(DP2001Request).filter(DP2001Request.id == dp_id).first()

    old = dp.status
    dp.status = "processing"
    db.commit()

    log_action(db, "dp2001_status_change", "DP2001", dp_id, old, "processing")

    return {"message": "DP-2001 moved to processing"}


@app.patch("/dp2001/{dp_id}/complete")
def complete_dp2001(
    dp_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):
    dp = db.query(DP2001Request).filter(DP2001Request.id == dp_id).first()

    old = dp.status
    dp.status = "completed"
    db.commit()

    log_action(db, "dp2001_status_change", "DP2001", dp_id, old, "completed")

    return {"message": "DP-2001 marked as completed"}


@app.patch("/dp2001/{dp_id}/reject")
def reject_dp2001(
    dp_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):
    dp = db.query(DP2001Request).filter(DP2001Request.id == dp_id).first()

    old = dp.status
    dp.status = "rejected"
    db.commit()

    log_action(db, "dp2001_status_change", "DP2001", dp_id, old, "rejected")

    return {"message": "DP-2001 rejected"}


# ---------------------------------------------------------
# AUDIT LOGS
# ---------------------------------------------------------

@app.get("/audit")
def list_audit_logs(
    db: Session = Depends(get_db),
    user: dict = Depends(verify_okta_token)
):
    return db.query(AuditLog).all()
