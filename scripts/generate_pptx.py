import os
import requests
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

def create_presentation():
    prs = Presentation()
    
    # helper for slide background
    def set_slide_background(slide, color):
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = color

    # helper to add a title and subtitle
    def add_title_slide(prs, title_text, subtitle_text):
        slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)
        set_slide_background(slide, RGBColor(15, 23, 42)) # Dark blue background
        
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        
        title.text = title_text
        subtitle.text = subtitle_text
        
        # Style
        title.text_frame.paragraphs[0].font.color.rgb = RGBColor(99, 102, 241) # Primary Indigo
        title.text_frame.paragraphs[0].font.bold = True
        subtitle.text_frame.paragraphs[0].font.color.rgb = RGBColor(148, 163, 184) # Light Slate
        return slide

    # helper for content slides
    def add_content_slide(prs, title_text, bullet_points, image_url=None):
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        set_slide_background(slide, RGBColor(15, 23, 42))
        
        title = slide.shapes.title
        title.text = title_text
        title.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
        
        body = slide.placeholders[1]
        tf = body.text_frame
        tf.text = bullet_points[0] if bullet_points else ""
        for point in bullet_points[1:]:
            p = tf.add_paragraph()
            p.text = point
            p.level = 0
            p.font.color.rgb = RGBColor(203, 213, 225)
            
        if image_url:
            try:
                img_data = requests.get(image_url).content
                with open("temp_img.jpg", "wb") as f:
                    f.write(img_data)
                slide.shapes.add_picture("temp_img.jpg", Inches(6), Inches(2), height=Inches(4))
                os.remove("temp_img.jpg")
            except Exception as e:
                print(f"Could not load image: {e}")
        
        return slide

    # SLIDE 1
    add_title_slide(prs, "Swaya.me", "Engage. Evaluate. Empower.\nThe Future of Live Engagement")

    # SLIDE 2
    add_content_slide(prs, "The 'Zoned Out' Audience", [
        "70% of webinar attendees are multitasking.",
        "Traditional classrooms are losing the battle for attention.",
        "Existing tools are expensive black boxes with no privacy."
    ])

    # SLIDE 3
    add_content_slide(prs, "Meet Swaya.me", [
        "Quizzes: Real-time competition with leaderboards.",
        "Polls: Instant crowd feedback and visualization.",
        "Exams: Secure, proctored certification with integrity scoring."
    ])

    # SLIDE 4
    add_content_slide(prs, "One Scan. Zero Login.", [
        "No app downloads required.",
        "No account creation for participants.",
        "Join in under 5 seconds via QR code."
    ])

    # SLIDE 5
    add_content_slide(prs, "AI is your Co-Pilot", [
        "Auto-Generate: Build quizzes from any prompt in seconds.",
        "Auto-Analyze: Performance summaries and AI insights.",
        "Auto-Moderate: Smart filtering for professional Word Clouds."
    ])

    # SLIDE 6
    add_content_slide(prs, "Beyond the Fun", [
        "Webcam Proctoring: AI-powered snapshots for integrity.",
        "OTP Verification: Frictionless identity confirmation.",
        "Integrity Reports: Professional PDF results with audit scoring."
    ])

    # SLIDE 7
    add_content_slide(prs, "Architected for Scale", [
        "Backend: FastAPI + Async Python.",
        "Real-time: Server-Sent Events (SSE).",
        "Multi-tenant: Total data isolation."
    ])

    # SLIDE 8
    add_content_slide(prs, "Global & Open", [
        "11 Languages Supported.",
        "100% Open Source (Apache 2.0).",
        "Self-hostable: Total data sovereignty."
    ])

    # SLIDE 9
    add_content_slide(prs, "Where Swaya Shines", [
        "Events: Conferences with 500+ live participants.",
        "Schools: Safe, proctored classroom testing.",
        "Corporate: Instant HR feedback and training."
    ])

    # SLIDE 10
    add_title_slide(prs, "Start Your First Session", "www.swaya.me\nClone the repo. Self-host today. Engage your world.")

    output_path = "_private/marketing/decks/Swaya_General_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation saved to {output_path}")

if __name__ == "__main__":
    create_presentation()
