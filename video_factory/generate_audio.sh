#!/bin/bash
# generate_audio.sh
mkdir -p assets/audio/en

API_KEY="${ELEVENLABS_API_KEY:?Set ELEVENLABS_API_KEY env var before running}"
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
  sleep 2
}

# 1. Intro (Using "Swayam")
generate_scene_audio "scene1" "Let’s be honest. In the age of constant distraction, keeping your audience engaged is harder than ever. You’re speaking, but are they listening? Or are they lost in their screens? What if you could stop fighting the devices, and start using them? This is Swayam."

# 2. Modes Overview
generate_scene_audio "scene2" "Swayam is the all-in-one interactive platform designed to bridge the digital divide. Whether you’re an educator, a team lead, or an event organizer, Swayam turns passive spectators into active participants. One unified platform. Four powerful modes."

# 3. Live Quiz (Dual View)
generate_scene_audio "scene3" "First up: The Live Quiz. High energy. High stakes. Create competitive sessions with real-time scoring and instant leaderboards. Watch as the room lights up with every correct answer. It’s not just a test; it’s a game-changer."

# 4. Live Poll & Word Cloud (Dual View)
generate_scene_audio "scene4" "Need an opinion? Try the Live Poll. Gather instant feedback as it happens. Our dynamic Word Clouds grow and evolve in front of your eyes, filtered automatically for safety. Every voice is heard—instantly."

# 5. Exams and Offline
generate_scene_audio "scene5" "For deep assessments, our Exam mode offers self-paced, timed sessions perfect for remote Learning. And for physical spaces? Offline Polls let you place QR codes in lobbies or classrooms for a constant pulse of feedback."

# 6. Smart Creation & AI
generate_scene_audio "scene6" "And creation? Effortless. Don’t waste hours on manual entry. Our AI Generator turns a single prompt into a localized, professional quiz in under thirty seconds. MCQs with images, scales, and support for eleven global languages are at your fingertips."

# 7. Zero Friction & Scale
generate_scene_audio "scene7" "The best part? Zero friction. No apps, no logins, no barriers. Your audience scans, joins, and is ready in seconds. From a small team meeting to a massive stadium of ten thousand, Swayam scales with your ambition."

# 8. Export & Close
generate_scene_audio "scene8" "When the session is over, the insights remain. Export your results directly to PDF, Excel, or PowerPoint for professional reporting. Swayam. Engagement made effortless. Register for free today at Swayam."
