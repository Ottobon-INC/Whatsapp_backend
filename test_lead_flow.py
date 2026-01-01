from fastapi.testclient import TestClient
from main import app
import uuid
from unittest.mock import patch

client = TestClient(app)

def test_lead_flow():
    # 1. Register a user
    user_data = {
        "name": "Test User",
        "email": f"test_{uuid.uuid4()}@example.com",
        "password": "password",
        "phone_number": "9999999999"
    }
    
    # Mocking DB calls to avoid errors if tables/columns don't exist yet
    # We will mock the supabase client functions inside modules.user_profile and modules.lead_manager
    
    # Actually, if we mock, we aren't testing the integration completely, but we test the logic.
    # Given the constraint that we can't run the SQL, mocking is the way to verify logic.
    
    with patch("modules.user_profile.supabase_insert") as mock_insert, \
         patch("modules.user_profile.supabase_select") as mock_select, \
         patch("modules.user_profile.supabase_update") as mock_update, \
         patch("modules.lead_manager.supabase_insert") as mock_lead_insert:

        # Mock Register Response
        user_id = str(uuid.uuid4())
        mock_insert.return_value = [{"user_id": user_id, "name": "Test User", "context": {}}]
        
        # Register
        resp = client.post("/user/register", json=user_data)
        assert resp.status_code == 200
        print("✅ User Registered")
        
        # Mock Profile Fetch (needs to return user with context)
        # We need to simulate maintaining state in the mocked loop
        current_context = {}
        
        def side_effect_get_profile(table, select, filters, **kwargs):
            return [{"user_id": user_id, "name": "Test User", "context": current_context}]
        
        mock_select.side_effect = side_effect_get_profile
        
        def side_effect_update(table, match, data, **kwargs):
            nonlocal current_context
            if "context" in data:
                current_context = data["context"]
            return {"status": "success"}

        mock_update.side_effect = side_effect_update

        # 2. Send /newlead
        payload = {"user_id": user_id, "message": "/newlead"}
        resp = client.post("/sakhi/chat", json=payload)
        data = resp.json()
        print(f"User: /newlead -> Bot: {data['reply']}")
        assert "What should we call them?" in data['reply']
        assert data['mode'] == "lead_input"
        
        # 3. Send Name
        payload["message"] = "Jane Doe"
        resp = client.post("/sakhi/chat", json=payload)
        data = resp.json()
        print(f"User: Jane Doe -> Bot: {data['reply']}")
        assert "phone number" in data['reply']
        
        # 4. Send Phone
        payload["message"] = "9876543210"
        resp = client.post("/sakhi/chat", json=payload)
        data = resp.json()
        print(f"User: 9876543210 -> Bot: {data['reply']}")
        assert "how old" in data['reply']

        # 5. Send Age
        payload["message"] = "25"
        resp = client.post("/sakhi/chat", json=payload)
        data = resp.json()
        print(f"User: 25 -> Bot: {data['reply']}")
        assert "gender" in data['reply']

        # 6. Send Gender
        payload["message"] = "Female"
        resp = client.post("/sakhi/chat", json=payload)
        data = resp.json()
        print(f"User: Female -> Bot: {data['reply']}")
        assert "health concern" in data['reply']
        
        # 7. Send Problem
        payload["message"] = "PCOS symptoms"
        resp = client.post("/sakhi/chat", json=payload)
        data = resp.json()
        print(f"User: PCOS symptoms -> Bot: {data['reply']}")
        assert "noted everything down" in data['reply']
        assert data['mode'] == "lead_complete"
        
        # Verify Insert called
        mock_lead_insert.assert_called()
        inserted_data = mock_lead_insert.call_args[0][1]
        print(f"✅ Lead Inserted: {inserted_data}")
        assert inserted_data['name'] == "Jane Doe"
        assert inserted_data['problem'] == "PCOS symptoms"

if __name__ == "__main__":
    try:
        from modules import user_profile
        # Reload to ensure mocks work if previously imported? 
        # Patching usually handles it if done where imported.
        test_lead_flow()
        print("\n🎉 ALL TESTS PASSED! Logic is correct.")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ ERROR: {e}")
