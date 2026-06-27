import re
import os
from io import BytesIO
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.cu2quPen import Cu2QuPen

app = FastAPI(title="Arabic Font Generator Service")

# تفعيل الـ CORS للسماح بالاتصال من واجهة الموقع
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

# ==========================================
# 1. مسار الفحص (للتأكد أن السيرفر يعمل)
# ==========================================
@app.get("/")
def health_check():
    return {"status": "success", "message": "سيرفر توليد الخطوط شغال ومستعد 🚀"}

# ==========================================
# 2. منطق تحليل مسارات SVG
# ==========================================
def parse_and_draw_svg(path_str: str, pen):
    tokens = re.findall(r'([a-zA-Z])|(-?\d*(?:\.\d+)?(?:[eE][-+]?\d+)?)', path_str)
    tokens = [t[0] or t[1] for t in tokens if t[0] or t[1]]
    
    current_x, current_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0
    
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
                x, y = float(tokens[i]), float(tokens[i+1])
                pen.moveTo((x, y))
                current_x, current_y = x, y
                start_x, start_y = x, y
                i += 2
            elif cmd == 'm':
                x, y = current_x + float(tokens[i]), current_y + float(tokens[i+1])
                pen.moveTo((x, y))
                current_x, current_y = x, y
                start_x, start_y = x, y
                i += 2
            elif cmd == 'L':
                x, y = float(tokens[i]), float(tokens[i+1])
                pen.lineTo((x, y))
                current_x, current_y = x, y
                i += 2
            elif cmd == 'l':
                x, y = current_x + float(tokens[i]), current_y + float(tokens[i+1])
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
                x1, y1 = float(tokens[i]), float(tokens[i+1])
                x2, y2 = float(tokens[i+2]), float(tokens[i+3])
                x, y = float(tokens[i+4]), float(tokens[i+5])
                pen.curveTo((x1, y1), (x2, y2), (x, y))
                current_x, current_y = x, y
                i += 6
            elif cmd == 'c':
                x1, y1 = current_x + float(tokens[i]), current_y + float(tokens[i+1])
                x2, y2 = current_x + float(tokens[i+2]), current_y + float(tokens[i+3])
                x, y = current_x + float(tokens[i+4]), current_y + float(tokens[i+5])
                pen.curveTo((x1, y1), (x2, y2), (x, y))
                current_x, current_y = x, y
                i += 6
            elif cmd == 'Q':
                x1, y1 = float(tokens[i]), float(tokens[i+1])
                x, y = float(tokens[i+2]), float(tokens[i+3])
                pen.qCurveTo((x1, y1), (x, y))
                current_x, current_y = x, y
                i += 4
            elif cmd == 'q':
                x1, y1 = current_x + float(tokens[i]), current_y + float(tokens[i+1])
                x, y = current_x + float(tokens[i+2]), current_y + float(tokens[i+3])
                pen.qCurveTo((x1, y1), (x, y))
                current_x, current_y = x, y
                i += 4
            elif cmd in ('Z', 'z'):
                pen.closePath()
                current_x, current_y = start_x, start_y
                cmd = 'M'
            else:
                i += 1
        except (IndexError, ValueError) as e:
            print(f"Skipping malformed command segment: {cmd}, error: {e}")
            i += 1

# ==========================================
# 3. مسار توليد ملف الخط
# ==========================================
@app.post("/api/generate-font")
def generate_font(request: FontRequest):
    if not request.glyphs:
        raise HTTPException(status_code=400, detail="الرجاء إرسال حرف واحد على الأقل.")
    
    ascent = 800
    descent = -200
    
    for g in request.glyphs:
        if g.ascent is not None:
            ascent = max(ascent, g.ascent)
        if g.descent is not None:
            descent = min(descent, g.descent)
            
    fb = FontBuilder(unitsPerEm=1024, isTTF=True)
    
    glyph_order = [".notdef"]
    character_map = {}
    glyphs = {}
    metrics = {}
    
    # مربع الـ notdef
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
    glyphs[".notdef"] = notdef_pen.glyph()
    metrics[".notdef"] = (600, 100)
    
    # حرف المسافة (Space)
    space_included = any(g.unicode == 32 or g.name == "space" for g in request.glyphs)
    if not space_included:
        glyph_order.append("space")
        character_map[32] = "space"
        space_pen = TTGlyphPen(None)
        glyphs["space"] = space_pen.glyph()
        metrics["space"] = (300, 0)
        
    # معالجة بقية المحارف المرسلة
    for g in request.glyphs:
        glyph_name = g.name if g.name else f"uni{g.unicode:04X}"
        if glyph_name == ".notdef":
            continue
            
        base_pen = TTGlyphPen(None)
        
        # مصفوفة تحويل إحداثيات Y
        transform_matrix = (1, 0, 0, -1, 0, ascent)
        t_pen = TransformPen(base_pen, transform_matrix)
        
        # معالجة المنحنيات التكعيبية
        cu2qu_pen = Cu2QuPen(t_pen, max_err=2.0)
        
        # رسم المسار
        parse_and_draw_svg(g.pathData, cu2qu_pen)
        
        try:
            glyph_outline = base_pen.glyph()
        except Exception as e:
            print(f"Failed to compile glyph {glyph_name}: {e}")
            glyph_outline = TTGlyphPen(None).glyph()
            
        glyph_order.append(glyph_name)
        glyphs[glyph_name] = glyph_outline
        
        # حساب الـ Left Side Bearing بشكل آمن 100%
        try:
            # نستخرج xMin الفعلي بعد الرسم بدلاً من getBounds
            lsb = int(getattr(glyph_outline, 'xMin', 0))
        except Exception:
            lsb = 0
            
        metrics[glyph_name] = (int(g.advanceWidth), lsb)
        
        if g.unicode and g.unicode > 0:
            character_map[int(g.unicode)] = glyph_name
            
    # بناء جداول الخط
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(character_map)
    fb.setupGlyphs(glyphs)
    fb.setupHorizontalMetrics(metrics)
    
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
