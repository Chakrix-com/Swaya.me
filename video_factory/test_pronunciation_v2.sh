API_KEY="REDACTED_ELEVENLABS_API_KEY"
VOICE_ID="qagSPKU8Dk70OM7QuI3u"
TEXT_1="Welcome to Swayam."
TEXT_2="Try Swayame."
curl -s -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID"      -H "Accept: audio/mpeg"      -H "Content-Type: application/json"      -H "xi-api-key: $API_KEY"      -d "{
       \"text\": \"$TEXT_1\",
       \"model_id\": \"eleven_multilingual_v2\"
     }" > swayam_test.mp3
curl -s -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID"      -H "Accept: audio/mpeg"      -H "Content-Type: application/json"      -H "xi-api-key: $API_KEY"      -d "{
       \"text\": \"$TEXT_2\",
       \"model_id\": \"eleven_multilingual_v2\"
     }" > swayame_test.mp3
