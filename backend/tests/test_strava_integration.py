"""
Test suite for CardioCoach Strava Integration
Tests: Strava OAuth endpoints, status, sync, disconnect
Also verifies Garmin endpoints are still dormant in backend
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestStravaEndpoints:
    """Test Strava integration endpoints"""
    
    def test_strava_status_not_connected(self):
        """GET /api/strava/status - should return connected: false when not connected"""
        response = requests.get(f"{BASE_URL}/api/strava/status?user_id=default")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert data["connected"] == False
        assert "last_sync" in data
        assert "workout_count" in data
        print(f"✓ Strava status: connected={data['connected']}, workout_count={data['workout_count']}")
    
    def test_strava_authorize_returns_error_without_credentials(self):
        """GET /api/strava/authorize - should return error when credentials not configured"""
        response = requests.get(f"{BASE_URL}/api/strava/authorize?user_id=default")
        # Should return 503 when STRAVA_CLIENT_ID/SECRET not set (520 via Cloudflare proxy)
        assert response.status_code in [503, 520]
        data = response.json()
        assert "detail" in data
        assert "not configured" in data["detail"].lower() or "contact" in data["detail"].lower()
        print(f"✓ Strava authorize returns error ({response.status_code}): {data['detail']}")
    
    def test_strava_sync_not_connected(self):
        """POST /api/strava/sync - should gracefully handle 'Not connected to Strava' message"""
        response = requests.post(f"{BASE_URL}/api/strava/sync?user_id=default")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] == False
        assert "message" in data
        assert "not connected" in data["message"].lower()
        print(f"✓ Strava sync handles not connected: {data['message']}")
    
    def test_strava_disconnect_success(self):
        """DELETE /api/strava/disconnect - should return success message"""
        response = requests.delete(f"{BASE_URL}/api/strava/disconnect?user_id=default")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] == True
        assert "message" in data
        print(f"✓ Strava disconnect: {data['message']}")


class TestGarminDormantEndpoints:
    """Test that Garmin endpoints still exist in backend (dormant)"""
    
    def test_garmin_status_endpoint_exists(self):
        """GET /api/garmin/status - should still work (dormant endpoint)"""
        response = requests.get(f"{BASE_URL}/api/garmin/status?user_id=default")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert data["connected"] == False
        print(f"✓ Garmin status (dormant): connected={data['connected']}")
    
    def test_garmin_authorize_endpoint_exists(self):
        """GET /api/garmin/authorize - should return error (dormant, no credentials)"""
        response = requests.get(f"{BASE_URL}/api/garmin/authorize")
        # Should return 503 when credentials not configured (520 via Cloudflare proxy)
        assert response.status_code in [503, 520]
        print(f"✓ Garmin authorize (dormant): returns error ({response.status_code}) as expected")
    
    def test_garmin_sync_endpoint_exists(self):
        """POST /api/garmin/sync - should handle not connected (dormant)"""
        response = requests.post(f"{BASE_URL}/api/garmin/sync?user_id=default")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] == False
        print(f"✓ Garmin sync (dormant): {data.get('message', 'handled')}")
    
    def test_garmin_disconnect_endpoint_exists(self):
        """DELETE /api/garmin/disconnect - should work (dormant)"""
        response = requests.delete(f"{BASE_URL}/api/garmin/disconnect?user_id=default")
        assert response.status_code == 200
        print(f"✓ Garmin disconnect (dormant): endpoint exists")


class TestExistingFunctionality:
    """Test that existing CardioCoach functionality still works"""
    
    def test_api_root(self):
        """GET /api/ - should return CardioCoach API message"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "CardioCoach" in data["message"]
        print(f"✓ API root: {data['message']}")
    
    def test_get_workouts(self):
        """GET /api/workouts - should return workout list"""
        response = requests.get(f"{BASE_URL}/api/workouts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Workouts: {len(data)} workouts returned")
    
    def test_get_stats(self):
        """GET /api/stats - should return training statistics"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_workouts" in data
        assert "total_distance_km" in data
        print(f"✓ Stats: {data['total_workouts']} workouts, {data['total_distance_km']} km")
    
    def test_coach_history(self):
        """GET /api/coach/history - should return conversation history"""
        response = requests.get(f"{BASE_URL}/api/coach/history?user_id=default")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Coach history: {len(data)} messages")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
