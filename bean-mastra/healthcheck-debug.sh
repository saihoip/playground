#!/bin/bash

# Debug version of healthcheck script with more verbose output
# Usage: sh healthcheck-debug.sh endpoints.txt

if [ "$#" -ne 1 ]; then
    echo "Usage: sh healthcheck-debug.sh endpoints.txt"
    exit 1
fi

ENDPOINT_FILE="$1"
TOKEN=""

echo "=== DEBUG HEALTHCHECK SCRIPT ==="
echo "Processing file: $ENDPOINT_FILE"
echo "================================="

# First pass: Look for the token endpoint and retrieve the access token.
echo ""
echo "PHASE 1: Token Acquisition"
echo "--------------------------"

while IFS= read -r line || [ -n "$line" ]; do
    # Skip empty lines and comments.
    [[ "$line" =~ ^#.*$ ]] && continue
    [[ -z "$line" ]] && continue

    name=$(echo "$line" | awk '{print $1}')
    method=$(echo "$line" | awk '{print $2}')
    url=$(echo "$line" | awk '{print $3}')
    options=$(echo "$line" | cut -d' ' -f4-)
    
    if [ "$name" = "token" ]; then
        echo "[$(date)] Found token endpoint: $name"
        echo "[$(date)] URL: $url"
        echo "[$(date)] Method: $method"
        echo "[$(date)] Options: $options"
        
        if echo "$options" | grep -q "\-k"; then
            CURL_INSECURE="-k"
            echo "[$(date)] Using insecure SSL (-k flag)"
        else
            CURL_INSECURE=""
        fi
        
        echo "[$(date)] Executing token request..."
        
        # Show the exact curl command
        echo "[$(date)] Curl command: curl $CURL_INSECURE --location --request POST \"$url\" --header 'Content-Type: application/x-www-form-urlencoded' --data-urlencode 'grant_type=client_credentials' --data-urlencode 'client_id=DWvSXeQmdbq3wgg/OStQ4gAemDzN' --data-urlencode 'client_secret=***'"
        
        token_response=$(curl $CURL_INSECURE --silent --location --request POST "$url" \
            --header 'Content-Type: application/x-www-form-urlencoded' \
            --data-urlencode 'grant_type=client_credentials' \
            --data-urlencode 'client_id=DWvSXeQmdbq3wgg/OStQ4gAemDzN' \
            --data-urlencode 'client_secret=mdYgc+Q5V+cDSUUqrOLFG+TZfxU2')
        
        echo "[$(date)] Raw token response: $token_response"
        
        # Extract the access_token from the JSON response using multiple methods
        if command -v jq >/dev/null 2>&1; then
            echo "[$(date)] Using jq for token extraction"
            TOKEN=$(echo "$token_response" | jq -r '.access_token // empty')
            echo "[$(date)] jq result: '$TOKEN'"
        else
            echo "[$(date)] jq not available, using regex"
        fi
        
        if [ -z "$TOKEN" ]; then
            echo "[$(date)] Trying regex method 1"
            TOKEN=$(echo "$token_response" | grep -o '"access_token"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
            echo "[$(date)] Regex method 1 result: '$TOKEN'"
        fi
        
        if [ -z "$TOKEN" ]; then
            echo "[$(date)] Trying regex method 2"
            TOKEN=$(echo "$token_response" | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
            echo "[$(date)] Regex method 2 result: '$TOKEN'"
        fi
        
        if [ -z "$TOKEN" ]; then
            echo "[$(date)] ERROR: Failed to extract access token"
            echo "[$(date)] Response was: $token_response"
            exit 1
        else
            echo "[$(date)] SUCCESS: Token extracted successfully"
            echo "[$(date)] Token (first 20 chars): ${TOKEN:0:20}..."
            echo "[$(date)] Token length: ${#TOKEN}"
        fi
        break
    fi
done < "$ENDPOINT_FILE"

# Second pass: Test endpoints
echo ""
echo "PHASE 2: Endpoint Testing"
echo "-------------------------"

while IFS= read -r line || [ -n "$line" ]; do
    [[ "$line" =~ ^#.*$ ]] && continue
    [[ -z "$line" ]] && continue

    name=$(echo "$line" | awk '{print $1}')
    method=$(echo "$line" | awk '{print $2}')
    url=$(echo "$line" | awk '{print $3}')
    options=$(echo "$line" | cut -d' ' -f4-)
    
    if [ "$name" = "token" ]; then
        continue
    fi

    echo ""
    echo "[$(date)] Testing endpoint: $name"
    echo "[$(date)] URL: $url"
    echo "[$(date)] Method: $method"
    echo "[$(date)] Options: $options"
    
    CURL_OPTS=""
    if echo "$options" | grep -q "\-k"; then
        CURL_OPTS="-k"
        echo "[$(date)] Using insecure SSL"
    fi
    
    AUTH_HEADER=""
    USE_AUTH=""
    if echo "$options" | grep -q "use_token"; then
        if [ -n "$TOKEN" ]; then
            AUTH_HEADER="Authorization: Bearer $TOKEN"
            USE_AUTH="--header"
            echo "[$(date)] Using token authentication"
            echo "[$(date)] Auth header: Authorization: Bearer ${TOKEN:0:20}..."
        else
            echo "[$(date)] WARNING: Endpoint requires token but no token available"
        fi
    else
        echo "[$(date)] No authentication required"
    fi

    # Build and show the curl command
    if [ "$method" = "GET" ]; then
        if [ -n "$USE_AUTH" ]; then
            echo "[$(date)] Curl command: curl $CURL_OPTS --header \"Authorization: Bearer [TOKEN]\" \"$url\""
            status=$(curl $CURL_OPTS --silent --output /dev/null --write-out "%{http_code}" \
                --header "$AUTH_HEADER" "$url")
        else
            echo "[$(date)] Curl command: curl $CURL_OPTS \"$url\""
            status=$(curl $CURL_OPTS --silent --output /dev/null --write-out "%{http_code}" \
                "$url")
        fi
    elif [ "$method" = "POST" ]; then
        if [ -n "$USE_AUTH" ]; then
            echo "[$(date)] Curl command: curl $CURL_OPTS --request POST --header \"Authorization: Bearer [TOKEN]\" \"$url\""
            status=$(curl $CURL_OPTS --silent --output /dev/null --write-out "%{http_code}" \
                --request POST --header "$AUTH_HEADER" "$url")
        else
            echo "[$(date)] Curl command: curl $CURL_OPTS --request POST \"$url\""
            status=$(curl $CURL_OPTS --silent --output /dev/null --write-out "%{http_code}" \
                --request POST "$url")
        fi
    else
        echo "[$(date)] Unknown method '$method' for endpoint '$name'"
        continue
    fi

    echo "[$(date)] HTTP Status: $status"
    
    if [ "$status" = "200" ] || [ "$status" = "403" ]; then
        echo "[$(date)] RESULT: SUCCESS - $name"
    else
        echo "[$(date)] RESULT: FAILED - $name (Status: $status)"
        
        # Additional debug for failed requests
        if [ "$status" = "401" ]; then
            echo "[$(date)] 401 indicates authentication failure"
            if echo "$options" | grep -q "use_token"; then
                echo "[$(date)] This endpoint uses token auth - check token validity"
            else
                echo "[$(date)] This endpoint doesn't use token auth - may need different credentials"
            fi
        fi
    fi
done < "$ENDPOINT_FILE"

echo ""
echo "=== DEBUG SUMMARY ==="
echo "Token available: $([ -n "$TOKEN" ] && echo "YES" || echo "NO")"
echo "Token length: ${#TOKEN}"
echo "====================="
