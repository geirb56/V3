import requests
import sys
import json
from datetime import datetime

class CardioCoachAPITester:
    def __init__(self, base_url="https://pace-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response preview: {str(response_data)[:200]}...")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    "test": name,
                    "endpoint": endpoint,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "endpoint": endpoint,
                "error": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test API root endpoint"""
        return self.run_test("API Root", "GET", "", 200)

    def test_get_workouts(self):
        """Test get all workouts"""
        success, response = self.run_test("Get All Workouts", "GET", "workouts", 200)
        if success and isinstance(response, list):
            print(f"   Found {len(response)} workouts")
            if len(response) > 0:
                print(f"   Sample workout: {response[0].get('name', 'N/A')}")
        return success, response

    def test_get_workout_detail(self, workout_id):
        """Test get specific workout"""
        success, response = self.run_test(
            f"Get Workout Detail ({workout_id})", 
            "GET", 
            f"workouts/{workout_id}", 
            200
        )
        if success:
            print(f"   Workout: {response.get('name', 'N/A')} - {response.get('type', 'N/A')}")
        return success, response

    def test_get_stats(self):
        """Test get training statistics"""
        success, response = self.run_test("Get Training Stats", "GET", "stats", 200)
        if success:
            print(f"   Total workouts: {response.get('total_workouts', 0)}")
            print(f"   Total distance: {response.get('total_distance_km', 0)} km")
            print(f"   Avg HR: {response.get('avg_heart_rate', 'N/A')} bpm")
        return success, response

    def test_coach_analyze(self):
        """Test AI coach analysis"""
        test_message = "Analyze my recent training load and effort distribution."
        success, response = self.run_test(
            "Coach AI Analysis (EN)", 
            "POST", 
            "coach/analyze", 
            200,
            data={"message": test_message, "language": "en"}
        )
        if success:
            print(f"   AI Response length: {len(response.get('response', ''))} chars")
            print(f"   Message ID: {response.get('message_id', 'N/A')}")
        return success, response

    def test_coach_analyze_french(self):
        """Test AI coach analysis in French"""
        test_message = "Analyse ma charge d'entrainement recente et la distribution de l'effort."
        success, response = self.run_test(
            "Coach AI Analysis (FR)", 
            "POST", 
            "coach/analyze", 
            200,
            data={"message": test_message, "language": "fr"}
        )
        if success:
            print(f"   AI Response length: {len(response.get('response', ''))} chars")
            print(f"   Message ID: {response.get('message_id', 'N/A')}")
            print(f"   Response preview: {response.get('response', '')[:100]}...")
        return success, response

    def test_create_workout(self):
        """Test creating a new workout"""
        test_workout = {
            "type": "run",
            "name": "Test Run",
            "date": "2026-01-15",
            "duration_minutes": 30,
            "distance_km": 5.0,
            "avg_heart_rate": 150,
            "avg_pace_min_km": 6.0,
            "notes": "Test workout from API testing"
        }
        success, response = self.run_test(
            "Create New Workout", 
            "POST", 
            "workouts", 
            200,
            data=test_workout
        )
        if success:
            print(f"   Created workout ID: {response.get('id', 'N/A')}")
        return success, response

    def test_get_messages(self):
        """Test get coach messages"""
        return self.run_test("Get Coach Messages", "GET", "messages", 200)

    def test_coach_history(self):
        """Test get conversation history"""
        success, response = self.run_test(
            "Get Coach History", 
            "GET", 
            "coach/history?user_id=default&limit=50", 
            200
        )
        if success:
            print(f"   Found {len(response)} conversation messages")
            if len(response) > 0:
                print(f"   Latest message: {response[-1].get('content', '')[:50]}...")
        return success, response

    def test_clear_coach_history(self):
        """Test clear conversation history"""
        success, response = self.run_test(
            "Clear Coach History", 
            "DELETE", 
            "coach/history?user_id=default", 
            200
        )
        if success:
            print(f"   Deleted {response.get('deleted_count', 0)} messages")
        return success, response

    def test_deep_analysis(self, workout_id):
        """Test deep workout analysis"""
        test_message = "Deep analysis of this workout"
        success, response = self.run_test(
            "Deep Workout Analysis", 
            "POST", 
            "coach/analyze", 
            200,
            data={
                "message": test_message, 
                "workout_id": workout_id,
                "language": "en",
                "deep_analysis": True,
                "user_id": "default"
            }
        )
        if success:
            print(f"   Deep analysis response length: {len(response.get('response', ''))} chars")
            print(f"   Message ID: {response.get('message_id', 'N/A')}")
            print(f"   Response preview: {response.get('response', '')[:100]}...")
        return success, response

    def test_coach_memory_persistence(self):
        """Test that coach remembers previous conversations"""
        # First message
        msg1 = "I had a great run yesterday"
        success1, response1 = self.run_test(
            "Coach Memory Test - Message 1", 
            "POST", 
            "coach/analyze", 
            200,
            data={"message": msg1, "language": "en", "user_id": "test_memory"}
        )
        
        if not success1:
            return False, {}
        
        # Second message that should reference the first
        msg2 = "How does that compare to my other recent workouts?"
        success2, response2 = self.run_test(
            "Coach Memory Test - Message 2", 
            "POST", 
            "coach/analyze", 
            200,
            data={"message": msg2, "language": "en", "user_id": "test_memory"}
        )
        
        if success2:
            print(f"   Memory test response: {response2.get('response', '')[:150]}...")
        
        return success2, response2

def main():
    print("🏃 CardioCoach API Testing Suite")
    print("=" * 50)
    
    tester = CardioCoachAPITester()
    
    # Test basic endpoints
    tester.test_root_endpoint()
    
    # Test workouts endpoints
    workouts_success, workouts_data = tester.test_get_workouts()
    
    # Test workout detail with mock data
    if workouts_success and workouts_data and len(workouts_data) > 0:
        first_workout_id = workouts_data[0].get('id')
        if first_workout_id:
            tester.test_get_workout_detail(first_workout_id)
    
    # Test stats
    tester.test_get_stats()
    
    # Test coach analysis (this might take longer due to AI processing)
    print("\n⚠️  Testing AI Coach (may take 10-30 seconds)...")
    tester.test_coach_analyze()
    
    # Test French coach analysis
    print("\n⚠️  Testing AI Coach in French (may take 10-30 seconds)...")
    tester.test_coach_analyze_french()
    
    # Test workout creation
    tester.test_create_workout()
    
    # Test messages
    tester.test_get_messages()
    
    # Test new coach memory features
    print("\n🧠 Testing Coach Memory Features...")
    
    # Test conversation history
    tester.test_coach_history()
    
    # Test deep analysis with workout
    if workouts_success and workouts_data and len(workouts_data) > 0:
        first_workout_id = workouts_data[0].get('id')
        if first_workout_id:
            print(f"\n⚠️  Testing Deep Analysis for workout {first_workout_id} (may take 10-30 seconds)...")
            tester.test_deep_analysis(first_workout_id)
    
    # Test memory persistence
    print("\n⚠️  Testing Coach Memory Persistence (may take 20-40 seconds)...")
    tester.test_coach_memory_persistence()
    
    # Test clear history (do this last)
    print("\n🗑️  Testing Clear History...")
    tester.test_clear_coach_history()
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.failed_tests:
        print("\n❌ Failed Tests:")
        for failure in tester.failed_tests:
            error_msg = failure.get('error', f"Status {failure.get('actual')} != {failure.get('expected')}")
            print(f"   - {failure['test']}: {error_msg}")
    
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())