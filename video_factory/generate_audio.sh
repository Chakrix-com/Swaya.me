#!/bin/bash
# generate_audio.sh
mkdir -p assets/audio/en

API_KEY="REDACTED_ELEVENLABS_API_KEY"
VOICE_ID="qagSPKU8Dk70OM7QuI3u"

generate_scene_audio() {
  local scene_id=$1
  local text=$2
  echo "Generating audio for $scene_id..."
  curl -s -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID" \
       -H "Accept: audio/mpeg" \
       -H "Content-Type: application/json" \
       -H "xi-api-key: $API_KEY" \
       -d "{
         \"text\": \"$text\",
         \"model_id\": \"eleven_multilingual_v2\",
         \"voice_settings\": {
           \"stability\": 0.5,
           \"similarity_boost\": 0.5
         }
       }" > "assets/audio/en/$scene_id.mp3"
}

generate_scene_audio "scene1" "You've been there. A presentation where everyone is looking at their phones instead of you. What if you could turn that distraction into action?"
generate_scene_audio "scene2" "Meet Swaya dot me. The interactive platform for modern teams, teachers, and creators. Host live quizzes, run async exams, or simple polls—all in one place."
generate_scene_audio "scene3" "Create in seconds with AI assistance. And the magic? Zero friction. No apps to download. No logins for your audience. Just scan, join, and play."
generate_scene_audio "scene4" "Watch the energy in the room shift. From a team of ten to a stadium of ten thousand, Swaya dot me scales with you in real-time."
generate_scene_audio "scene5" "Language shouldn't be a barrier. With support for 11 global languages, Swaya dot me ensures every voice is heard, anywhere on earth."
generate_scene_audio "scene6" "Export your results to PDF, Excel, or PowerPoint instantly. Host your first session for free today at Swaya dot me."
