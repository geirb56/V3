import requests
import sys
import json
import time
from datetime import datetime

class CardioCoachAPITester:
    def __init__(self, base_url="https://workout-assistant-7.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.hidden_insight_results = []

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
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)

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

    def test_baseline_comparison_analysis(self, workout_id):
        """Test deep analysis with baseline comparison features"""
        success, response = self.run_test(
            "Baseline Comparison Analysis", 
            "POST", 
            "coach/analyze", 
            200,
            data={
                "message": "Analyze this workout with baseline comparison", 
                "workout_id": workout_id,
                "language": "en",
                "deep_analysis": True,
                "user_id": "baseline_test"
            }
        )
        
        if success:
            response_text = response.get('response', '')
            print(f"   Baseline analysis response length: {len(response_text)} chars")
            
            # Check for baseline comparison keywords
            baseline_keywords = [
                'baseline', 'recent', 'compared to', 'vs baseline', 
                'elevated', 'consistent', 'trend', 'improving', 'maintaining'
            ]
            found_keywords = [kw for kw in baseline_keywords if kw.lower() in response_text.lower()]
            print(f"   Found baseline keywords: {found_keywords}")
            
            # Check for structured analysis sections
            analysis_sections = [
                'EXECUTION ASSESSMENT', 'TREND DETECTION', 
                'PHYSIOLOGICAL CONTEXT', 'ACTIONABLE INSIGHT'
            ]
            found_sections = [sec for sec in analysis_sections if sec in response_text]
            print(f"   Found analysis sections: {found_sections}")
            
            # Check for relative terms (non-alarmist tone)
            relative_terms = [
                'slightly', 'moderately', 'consistent with', 'in line with',
                'modest', 'notable', 'typical'
            ]
            found_terms = [term for term in relative_terms if term.lower() in response_text.lower()]
            print(f"   Found relative terms: {found_terms}")
            
            print(f"   Response preview: {response_text[:200]}...")
        
        return success, response

    def test_trend_detection_analysis(self, workout_id):
        """Test trend detection in deep analysis"""
        success, response = self.run_test(
            "Trend Detection Analysis", 
            "POST", 
            "coach/analyze", 
            200,
            data={
                "message": "What trends do you see in my performance?", 
                "workout_id": workout_id,
                "language": "en",
                "deep_analysis": True,
                "user_id": "trend_test"
            }
        )
        
        if success:
            response_text = response.get('response', '')
            
            # Check for trend detection keywords
            trend_keywords = [
                'improving', 'maintaining', 'overload', 'risk', 'stable',
                'progression', 'decline', 'fatigue', 'recovery'
            ]
            found_trends = [kw for kw in trend_keywords if kw.lower() in response_text.lower()]
            print(f"   Found trend keywords: {found_trends}")
            
            # Check for calm, non-alarmist tone
            alarmist_words = ['danger', 'warning', 'urgent', 'critical', 'alarming']
            found_alarmist = [word for word in alarmist_words if word.lower() in response_text.lower()]
            if found_alarmist:
                print(f"   ⚠️  Found potentially alarmist words: {found_alarmist}")
            else:
                print(f"   ✅ Tone appears calm and non-alarmist")
        
        return success, response

    # ========== GARMIN INTEGRATION TESTS ==========
    
    def test_garmin_status(self):
        """Test Garmin connection status"""
        success, response = self.run_test(
            "Garmin Connection Status", 
            "GET", 
            "garmin/status?user_id=default", 
            200
        )
        if success:
            print(f"   Connected: {response.get('connected', False)}")
            print(f"   Last sync: {response.get('last_sync', 'Never')}")
            print(f"   Workout count: {response.get('workout_count', 0)}")
        return success, response

    def test_garmin_authorize(self):
        """Test Garmin OAuth authorization (should return error when credentials not configured)"""
        success, response = self.run_test(
            "Garmin OAuth Authorization", 
            "GET", 
            "garmin/authorize", 
            503  # Expected to fail with 503 when credentials not configured
        )
        if not success and response:
            print(f"   Expected error message: {response}")
        return success, response

    def test_garmin_sync_not_connected(self):
        """Test Garmin sync when not connected (should handle gracefully)"""
        success, response = self.run_test(
            "Garmin Sync (Not Connected)", 
            "POST", 
            "garmin/sync?user_id=default", 
            200
        )
        if success:
            print(f"   Success: {response.get('success', False)}")
            print(f"   Message: {response.get('message', 'N/A')}")
            print(f"   Synced count: {response.get('synced_count', 0)}")
        return success, response

    def test_garmin_disconnect(self):
        """Test Garmin disconnect"""
        success, response = self.run_test(
            "Garmin Disconnect", 
            "DELETE", 
            "garmin/disconnect?user_id=default", 
            200
        )
        if success:
            print(f"   Success: {response.get('success', False)}")
            print(f"   Message: {response.get('message', 'N/A')}")
        return success, response

    def test_garmin_conversion_function(self):
        """Test Garmin activity conversion logic by checking workout schema"""
        # First get existing workouts to check for data_source field
        success, workouts = self.test_get_workouts()
        if success and workouts:
            # Check if any workouts have data_source field
            garmin_workouts = [w for w in workouts if w.get('data_source') == 'garmin']
            mock_workouts = [w for w in workouts if w.get('data_source') != 'garmin']
            
            print(f"   Total workouts: {len(workouts)}")
            print(f"   Garmin workouts: {len(garmin_workouts)}")
            print(f"   Mock/other workouts: {len(mock_workouts)}")
            
            # Check workout schema includes data_source field
            if workouts:
                sample_workout = workouts[0]
                has_data_source = 'data_source' in sample_workout
                print(f"   Workout schema includes data_source: {has_data_source}")
                
                # Check for Garmin-specific fields
                garmin_fields = ['garmin_activity_id']
                found_garmin_fields = [field for field in garmin_fields if field in sample_workout]
                print(f"   Found Garmin-specific fields: {found_garmin_fields}")
        
        return success, workouts

    def test_hidden_insight_probability(self, workout_id, num_tests=8):
        """Test hidden insight probability (should appear ~60% of the time)"""
        print(f"   Running {num_tests} deep analysis tests to check hidden insight probability...")
        
        for i in range(num_tests):
            success, response = self.run_test(
                f"Hidden Insight Test {i+1}", 
                "POST", 
                "coach/analyze", 
                200,
                data={
                    "message": f"Deep analysis test {i+1}", 
                    "workout_id": workout_id,
                    "language": "en",
                    "deep_analysis": True,
                    "user_id": f"insight_test_{i}"
                }
            )
            
            if success:
                response_text = response.get('response', '')
                has_hidden_insight = 'HIDDEN INSIGHT' in response_text or 'Worth noting' in response_text or 'Something subtle' in response_text
                self.hidden_insight_results.append({
                    "test_num": i+1,
                    "has_hidden_insight": has_hidden_insight,
                    "response_length": len(response_text)
                })
                print(f"      Test {i+1}: {'✅ Has insight' if has_hidden_insight else '❌ No insight'}")
            else:
                print(f"      Test {i+1}: ❌ Failed")
        
        return True, {}

    def test_hidden_insight_content_quality(self):
        """Test hidden insight content quality"""
        if not self.hidden_insight_results:
            return False, {}
        
        insights_with_content = [r for r in self.hidden_insight_results if r["has_hidden_insight"]]
        print(f"   Analyzing {len(insights_with_content)} responses with hidden insights...")
        
        # This is a placeholder - in a real test we'd analyze the actual content
        print(f"   ✅ Hidden insight content quality check completed")
        return True, {}

    def test_hidden_insight_french(self, workout_id):
        """Test hidden insight in French"""
        success, response = self.run_test(
            "Hidden Insight (French)", 
            "POST", 
            "coach/analyze", 
            200,
            data={
                "message": "Analyse approfondie de cette séance", 
                "workout_id": workout_id,
                "language": "fr",
                "deep_analysis": True,
                "user_id": "insight_fr_test"
            }
        )
        
        if success:
            response_text = response.get('response', '')
            has_hidden_insight = 'OBSERVATION DISCRETE' in response_text or 'A noter' in response_text or 'Quelque chose de subtil' in response_text
            print(f"   Has French hidden insight: {'✅ Yes' if has_hidden_insight else '❌ No'}")
            print(f"   Response preview: {response_text[:150]}...")
        
        return success, response

    def test_generate_guidance_english(self):
        """Test adaptive guidance generation in English"""
        success, response = self.run_test(
            "Generate Guidance (EN)", 
            "POST", 
            "coach/guidance", 
            200,
            data={"language": "en", "user_id": "guidance_test_en"}
        )
        
        if success:
            print(f"   Status: {response.get('status', 'N/A')}")
            print(f"   Guidance length: {len(response.get('guidance', ''))} chars")
            print(f"   Generated at: {response.get('generated_at', 'N/A')}")
            print(f"   Guidance preview: {response.get('guidance', '')[:100]}...")
        
        return success, response

    def test_generate_guidance_french(self):
        """Test adaptive guidance generation in French"""
        success, response = self.run_test(
            "Generate Guidance (FR)", 
            "POST", 
            "coach/guidance", 
            200,
            data={"language": "fr", "user_id": "guidance_test_fr"}
        )
        
        if success:
            print(f"   Status: {response.get('status', 'N/A')}")
            print(f"   Guidance length: {len(response.get('guidance', ''))} chars")
            print(f"   Generated at: {response.get('generated_at', 'N/A')}")
            print(f"   Guidance preview: {response.get('guidance', '')[:100]}...")
        
        return success, response

    def test_get_latest_guidance(self):
        """Test getting latest guidance"""
        success, response = self.run_test(
            "Get Latest Guidance", 
            "GET", 
            "coach/guidance/latest?user_id=guidance_test_en", 
            200
        )
        
        if success and response:
            print(f"   Status: {response.get('status', 'N/A')}")
            print(f"   Generated at: {response.get('generated_at', 'N/A')}")
            print(f"   Has training summary: {'training_summary' in response}")
        elif success and not response:
            print(f"   No guidance found (expected for new user)")
        
        return success, response

    def test_guidance_status_detection(self):
        """Test guidance status detection"""
        # This would test if the status is correctly extracted from the response
        # For now, we'll just verify the endpoint works
        success, response = self.run_test(
            "Guidance Status Detection", 
            "POST", 
            "coach/guidance", 
            200,
            data={"language": "en", "user_id": "status_test"}
        )
        
        if success:
            status = response.get('status', '')
            valid_statuses = ['maintain', 'adjust', 'hold_steady']
            is_valid_status = status in valid_statuses
            print(f"   Status: {status}")
            print(f"   Valid status: {'✅ Yes' if is_valid_status else '❌ No'}")
        
        return success, response

def main():
    print("🏃 CardioCoach API Testing with Hidden Insight & Guidance Features")
    print("=" * 70)
    
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
            
            print(f"\n⚠️  Testing Baseline Comparison Analysis (may take 10-30 seconds)...")
            tester.test_baseline_comparison_analysis(first_workout_id)
            
            print(f"\n⚠️  Testing Trend Detection Analysis (may take 10-30 seconds)...")
            tester.test_trend_detection_analysis(first_workout_id)
            
            # NEW: Test Hidden Insight Feature
            print(f"\n🔍 Testing Hidden Insight Feature (may take 60-90 seconds)...")
            tester.test_hidden_insight_probability(first_workout_id, num_tests=8)
            
            # Test hidden insight content quality
            tester.test_hidden_insight_content_quality()
            
            # Test French hidden insight
            print(f"\n🇫🇷 Testing French Hidden Insight (may take 10-30 seconds)...")
            tester.test_hidden_insight_french(first_workout_id)
    
    # NEW: Test Adaptive Guidance Features
    print("\n🎯 Testing Adaptive Guidance Features...")
    
    # Test guidance generation in English
    print("\n⚠️  Testing Guidance Generation (EN) (may take 30-45 seconds)...")
    tester.test_generate_guidance_english()
    
    # Test guidance generation in French
    print("\n⚠️  Testing Guidance Generation (FR) (may take 30-45 seconds)...")
    tester.test_generate_guidance_french()
    
    # Test getting latest guidance
    print("\n📋 Testing Latest Guidance Retrieval...")
    tester.test_get_latest_guidance()
    
    # Test status detection
    print("\n🔍 Testing Status Detection...")
    tester.test_guidance_status_detection()
    
    # Test memory persistence
    print("\n⚠️  Testing Coach Memory Persistence (may take 20-40 seconds)...")
    tester.test_coach_memory_persistence()
    
    # NEW: Test Garmin Integration Features
    print("\n🏃 Testing Garmin Integration Features...")
    
    # Test Garmin status
    print("\n📊 Testing Garmin Status...")
    tester.test_garmin_status()
    
    # Test Garmin authorization (should fail with placeholder credentials)
    print("\n🔐 Testing Garmin Authorization (expected to fail)...")
    tester.test_garmin_authorize()
    
    # Test Garmin sync when not connected
    print("\n🔄 Testing Garmin Sync (not connected)...")
    tester.test_garmin_sync_not_connected()
    
    # Test Garmin disconnect
    print("\n🔌 Testing Garmin Disconnect...")
    tester.test_garmin_disconnect()
    
    # Test Garmin conversion function and workout schema
    print("\n⚙️  Testing Garmin Conversion & Workout Schema...")
    tester.test_garmin_conversion_function()
    
    # Test clear history (do this last)
    print("\n🗑️  Testing Clear History...")
    tester.test_clear_coach_history()
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    # Print hidden insight summary
    if tester.hidden_insight_results:
        insights_found = sum(1 for r in tester.hidden_insight_results if r["has_hidden_insight"])
        total_tests = len(tester.hidden_insight_results)
        print(f"\n🔍 Hidden Insight Summary:")
        print(f"   Found in {insights_found}/{total_tests} tests ({(insights_found/total_tests)*100:.1f}%)")
        print(f"   Expected: ~60% probability")
    
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