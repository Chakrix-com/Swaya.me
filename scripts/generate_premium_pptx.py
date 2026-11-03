import os
import requests
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# --- THEME COLORS ---
NAVY = RGBColor(15, 23, 42)
INDIGO = RGBColor(99, 102, 241)
TEAL = RGBColor(45, 212, 191)
WHITE = RGBColor(255, 255, 255)
SLATE = RGBColor(148, 163, 184)
PINK = RGBColor(244, 114, 182)
BLUE = RGBColor(96, 165, 250)
AMBER = RGBColor(251, 191, 36)

IMAGES = {
    "cover": "https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=1200&auto=format&fit=crop", # Abstract tech
    "audience": "https://images.unsplash.com/photo-1515187029135-18ee286d815b?q=80&w=1200&auto=format&fit=crop", # Meeting/Conference
    "qr": "https://images.unsplash.com/photo-1614850523296-d8c1af93d400?q=80&w=1200&auto=format&fit=crop", # QR/Mobile
    "ai": "https://images.unsplash.com/photo-1620712943543-bcc4628c6757?q=80&w=1200&auto=format&fit=crop", # AI/Digital
    "security": "https://images.unsplash.com/photo-1563986768609-322da13575f3?q=80&w=1200&auto=format&fit=crop", # Shield/Security
}

def download_img(url, name):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(name, 'wb') as f: f.write(r.content)
            return True
    except: pass
    return False

def setup_slide(slide):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    # Top accent line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.08))
    line.fill.solid(); line.fill.fore_color.rgb = INDIGO; line.line.fill.background()

def create_premium_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # --- SLIDE 1: COVER ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    setup_slide(slide)
    if download_img(IMAGES["cover"], "cover.jpg"):
        slide.shapes.add_picture("cover.jpg", Inches(7), 0, height=Inches(7.5))
    
    title = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(6), Inches(2))
    p = title.text_frame.paragraphs[0]
    p.text = "Swaya.me"
    p.font.size = Pt(84); p.font.bold = True; p.font.color.rgb = INDIGO
    
    sub = slide.shapes.add_textbox(Inches(0.6), Inches(4), Inches(6), Inches(1))
    p = sub.text_frame.paragraphs[0]
    p.text = "Engage. Evaluate. Empower.\nThe Future of Live Audience Interaction"
    p.font.size = Pt(24); p.font.color.rgb = SLATE

    # --- SLIDE 2: THE PAIN ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    setup_slide(slide)
    
    h = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(1))
    h.text_frame.text = "The 'Zoned Out' Audience"
    h.text_frame.paragraphs[0].font.size = Pt(44); h.text_frame.paragraphs[0].font.bold = True; h.text_frame.paragraphs[0].font.color.rgb = WHITE
    
    if download_img(IMAGES["audience"], "audience.jpg"):
        slide.shapes.add_picture("audience.jpg", Inches(0.5), Inches(2), width=Inches(6))
    
    bullets = ["70% of webinar attendees are multitasking.", "Engagement is at an all-time low.", "Expensive tools, complicated logins, no privacy."]
    txt = slide.shapes.add_textbox(Inches(7), Inches(2), Inches(5.5), Inches(4))
    for b in bullets:
        p = txt.text_frame.add_paragraph(); p.text = f"• {b}"; p.font.size = Pt(28); p.font.color.rgb = SLATE; p.space_after = Pt(20)

    # --- SLIDE 3: THE SOLUTION (Infographic) ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    setup_slide(slide)
    h = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(1))
    h.text_frame.text = "Swaya.me: One Platform, Infinite Uses"
    h.text_frame.paragraphs[0].font.size = Pt(44); h.text_frame.paragraphs[0].font.bold = True; h.text_frame.paragraphs[0].font.color.rgb = WHITE

    cards = [
        ("Live Quizzes", "Real-time leaderboard shifting.", PINK),
        ("Live Polls", "Instant visual feedback.", BLUE),
        ("Word Clouds", "Crowd-sourced brainstorming.", TEAL),
        ("Secure Exams", "AI-proctored certification.", AMBER)
    ]
    for i, (name, desc, color) in enumerate(cards):
        x = Inches(0.5 + i*3.2)
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(2.5), Inches(2.8), Inches(3.5))
        shape.fill.solid(); shape.fill.fore_color.rgb = RGBColor(30, 41, 59); shape.line.color.rgb = color; shape.line.width = Pt(2)
        
        t = slide.shapes.add_textbox(x, Inches(3), Inches(2.8), Inches(1))
        p = t.text_frame.paragraphs[0]; p.text = name; p.font.bold = True; p.font.size = Pt(24); p.font.color.rgb = color; p.alignment = PP_ALIGN.CENTER
        p2 = t.text_frame.add_paragraph(); p2.text = desc; p2.font.size = Pt(14); p2.font.color.rgb = SLATE; p2.alignment = PP_ALIGN.CENTER

    # --- SLIDE 4: ZERO FRICTION ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    setup_slide(slide)
    if download_img(IMAGES["qr"], "qr.jpg"):
        slide.shapes.add_picture("qr.jpg", Inches(0.5), Inches(1.5), height=Inches(5))
    
    t = slide.shapes.add_textbox(Inches(7), Inches(2.5), Inches(6), Inches(2))
    p = t.text_frame.paragraphs[0]; p.text = "One Scan.\nZero Login."; p.font.size = Pt(64); p.font.bold = True; p.font.color.rgb = TEAL
    p2 = t.text_frame.add_paragraph(); p2.text = "No apps. No sign-ups. Join in 5 seconds."; p2.font.size = Pt(24); p2.font.color.rgb = SLATE

    # --- SLIDE 5: AI POWER ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    setup_slide(slide)
    if download_img(IMAGES["ai"], "ai.jpg"):
        slide.shapes.add_picture("ai.jpg", Inches(7), Inches(1.5), width=Inches(5.5))
    
    h = slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(6), Inches(1))
    h.text_frame.text = "AI is Your Co-Pilot"
    h.text_frame.paragraphs[0].font.size = Pt(44); h.text_frame.paragraphs[0].font.bold = True; h.text_frame.paragraphs[0].font.color.rgb = WHITE
    
    txt = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(6), Inches(4))
    points = ["Auto-Generate quizzes from any prompt.", "Auto-Analyze session results instantly.", "Auto-Moderate Word Clouds for safety."]
    for p_text in points:
        p = txt.text_frame.add_paragraph(); p.text = f"✓ {p_text}"; p.font.size = Pt(22); p.font.color.rgb = SLATE; p.space_after = Pt(15)

    # --- SLIDE 6: SECURITY ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    setup_slide(slide)
    if download_img(IMAGES["security"], "security.jpg"):
        slide.shapes.add_picture("security.jpg", Inches(0.5), Inches(1.5), width=Inches(5.5))
    
    t = slide.shapes.add_textbox(Inches(6.5), Inches(2), Inches(6), Inches(3))
    p = t.text_frame.paragraphs[0]; p.text = "Trust in Every Test"; p.font.size = Pt(44); p.font.bold = True; p.font.color.rgb = AMBER
    p2 = t.text_frame.add_paragraph(); p2.text = "• AI Webcam Proctoring\n• OTP Identity Verification\n• Secure, Timed Session Control\n• Automated Professional PDF Reports"; p2.font.size = Pt(22); p2.font.color.rgb = SLATE; p2.line_spacing = 1.5

    # --- SLIDE 7: ARCHITECTURE ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    setup_slide(slide)
    h = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(1))
    h.text_frame.text = "Architected for Performance"
    h.text_frame.paragraphs[0].font.size = Pt(44); h.text_frame.paragraphs[0].font.bold = True; h.text_frame.paragraphs[0].font.color.rgb = WHITE
    
    # Code box
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1), Inches(2), Inches(11.3), Inches(4))
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(10, 15, 30); box.line.color.rgb = INDIGO
    t = slide.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11), Inches(3.5))
    p = t.text_frame.paragraphs[0]; p.text = "// THE SWAYA STACK"; p.font.color.rgb = TEAL; p.font.name = "Courier New"; p.font.size = Pt(20)
    p2 = t.text_frame.add_paragraph(); p2.text = "FastAPI + Async SQLAlchemy (Python 3.10+)\nRedis Pub/Sub for Event Distribution\nServer-Sent Events (SSE) for Real-time Delivery\nMulti-tenant Data Isolation by Design"; p2.font.color.rgb = WHITE; p2.font.name = "Courier New"; p2.font.size = Pt(24); p2.line_spacing = 1.4

    # --- SLIDE 8: GLOBAL ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    setup_slide(slide)
    h = slide.shapes.add_textbox(Inches(0), Inches(2.5), Inches(13.333), Inches(2))
    p = h.text_frame.paragraphs[0]; p.text = "11 Languages. 100% Open Source."; p.font.size = Pt(64); p.font.bold = True; p.alignment = PP_ALIGN.CENTER; p.font.color.rgb = WHITE
    p2 = h.text_frame.add_paragraph(); p2.text = "Hindi • Tamil • Telugu • Kannada • Bengali • Gujarati\nSpanish • French • German • Russian • English"; p2.font.size = Pt(28); p2.alignment = PP_ALIGN.CENTER; p2.font.color.rgb = TEAL

    # --- SLIDE 9: CALL TO ACTION ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    setup_slide(slide)
    t = slide.shapes.add_textbox(Inches(0), Inches(2), Inches(13.333), Inches(2))
    p = t.text_frame.paragraphs[0]; p.text = "Start Your First Session"; p.font.size = Pt(72); p.font.bold = True; p.alignment = PP_ALIGN.CENTER; p.font.color.rgb = INDIGO
    p2 = t.text_frame.add_paragraph(); p2.text = "www.swaya.me"; p2.font.size = Pt(48); p2.alignment = PP_ALIGN.CENTER; p2.font.color.rgb = WHITE
    
    p3 = t.text_frame.add_paragraph(); p3.text = "\nClone the repo. Self-host today. Engage your world."; p3.font.size = Pt(20); p3.alignment = PP_ALIGN.CENTER; p3.font.color.rgb = SLATE

    # Save and Clean
    prs.save("_private/marketing/decks/Swaya_Final_Presentation.pptx")
    for f in os.listdir("."):
        if f.endswith(".jpg"): os.remove(f)
    print("Deck created: _private/marketing/decks/Swaya_Final_Presentation.pptx")

if __name__ == "__main__":
    create_premium_deck()
