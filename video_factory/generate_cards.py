from PIL import Image, ImageDraw, ImageFont
import os

def create_ui_card(text, subtext, output_name):
    bg = Image.open("assets/title_bg.png").convert("RGBA")
    bg = bg.resize((1920, 1080), Image.LANCZOS)
    draw = ImageDraw.Draw(bg)
    
    try:
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 80)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 50)
    except:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        
    logo = Image.open("assets/logo.png").convert("RGBA")
    logo = logo.resize((400, 100), Image.LANCZOS)
    bg.paste(logo, (1920//2 - 200, 1080//2 - 250), logo)
    
    # Modern text measurement
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font_main)
    w, h = right - left, bottom - top
    draw.text(((1920-w)/2, 1080//2 + 20), text, font=font_main, fill=(255, 255, 255, 255))
    
    left, top, right, bottom = draw.textbbox((0, 0), subtext, font=font_sub)
    sw, sh = right - left, bottom - top
    draw.text(((1920-sw)/2, 1080//2 + 130), subtext, font=font_sub, fill=(180, 180, 255, 255))
    
    bg.save(f"assets/{output_name}")
    print(f"Created {output_name}")

if __name__ == "__main__":
    create_ui_card("Interactive Sessions Redefined", "www.swaya.me", "intro_card.png")
    create_ui_card("Engagement Made Effortless", "www.swaya.me", "outro_card.png")
