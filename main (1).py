import re
import os
from io import BytesIO
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

app = FastAPI(title="Arabic Font Generator Service")

# Allow CORS for easy integration with frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GlyphInput(BaseModel):
    name: str
    unicode: int
    pathData: str
    advanceWidth: int
    glyphType: Optional[str] = None
    ascent: Optional[int] = None
    descent: Optional[int] = None

class FontRequest(BaseModel):
    fontName: Optional[str] = "SmartArabicFont"
    glyphs: List[GlyphInput]

def parse_and_draw_svg(path_str: str, pen: TTGlyphPen):
    # Regex to tokenize standard SVG path commands and numeric coordinates
    tokens = re.findall(r'([a-zA-Z])|(-?\d*(?:\.\d+)?(?:[eE][-+]?\d+)?)', path_str)
    # Filter out empty tuples and clean
    tokens = [t[0] or t[1] for t in tokens if t[0] or t[1]]
    
    current_x = 0.0
    current_y = 0.0
    start_x = 0.0
    start_y = 0.0
    
    i = 0
    cmd = 'M'
    
    while i < len(tokens):
        token = tokens[i]
        if token.isalpha():
            cmd = token
            i += 1
            if i >= len(tokens) and cmd not in ('Z', 'z'):
                break
        
        try:
            if cmd == 'M':
                x = float(tokens[i])
                y = float(tokens[i+1])
                pen.moveTo((x, y))
                current_x, current_y = x, y
                start_x, start_y = x, y
                i += 2
            elif cmd == 'm':
                x = current_x + float(tokens[i])
                y = current_y + float(tokens[i+1])
                pen.moveTo((x, y))
                current_x, current_y = x, y
                start_x, start_y = x, y
                i += 2
            elif cmd == 'L':
                x = float(tokens[i])
                y = float(tokens[i+1])
                pen.lineTo((x, y))
                current_x, current_y = x, y
                i += 2
            elif cmd == 'l':
                x = current_x + float(tokens[i])
                y = current_y + float(tokens[i+1])
                pen.lineTo((x, y))
                current_x, current_y = x, y
                i += 2
            elif cmd == 'H':
                x = float(tokens[i])
                pen.lineTo((x, current_y))
                current_x = x
                i += 1
            elif cmd == 'h':
                x = current_x + float(tokens[i])
                pen.lineTo((x, current_y))
                current_x = x
                i += 1
            elif cmd == 'V':
                y = float(tokens[i])
                pen.lineTo((current_x, y))
                current_y = y
                i += 1
            elif cmd == 'v':
                y = current_y + float(tokens[i])
                pen.lineTo((current_x, y))
                current_y = y
                i += 1
            elif cmd == 'C':
                x1 = float(tokens[i])
                y1 = float(tokens[i+1])
                x2 = float(tokens[i+2])
                y2 = float(tokens[i+3])
                x = float(tokens[i+4])
                y = float(tokens[i+5])
                pen.curveTo((x1, y1), (x2, y2), (x, y))
                current_x, current_y = x, y
                i += 6
            elif cmd == 'c':
                x1 = current_x + float(tokens[i])
                y1 = current_y + float(tokens[i+1])
                x2 = current_x + float(tokens[i+2])
                y2 = current_y + float(tokens[i+3])
                x = current_x + float(tokens[i+4])
                y = current_y + float(tokens[i+5])
                pen.curveTo((x1, y1), (x2, y2), (x, y))
                current_x, current_y = x, y
                i += 6
            elif cmd == 'Q':
                x1 = float(tokens[i])
                y1 = float(tokens[i+1])
                x = float(tokens[i+2])
                y = float(tokens[i+3])
                pen.qCurveTo((x1, y1), (x, y))
                current_x, current_y = x, y
                i += 4
            elif cmd == 'q':
                x1 = current_x + float(tokens[i])
                y1 = current_y + float(tokens[i+1])
                x = current_x + float(tokens[i+2])
                y = current_y + float(tokens[i+3])
                pen.qCurveTo((x1, y1), (x, y))
                current_x, current_y = x, y
                i += 4
            elif cmd in ('Z', 'z'):
                pen.closePath()
                current_x, current_y = start_x, start_y
                # If there are subsequent coordinates, assume M mode
                cmd = 'M'
            else:
                # Unrecognized command token, skip to prevent infinite loop
                i += 1
        except (IndexError, ValueError) as e:
            # Safe recovery from malformed segments
            print(f"Skipping malformed command segment: {cmd}, error: {e}")
            i += 1

@app.post("/api/generate-font")
def generate_font(request: FontRequest):
    if not request.glyphs:
        raise HTTPException(status_code=400, detail="الرجاء إرسال حرف واحد على الأقل.")
    
    # 1. Determine font metrics from inputs or defaults
    ascent = 800
    descent = -200
    
    for g in request.glyphs:
        if g.ascent is not None:
            ascent = max(ascent, g.ascent)
        if g.descent is not None:
            descent = min(descent, g.descent)
            
    # Setup FontBuilder
    fb = FontBuilder(unitsPerEm=1024, isTTF=True)
    
    # 2. Build glyph definitions, always starting with .notdef (TrueType requirement)
    glyph_order = [".notdef"]
    character_map = {}
    glyphs = {}
    metrics = {}
    
    # Add .notdef box glyph
    notdef_pen = TTGlyphPen(None)
    notdef_pen.moveTo((100, 0))
    notdef_pen.lineTo((100, ascent))
    notdef_pen.lineTo((500, ascent))
    notdef_pen.lineTo((500, 0))
    notdef_pen.closePath()
    notdef_pen.moveTo((150, 50))
    notdef_pen.lineTo((450, 50))
    notdef_pen.lineTo((450, ascent - 50))
    notdef_pen.lineTo((150, ascent - 50))
    notdef_pen.closePath()
    glyphs[".notdef"] = notdef_pen.getGlyph()
    metrics[".notdef"] = (600, 100)
    
    # Add Space glyph if not present
    space_included = any(g.unicode == 32 or g.name == "space" for g in request.glyphs)
    if not space_included:
        glyph_order.append("space")
        character_map[32] = "space"
        space_pen = TTGlyphPen(None)
        glyphs["space"] = space_pen.getGlyph()
        metrics["space"] = (300, 0)
        
    # Process user glyphs
    for g in request.glyphs:
        glyph_name = g.name if g.name else f"uni{g.unicode:04X}"
        if glyph_name == ".notdef":
            continue
            
        # Draw glyph path onto TTGlyphPen
        pen = TTGlyphPen(None)
        parse_and_draw_svg(g.pathData, pen)
        
        try:
            glyph_outline = pen.getGlyph()
        except Exception as e:
            print(f"Failed to compile glyph {glyph_name}: {e}")
            # Fallback to empty glyph
            glyph_outline = TTGlyphPen(None).getGlyph()
            
        glyph_order.append(glyph_name)
        glyphs[glyph_name] = glyph_outline
        
        # Calculate left side bearing (LSB) from path minX or default to 0
        lsb = 0
        metrics[glyph_name] = (int(g.advanceWidth), lsb)
        
        if g.unicode and g.unicode > 0:
            character_map[int(g.unicode)] = glyph_name
            
    # Setup glyph structure
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(character_map)
    fb.setupGlyphs(glyphs)
    fb.setupHorizontalMetrics(metrics)
    
    # Setup table headers and name fields
    font_name_safe = re.sub(r'[^a-zA-Z0-9]', '', request.fontName)
    fb.setupHorizontalHeader(ascent=int(ascent), descent=int(descent))
    fb.setupNameTable({
        "familyName": request.fontName,
        "styleName": "Regular",
        "uniqueFontIdentifier": f"{font_name_safe} 1.0",
        "fullName": f"{request.fontName} Regular",
        "psName": f"{font_name_safe}-Regular"
    })
    
    fb.setupOS2(sTypoAscender=int(ascent), sTypoDescender=int(descent))
    fb.setupPost()
    
    # Compile and return standard TTF file
    buf = BytesIO()
    fb.save(buf)
    buf.seek(0)
    
    return Response(
        content=buf.read(),
        media_type="font/ttf",
        headers={
            "Content-Disposition": f"attachment; filename={font_name_safe}.ttf"
        }
    )

if __name__ == "__main__":
    import uvicorn
    # Standalone script runner
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
