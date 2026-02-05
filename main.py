# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from modules.user_profile import (
    create_user,
    update_preferred_language,
    update_relation,
    get_user_profile,
    get_user_profile,
    resolve_user_id_by_phone,
    get_user_by_phone,
    create_partial_user,
    update_user_profile,
    login_user,
)
from modules.response_builder import (
    classify_message,
    generate_medical_response,
    generate_smalltalk_response,
    contains_telugu_unicode,
    is_mostly_english,
    force_rewrite_to_tinglish,
    force_rewrite_to_telugu,
)
from modules.conversation import save_user_message, save_sakhi_message, get_last_messages
from modules.user_answers import save_bulk_answers
from modules.model_gateway import get_model_gateway, Route
from modules.slm_client import get_slm_client
from modules.guardrails import get_guardrails
from modules.search_hierarchical import hierarchical_rag_query, format_hierarchical_context
from modules.lead_manager import handle_lead_flow, _get_chat_state
from modules.user_rewards import (
    award_points,
    store_new_question,
    get_user_rewards,
    classify_for_reward,
    RewardType,
)
import asyncio

app = FastAPI()



# CORS Configuration - Allow Replit frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize model gateway, SLM client, and guardrails (singleton instances)
model_gateway = get_model_gateway()
slm_client = get_slm_client()
guardrails = get_guardrails()


class RegisterRequest(BaseModel):
    name: str  # full name
    email: str
    password: str
    phone_number: str | None = None
    role: str | None = "USER"
    preferred_language: str | None = None
    user_relation: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


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


@app.post("/user/login")
def login(req: LoginRequest):
    """
    Authenticate user with email and password.
    """
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="email and password are required")
    
    try:
        user = login_user(req.email, req.password)
        
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        return {
            "status": "success",
            "user_id": user.get("user_id"),
            "user": user
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
async def sakhi_chat(req: ChatRequest):
    # 1. Resolve or Create User
    user = None
    if req.user_id:
        user = get_user_profile(req.user_id)
    elif req.phone_number:
        user = get_user_by_phone(req.phone_number)

    # If new user (by phone), create them
    if not user:
        if req.phone_number:
            try:
                user = create_partial_user(req.phone_number)
                # Return Welcome Message
                return {
                    "reply": "Welcome to Sakhi! I'm here to support you on your health journey. ❤️ \n Let's get started! What should I call you? (Please type just your name, e.g., Deepthi)",
                    "mode": "onboarding",
                    "intent": "The intent is to onboarding the user"
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to register user: {e}")
        else:
             raise HTTPException(status_code=400, detail="user_id or phone_number is required")

    user_id = user.get("user_id")

    # 2. Check Onboarding Status (NULL checks)
    current_name = user.get("name")
    current_gender = user.get("gender")
    # Handle possible case variants for location
    current_location = user.get("location") or user.get("Location")

    print(f"DEBUG: User={user_id}, Name={current_name}, Gender={current_gender}, Location={current_location}")

    msg = req.message.strip()

    # STATE 1: WAITING FOR NAME (User sent Name)
    if not current_name:
        update_user_profile(user_id, {"name": msg})
        return {
            "reply": f"Nice to meet you, {msg}! Can you let me know your gender ? (Please reply with 'Male' or 'Female')",
            "mode": "onboarding",
            "intent": "The intent is to ask for gender"
        }

    # STATE 2: WAITING FOR GENDER (User sent Gender)
    elif not current_gender:
        update_user_profile(user_id, {"gender": msg})
        return {
            "reply": "Got it. And finally, what's your location (City/Town)? (e.g., Vizag)",
            "mode": "onboarding",
            "intent": "The intent is to ask for location"
        }

    # STATE 3: WAITING FOR LOCATION (User sent Location)
    elif not current_location:
        # Update both keys to be safe
        update_user_profile(user_id, {"location": msg}) 
        
        long_intro = (
            "Thank you! Your profile is all set.\n"
            "Welcome to JanmaSethu. I know that the journey to parenthood is filled with ups and downs, endless questions, and moments where you just need someone to listen.\n\n"
            "That is why I am here.\n\n"
            "I am Sakhi, and I want you to think of me not just as a tool, but as your trusted companion. I am your judgment-free friend, here to hold your hand through it all—from pre-parenthood to pregnancy and beyond.\n\n"
            "How can I help you today?\n\n"
            "💛 I am a Safe Space: Pour your heart out, ask me the \"silly\" questions, or just vent. I am here to listen without judgment.\n\n"
            "👩‍⚕️ I offer Doctor-Approved Trust: While I speak to you like a friend, my wisdom comes from validated medical professionals, so you can trust the guidance I give.\n\n"
            "🧠 I bring Visual Clarity: Confused by medical terms? I use simple infographics to make complex topics clear and easy to understand.\n\n"
            "My goal is to restore your faith and give you strength when you need it most. I am ready to listen whenever you are ready to talk.\n\n"
        )
        
        return {
            "reply": long_intro,
            "mode": "onboarding_complete",
            "image": "Sakhi_intro.png",
            "intent": "The intent is to complete the onboarding"
        }

    # 2.0 Check /rewards command
    if msg.lower() == "/rewards":
        total = get_user_rewards(user_id)
        return {
            "reply": f"🏆 You have earned {total} reward points! Keep asking questions to earn more.",
            "mode": "rewards",
            "intent": "The intent is to show rewards"
        }

    # 2.1 Check Lead Feature Flow (/newlead or in-progress)
    try:
        # Check separate state table, do NOT rely on user['context']
        chat_state = _get_chat_state(user_id)
        if chat_state is None:
             chat_state = {}
        
        # Check if user triggered new lead OR is currently in a lead flow step
        if msg.lower() == "/newlead" or (chat_state.get("lead_flow") and chat_state["lead_flow"].get("step")):
             return handle_lead_flow(user_id, msg, user)
    except Exception as e:
        print(f"❌ ERROR in Lead Flow: {e}")
        # Improve error visibility - likely DB schema missing
        if "sakhi_chat_states" in str(e):
             print("⚠️ HINT: Did you run setup_leads_strict.sql? The 'sakhi_chat_states' table might be missing.")
        pass

    # 3. Normal Flow
    
    # ===== GUARDRAILS: Detect Intent & Handle Out-of-Scope =====
    # Check if user is asking about off-topic things (sports, movies, etc.)
    redirect_response = guardrails.get_redirect_for_out_of_scope(req.message)
    if redirect_response:
        # Politely redirect to fertility/pregnancy topics
        try:
            save_user_message(user_id, req.message, req.language)
            save_sakhi_message(user_id, redirect_response, req.language)
        except:
            pass
        return {
            "reply": redirect_response,
            "mode": "general",
            "language": req.language,
            "intent": "out_of_scope"
        }
    
    try:
        save_user_message(user_id, req.message, req.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save user message: {e}")

    # STEP 0: Decide routing using Model Gateway
    # NOTE: Router works best with English. Translate first for routing check?
    from modules.translation_service import translate_query 
    # STEP 0: Parallelize Translation and Classification
    # To reduce latency, we run these independent tasks concurrently.
    
    # 1. Start Translation (Independent)
    # Translate for internal logic only (routing + search)
    translation_task = asyncio.create_task(translate_query(req.message, target_lang="en"))
    
    # 2. Start Classification (Independent)
    classification_task = asyncio.create_task(classify_message(req.message))

    # 3. Start Intent Label Generation (Independent)
    # Just initiate it here, we will gather it later
    # Use detected lang if available, else default to 'en' first, but we don't have it yet.
    # So we can pass 'en' or wait.
    # BETTER: Wait for classification/translation first? 
    # Actually, let's run it parallel with just the raw message. SLM can handle language.
    # We'll pass the requested language if user explicitly sent one, or just 'en' for now.
    intent_task = asyncio.create_task(slm_client.generate_intent_label(req.message, language=req.language))

    # Wait for all to complete
    try:
        english_intent_query, classification, intent_label = await asyncio.gather(
            translation_task, 
            classification_task, 
            intent_task
        )
    except Exception as e:
         # If classification fails, we might still have translation, but better to fail safe
         raise HTTPException(status_code=500, detail=f"Failed during initial processing: {e}")
    
    # Pass English query to router for better accuracy on non-English inputs
    route = await model_gateway.decide_route(english_intent_query)
    # STEP: Decide FINAL response language (single source of truth)
    detected_lang = classification.get("language", "en").lower()
    signal = classification.get("signal", "NO")

    if detected_lang == "tinglish":
        target_lang = "Tinglish"   # respond in Tinglish
    elif detected_lang in ["telugu", "te"]:
        target_lang = "Telugu"
    else:
        target_lang = "English"


    # Fetch user name for personalization
    user_name = None
    try:
        profile = get_user_profile(user_id)
        if profile:
            user_name = profile.get("name")
            if user_name and not user_name.strip():
                user_name = None
    except Exception as e:
        print(f"DEBUGGING ERROR: Failed to fetch profile for name: {e}")
        user_name = None

    print(f"DEBUG: Final user_name passed to LLM: '{user_name}'")

    # Conversation history for both modes
    history = get_last_messages(user_id, limit=5)

    # ===== ROUTE 1: SLM_DIRECT (Small talk, no RAG) =====
    if route == Route.SLM_DIRECT:
        try:
            final_ans = await slm_client.generate_chat(
                message=req.message,
                language=target_lang,
                user_name=user_name,
            )

            # HARD ENFORCEMENT: Tinglish check for SLM
            if target_lang.lower() == "tinglish":
                 if contains_telugu_unicode(final_ans) or is_mostly_english(final_ans):
                     print("⚠️ SLM Validation Failure. Forcing Rewrite.")
                     final_ans = await force_rewrite_to_tinglish(final_ans, user_name=user_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate SLM chat response: {e}")
        
        try:
            save_sakhi_message(user_id, final_ans, target_lang)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save Sakhi message: {e}")
        
        # Light cleanup of output
        final_ans = guardrails.clean_output(final_ans)
        
        # STRIP FOLLOW-UP QUESTIONS for small talk (SLM_DIRECT should not have follow-ups)
        import re
        final_ans = re.sub(r'(?i)\n\s*follow\s*-?\s*ups?\s*:.*$', '', final_ans, flags=re.DOTALL).strip()
        
        # NUCLEAR CLEANUP for specific banned words
        final_ans = re.sub(r'(?i)\b(aam|aayi)\b[,.]*', '', final_ans).strip()

        # Award points asynchronously (CONVERSATIONAL = 1 pt)
        asyncio.create_task(award_points(user_id, RewardType.CONVERSATIONAL))

        return {
            "reply": final_ans,
            "mode": "general",
            "language": target_lang,
            "reply": final_ans,
            "mode": "general",
            "language": target_lang,
            "route": "slm_direct",
            "intent": intent_label
        }
    
    # ===== ROUTE 2: SLM_RAG (Simple medical, RAG + SLM) =====
    elif route == Route.SLM_RAG:
        # Perform RAG search using TRANSLATED QUERY for better recall
        try:
            # We pass the translated english query to the search function
            # Use english_intent_query for RAG search as it yields better semantic matches
            search_query = english_intent_query if english_intent_query else req.message
            kb_results, rag_best_similarity = await hierarchical_rag_query(search_query) 
            context_text = format_hierarchical_context(kb_results)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to perform RAG search: {e}")
        
        # Generate response using SLM with context
        try:
            # STRATEGY CHANGE for Tinglish & Telugu:
            # 1. Ask SLM for English (Ensures factual accuracy from RAG)
            # 2. Use GPT-4o-mini to translate to natural Tinglish/Telugu
            effective_lang = "English" if target_lang in ["Tinglish", "Telugu"] else target_lang

            final_ans = await slm_client.generate_rag_response(
                context=context_text,
                message=req.message, # Keep original message for personality/tone matching
                language=effective_lang,
                user_name=user_name,
            )

            # FORCE REWRITE
            if target_lang == "Tinglish":
                 print(f"ℹ️  Tinglish requested. Converting English SLM response to Tinglish...")
                 final_ans = await force_rewrite_to_tinglish(final_ans, user_name=user_name)
            elif target_lang == "Telugu":
                 print(f"ℹ️  Telugu requested. Converting English SLM response to Telugu...")
                 final_ans = await force_rewrite_to_telugu(final_ans, user_name=user_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate SLM RAG response: {e}")
        
        try:
            save_sakhi_message(user_id, final_ans, target_lang)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save Sakhi message: {e}")
        
        # Extract metadata from KB results
        infographic_url = None
        youtube_link = None
        if kb_results:
            for item in kb_results:
                if item.get("source_type") == "FAQ":
                    if item.get("infographic_url"):
                        infographic_url = item["infographic_url"]
                    if item.get("youtube_link"):
                        youtube_link = item["youtube_link"]
                    if infographic_url or youtube_link:
                        break
        
        response_payload = {
            "reply": final_ans,
            "mode": "medical",
            "language": target_lang,
            "youtube_link": youtube_link,
            "infographic_url": infographic_url,
            "infographic_url": infographic_url,
            "route": "slm_rag",
            "intent": intent_label
        }
        
        # Light cleanup of output
        cleaned_reply = guardrails.clean_output(final_ans)
        
        # NUCLEAR CLEANUP
        import re
        cleaned_reply = re.sub(r'(?i)\b(aam|aayi)\b[,.]*', '', cleaned_reply).strip()
        response_payload["reply"] = cleaned_reply
        
        # Award points asynchronously
        best_similarity = 0.0
        if kb_results:
             best_similarity = max((item.get("similarity", 0) for item in kb_results), default=0.0)

        reward_type = classify_for_reward(route="slm_rag", rag_similarity=best_similarity)
        asyncio.create_task(award_points(user_id, reward_type))
        
        # Store new questions for KB expansion
        if reward_type == RewardType.NEW_QUESTION:
            asyncio.create_task(store_new_question(user_id, req.message, best_similarity))
        
        # Safe logging to avoid Unicode errors on Windows console
        try:
            print(f"Response Payload: {response_payload}")
        except UnicodeEncodeError:
            print(f"Response Payload sent (contains special characters)")
        return response_payload

    # ===== ROUTE 3: OPENAI_RAG (Complex medical, ambiguous, or default queries) =====
    # Model gateway has already decided this should go to OpenAI RAG
    # Trust the model gateway decision - don't override with signal check

    # ===== ROUTE 3: OPENAI_RAG (Complex medical or default, RAG + GPT-4) =====
    # Medical mode: RAG
    try:
        final_ans, _kb = await generate_medical_response(
            prompt=req.message,
            target_lang=target_lang,
            history=history,
            user_name=user_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate medical response: {e}")

    try:
        save_sakhi_message(user_id, final_ans, target_lang)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save Sakhi message: {e}")

    # Extract infographic_url and youtube_link if available in kb_results
    infographic_url = None
    youtube_link = None

    if _kb:
        for item in _kb:
            if item.get("source_type") == "FAQ":
                if item.get("infographic_url"):
                    infographic_url = item["infographic_url"]
                if item.get("youtube_link"):
                    youtube_link = item["youtube_link"]
                # If we found an FAQ match, we likely want to use its metadata
                if infographic_url or youtube_link:
                    break

    response_payload = {
        "reply": final_ans, 
        "mode": "medical", 
        "language": target_lang,
        "youtube_link": youtube_link,
        "infographic_url": infographic_url,
        "infographic_url": infographic_url,
        "route": "openai_rag",
        "intent": intent_label
    }
    
    # Light cleanup of output
    response_payload["reply"] = guardrails.clean_output(final_ans)
    
    # Award points asynchronously (MEDICAL = 3 pts for OpenAI RAG)
    asyncio.create_task(award_points(user_id, RewardType.MEDICAL))
    
    # Safe logging to avoid Unicode errors on Windows console
    try:
        print(f"Response Payload: {response_payload}")
    except UnicodeEncodeError:
        print(f"Response Payload sent (contains special characters)")
    return response_payload


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