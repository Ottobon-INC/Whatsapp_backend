# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from modules.user_profile import (
    create_user,
    update_preferred_language,
    update_relation,
    get_user_profile,
    resolve_user_id_by_phone,
)
from modules.response_builder import (
    classify_message,
    generate_medical_response,
    generate_smalltalk_response,
)
from modules.conversation import save_user_message, save_sakhi_message, get_last_messages
from modules.user_answers import save_bulk_answers

app = FastAPI()


class RegisterRequest(BaseModel):
    name: str  # full name
    email: str
    password: str
    phone_number: str | None = None
    role: str | None = "USER"
    preferred_language: str | None = None
    user_relation: str | None = None


class ChatRequest(BaseModel):
    user_id: str | None = None
    phone_number: str | None = None
    message: str
    language: str = "en"


class AnswerItem(BaseModel):
    question_key: str
    selected_options: list[str]


class UserAnswersRequest(BaseModel):
    user_id: str
    answers: list[AnswerItem]


class UpdateRelationRequest(BaseModel):
    user_id: str
    relation: str


class UpdatePreferredLanguageRequest(BaseModel):
    user_id: str
    preferred_language: str


@app.get("/")
def home():
    return {"message": "Sakhi API working!"}


@app.post("/user/register")
def register_user(req: RegisterRequest):
    try:
        user_row = create_user(
            name=req.name,
            email=req.email,
            phone_number=req.phone_number,
            password=req.password,
            role=req.role,
            preferred_language=req.preferred_language,
            relation=req.user_relation,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    user_id = user_row.get("user_id")

    return {"status": "success", "user_id": user_id, "user": user_row}


@app.post("/sakhi/chat")
def sakhi_chat(req: ChatRequest):
    # Resolve user_id via phone_number if not provided
    user_id = req.user_id
    if not user_id:
        if not req.phone_number:
            raise HTTPException(status_code=400, detail="user_id or phone_number is required")
        user_id = resolve_user_id_by_phone(req.phone_number)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found for provided phone number")

    try:
        save_user_message(user_id, req.message, req.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save user message: {e}")

    # Step 1: classify message
    try:
        classification = classify_message(req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to classify message: {e}")

    detected_lang = classification.get("language", req.language)
    signal = classification.get("signal", "NO")

    # Fetch user name for personalization
    user_name = None
    try:
        profile = get_user_profile(user_id)
        if profile:
            user_name = profile.get("name")
    except Exception:
        user_name = None

    # Conversation history for both modes
    history = get_last_messages(user_id, limit=5)

    if signal != "YES":
        # Small-talk mode: no RAG
        try:
            final_ans = generate_smalltalk_response(
                req.message,
                detected_lang,
                history,
                user_name=user_name,
                store_to_kb=False,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate small-talk response: {e}")

        try:
            save_sakhi_message(user_id, final_ans, detected_lang)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save Sakhi message: {e}")

        return {"reply": final_ans, "mode": "general", "language": detected_lang}

    # Medical mode: RAG
    try:
        final_ans, _kb = generate_medical_response(
            prompt=req.message,
            target_lang=detected_lang,
            history=history,
            user_name=user_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate medical response: {e}")

    try:
        save_sakhi_message(user_id, final_ans, detected_lang)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save Sakhi message: {e}")

    return {"reply": final_ans, "mode": "medical", "language": detected_lang}


@app.post("/user/answers")
def save_user_answers(req: UserAnswersRequest):
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if not req.answers:
        raise HTTPException(status_code=400, detail="answers cannot be empty")

    for ans in req.answers:
        if not ans.question_key:
            raise HTTPException(status_code=400, detail="question_key is required for each answer")
        if not ans.selected_options:
            raise HTTPException(status_code=400, detail="selected_options must be non-empty for each answer")

    try:
        saved_count, _ = save_bulk_answers(
            user_id=req.user_id,
            answers=[a.dict() for a in req.answers],
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success", "saved": saved_count}


@app.post("/user/relation")
def set_user_relation(req: UpdateRelationRequest):
    if not req.user_id or not req.relation:
        raise HTTPException(status_code=400, detail="user_id and relation are required")

    try:
        update_relation(req.user_id, req.relation)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success"}


@app.post("/user/preferred-language")
def set_user_preferred_language(req: UpdatePreferredLanguageRequest):
    if not req.user_id or not req.preferred_language:
        raise HTTPException(status_code=400, detail="user_id and preferred_language are required")

    try:
        update_preferred_language(req.user_id, req.preferred_language)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success"}
