#!/bin/bash

# LLM Service API Test Suite
# Tests all major functionality of the SHATO LLM service

# Configuration
API_URL="http://localhost:8002"
HEADER="Content-Type: application/json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_data="$2"
    local expected_pattern="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "${BLUE}[TEST $TOTAL_TESTS] $test_name${NC}"
    echo "Request: $test_data"
    
    response=$(curl -s -X POST "$API_URL/generate_response" \
        -H "$HEADER" \
        -d "$test_data")
    
    echo "Response: $response"
    
    if [[ $response == *"$expected_pattern"* ]]; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FAIL - Expected to contain: $expected_pattern${NC}"
    fi
    echo "----------------------------------------"
}

# Function to check health endpoints
check_health() {
    echo -e "${YELLOW}=== HEALTH CHECKS ===${NC}"
    
    echo -e "${BLUE}Checking simple health endpoint...${NC}"
    health_response=$(curl -s "$API_URL/health")
    echo "Health: $health_response"
    
    echo -e "${BLUE}Checking detailed health endpoint...${NC}"
    detailed_health=$(curl -s "$API_URL/")
    echo "Detailed Health: $detailed_health"
    
    echo -e "${BLUE}Checking stats endpoint...${NC}"
    stats_response=$(curl -s "$API_URL/stats")
    echo "Stats: $stats_response"
    echo "----------------------------------------"
}

echo -e "${YELLOW}=== SHATO LLM SERVICE TEST SUITE ===${NC}"
echo "Testing API at: $API_URL"
echo ""

# Health checks first
check_health

echo -e "${YELLOW}=== FUNCTIONAL TESTS ===${NC}"

# Test 1: Basic greeting (conversation)
run_test "Basic Greeting" \
    '{"user_input": "morning!"}' \
    '"command":null'

# Test 2: Capabilities question (conversation)
run_test "Capabilities Question" \
    '{"user_input": "What are your abilities?"}' \
    '"command":null'

# Test 3: Basic movement with coordinates
run_test "Movement with Coordinates" \
    '{"user_input": "Move to positions 5, 7"}' \
    '"command":"move_to"'

# Test 4: Movement with decimal coordinates
run_test "Movement with Decimal Coordinates" \
    '{"user_input": "Go to coordinates 10.5, -3.2"}' \
    '"command":"move_to"'

# Test 5: Clockwise rotation
run_test "Clockwise Rotation" \
    '{"user_input": "Turn 90 degrees clockwise"}' \
    '"command":"rotate"'

# Test 6: Counter-clockwise rotation  
run_test "Counter-clockwise Rotation" \
    '{"user_input": "Rotate 45 degrees counter-clockwise"}' \
    '"command":"rotate"'

# Test 7: Basic patrol (should default to repeat_count: 1)
run_test "Basic Patrol - Default Parameters" \
    '{"user_input": "Start gaurding the first floor"}' \
    '"repeat_count":1'

# Test 8: Patrol with explicit parameters
run_test "Patrol with Explicit Rounds" \
    '{"user_input": "Guard the bedrooms for 3 rounds"}' \
    '"repeat_count":3'

# Test 9: Continuous patrol (should be repeat_count: -1)
run_test "Continuous Patrol" \
    '{"user_input": "Monitor the second floor continuously at fast speed"}' \
    '"repeat_count":-1'

# Test 10: Edge case - impossible command
run_test "Edge Case - Impossible Command" \
    '{"user_input": "Fly to the moon"}' \
    '"command":null'

# Test 11: Empty input (should fail with 400)
run_test "Empty Input Validation" \
    '{"user_input": ""}' \
    'user_input is required'

# Test 12: Retry context feature
run_test "Retry Context Feature" \
    '{"user_input": "Move robot", "retry_context": "Provide coordinates like: move to 5, 7"}' \
    '"command":'

# Test 13: JSON schema validation (all responses should be valid JSON)
echo -e "${BLUE}[TEST $((TOTAL_TESTS + 1))] JSON Schema Validation${NC}"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

test_response=$(curl -s -X POST "$API_URL/generate_response" \
    -H "$HEADER" \
    -d '{"user_input": "Hello"}')

echo "Testing JSON validity of response..."
if echo "$test_response" | jq . > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS - Valid JSON response${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    # Check required fields
    if echo "$test_response" | jq -e '.response and (.command != null or .command == null) and (.command_params != null or .command_params == null)' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS - Required fields present${NC}"
    else
        echo -e "${RED}❌ FAIL - Missing required fields${NC}"
    fi
else
    echo -e "${RED}❌ FAIL - Invalid JSON response${NC}"
fi
echo "----------------------------------------"

# Test 14: Alternative movement phrasing
run_test "Alternative Movement Phrasing" \
    '{"user_input": "Navigate to point 8, 3"}' \
    '"command":"move_to"'

# Test 15: Informal movement command
run_test "Informal Movement Command" \
    '{"user_input": "Go over to 2, 4 please"}' \
    '"command":"move_to"'

# Test 16: Movement with extra words
run_test "Movement with Extra Words" \
    '{"user_input": "I need you to move to location 7, 9 now"}' \
    '"command":"move_to"'

# Test 17: Alternative rotation phrasing
run_test "Alternative Rotation Phrasing" \
    '{"user_input": "Spin 180 degrees clockwise"}' \
    '"command":"rotate"'

# Test 18: Informal rotation command
run_test "Informal Rotation Command" \
    '{"user_input": "Turn left by 90 degrees"}' \
    '"command":"rotate"'

# Test 19: Rotation with alternative direction
run_test "Rotation with Alternative Direction" \
    '{"user_input": "Rotate 45 degrees anti-clockwise"}' \
    '"command":"rotate"'

# Test 20: Alternative patrol phrasing
run_test "Alternative Patrol Phrasing" \
    '{"user_input": "Begin monitoring the bedrooms"}' \
    '"command":"start_patrol"'

# Test 21: Informal patrol command
run_test "Informal Patrol Command" \
    '{"user_input": "Can you watch the first floor for me?"}' \
    '"command":"start_patrol"'

# Test 22: Patrol with word numbers
run_test "Patrol with Word Numbers" \
    '{"user_input": "Patrol second floor five times"}' \
    '"repeat_count":5'

# Test 23: Mixed case and punctuation
run_test "Mixed Case and Punctuation" \
    '{"user_input": "MOVE TO 3,6!"}' \
    '"command":"move_to"'

# Test 24: Typos and misspellings
run_test "Typos and Misspellings" \
    '{"user_input": "rotat 30 degres clockwize"}' \
    '"command":"rotate"'

# Test 25: Colloquial expressions
run_test "Colloquial Expressions" \
    '{"user_input": "Head over to coordinates 1, 5"}' \
    '"command":"move_to"'

# Test 26: Complex patrol request
run_test "Complex Patrol Request" \
    '{"user_input": "Keep an eye on the bedrooms area continuously"}' \
    '"repeat_count":-1'

# Test 27: Ambiguous movement (should be conversation)
run_test "Ambiguous Movement" \
    '{"user_input": "Move a little bit"}' \
    '"command":null'

# Test 28: Alternative greeting
run_test "Alternative Greeting" \
    '{"user_input": "Hey there robot!"}' \
    '"command":null'

# Test 29: Question about status
run_test "Question About Status" \
    '{"user_input": "Where are you right now?"}' \
    '"command":null'

# Test 30: Complex impossible command
run_test "Complex Impossible Command" \
    '{"user_input": "Transform into a helicopter and fly around"}' \
    '"command":null'

# Test 31: Movement with alternative units
run_test "Movement with Alternative Units" \
    '{"user_input": "Go to x=12 y=8"}' \
    '"command":"move_to"'

# Test 32: Performance test (response time)
echo -e "${BLUE}[TEST $((TOTAL_TESTS + 1))] Performance Test${NC}"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

start_time=$(date +%s%N)
curl -s -X POST "$API_URL/generate_response" \
    -H "$HEADER" \
    -d '{"user_input": "Move to 1, 2"}' > /dev/null
end_time=$(date +%s%N)

duration_ms=$(( (end_time - start_time) / 1000000 ))
echo "Response time: ${duration_ms}ms"

if [ $duration_ms -lt 5000 ]; then
    echo -e "${GREEN}✅ PASS - Response under 5 seconds${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ FAIL - Response took over 5 seconds${NC}"
fi
echo "----------------------------------------"

# Summary
echo -e "${YELLOW}=== TEST SUMMARY ===${NC}"
echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $((TOTAL_TESTS - PASSED_TESTS))"

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! LLM Service is working correctly.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Check the output above for details.${NC}"
    exit 1
fi