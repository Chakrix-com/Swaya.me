API_KEY="REDACTED_ELEVENLABS_API_KEY"
VOICE_ID="qagSPKU8Dk70OM7QuI3u"
TEXT="Welcome to Swayame. Engagement made effortless."
curl -s -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID"      -H "Accept: audio/mpeg"      -H "Content-Type: application/json"      -H "xi-api-key: $API_KEY"      -d "{
       \"text\": \"$TEXT\",
       \"model_id\": \"eleven_multilingual_v2\"
     }" > test_pronunciation.mp3
