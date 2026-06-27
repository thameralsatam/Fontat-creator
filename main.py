import os
import re
from io import BytesIO
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from svgelements import Path, Move, Line, QuadraticBezier, CubicBezier, Close

app = FastAPI(title="Arabic Font Generator Service")

# 3. أمان السيرفر: حصر الـ CORS (استبدل الرابط أدناه برابط موقعك الفعلي للإنتاج)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://your-production-domain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GlyphInput(BaseModel):
    name: str
    unicode: int
    pathData: str
    # 4. التحقق من الـ advanceWidth
    advanceWidth: int = Field(..., gt=0, description="يجب أن يكون عرض الحرف أكبر من صفر")
    ascent: Optional[int] = None
    descent: Optional[int] = None

class FontRequest(BaseModel):
    fontName: Optional[str] = "SmartArabicFont"
    glyphs: List[GlyphInput]

@app.get("/")
def health_check():
    return {"status": "success", "message": "السيرفر المحدث يعمل (الفرونت إند يتحكم بالإحداثيات)"}

def parse_and_draw_svg(path_str: str, pen):
    try:
        svg_path = Path(path_str)
        svg_path.approximate_arcs_with_cubics()

        for segment in svg_path:
            if isinstance(segment, Move):
                pen.moveTo((segment.end.x, segment.end.y))
            elif isinstance(segment, Line):
                pen.lineTo((segment.end.x, segment.end.y))
            elif isinstance(segment, QuadraticBezier):
                pen.qCurveTo((segment.control.x, segment.control.y), (segment.end.x, segment.end.y))
            elif isinstance(segment, CubicBezier):
                pen.curveTo((segment.control1.x, segment.control1.y),
                            (segment.control2.x, segment.control2.y),
                            (segment.end.x, segment.end.y))
            elif isinstance(segment, Close):
                pen.closePath()
    except Exception as e:
        print(f"Error parsing path: {e}")

@app.post("/api/generate-font")
def generate_font(request: FontRequest):
    if not request.glyphs:
        raise HTTPException(status_code=400, detail="الرجاء إرسال حرف واحد على الأقل.")
    
    # 2. قراءة بيانات الأداء (ascent/descent) من الطلب إن وجدت
    # نأخذ أكبر ascent وأصغر descent من المدخلات كقيم عامة للخط
    ascent = 800
    descent = -200
    
    # تحديث القيم بناءً على أول حرف يحتوي قيم مخصصة (أو يمكن عمل منطق أعمق)
    for g in request.glyphs:
        if g.ascent is not None: ascent = max(ascent, g.ascent)
        if g.descent is not None: descent = min(descent, g.descent)
            
    fb = FontBuilder(unitsPerEm=1000, isTTF=True)
    
    glyph_order = [".notdef"]
    character_map = {}
    glyphs = {}
    metrics = {}
    
    # تعريف .notdef (مربع افتراضي)
    notdef_pen = TTGlyphPen(None)
    glyphs[".notdef"] = notdef_pen.glyph()
    metrics[".notdef"] = (600, 100)
    
    for g in request.glyphs:
        glyph_name = g.name if g.name else f"uni{g.unicode:04X}"
        base_pen = TTGlyphPen(None)
        
        # 1. القلب المزدوج: تم إزالة أي TransformPen. 
        # السيرفر يرسم المسار كما يصله تماماً من الفرونت إند.
        cu2qu_pen = Cu2QuPen(base_pen, max_err=2.0)
        
        parse_and_draw_svg(g.pathData, cu2qu_pen)
        
        glyph_outline = base_pen.glyph()
        glyph_order.append(glyph_name)
        glyphs[glyph_name] = glyph_outline
        
        lsb = int(getattr(glyph_outline, 'xMin', 0))
        metrics[glyph_name] = (int(g.advanceWidth), lsb)
        
        if g.unicode > 0:
            character_map[int(g.unicode)] = glyph_name
            
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(character_map)
    fb.setupGlyphs(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=int(ascent), descent=int(descent))
    
    # إعدادات التعريف
    fb.setupNameTable({
        "familyName": request.fontName,
        "styleName": "Regular",
        "fullName": f"{request.fontName} Regular",
        "psName": f"{re.sub(r'[^a-zA-Z0-9]', '', request.fontName)}-Regular"
    })
    
    fb.setupOS2(sTypoAscender=int(ascent), sTypoDescender=int(descent))
    fb.setupPost()
    
    buf = BytesIO()
    fb.save(buf)
    buf.seek(0)
    
    return Response(content=buf.read(), media_type="font/ttf")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
