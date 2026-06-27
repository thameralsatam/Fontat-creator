import os
import re
from io import BytesIO
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

# استخدام المكتبة الاحترافية لقراءة مسارات SVG
from svgelements import Path, Move, Line, QuadraticBezier, CubicBezier, Close, Arc

app = FastAPI(title="Arabic Font Generator Service")

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

@app.get("/")
def health_check():
    return {"status": "success", "message": "سيرفر البايثون المحدث يعمل بكفاءة 🚀"}

def parse_and_draw_svg(path_str: str, pen):
    """
    دالة احترافية لقراءة الـ SVG باستخدام svgelements 
    لحل مشاكل الأقواس (Arcs) والمسارات المضغوطة التي كان يفشل فيها الـ Regex.
    """
    try:
        # قراءة المسار وتحويل الأقواس (Arcs) تلقائياً إلى منحنيات بيزير متوافقة مع الخطوط
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
                # Cu2QuPen الذي يغلف هذا القلم سيقوم بتحويل الـ Cubic إلى Quadratic تلقائياً
                pen.curveTo((segment.control1.x, segment.control1.y),
                            (segment.control2.x, segment.control2.y),
                            (segment.end.x, segment.end.y))
            elif isinstance(segment, Close):
                pen.closePath()
    except Exception as e:
        print(f"Error parsing path using svgelements: {e}")

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
            
    # تم التعديل إلى 1000 ليتطابق مع حسابات الفرونت اند
    fb = FontBuilder(unitsPerEm=1000, isTTF=True)
    
    glyph_order = [".notdef"]
    character_map = {}
    glyphs = {}
    metrics = {}
    
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
    
    space_included = any(g.unicode == 32 or g.name == "space" for g in request.glyphs)
    if not space_included:
        glyph_order.append("space")
        character_map[32] = "space"
        space_pen = TTGlyphPen(None)
        glyphs["space"] = space_pen.glyph()
        metrics["space"] = (300, 0)
        
    for g in request.glyphs:
        glyph_name = g.name if g.name else f"uni{g.unicode:04X}"
        if glyph_name == ".notdef":
            continue
            
        base_pen = TTGlyphPen(None)
        
        # تم إزالة TransformPen لمنع القلب المزدوج للمحور الصادي.
        # تحويل الـ Cubic إلى Quadratic
        cu2qu_pen = Cu2QuPen(base_pen, max_err=2.0)
        
        try:
            parse_and_draw_svg(g.pathData, cu2qu_pen)
            glyph_outline = base_pen.glyph()
        except Exception as e:
            print(f"Failed to compile glyph {glyph_name}: {e}")
            # في حال الفشل نضع مساراً فارغاً كي لا ينهار ملف الخط بالكامل
            glyph_outline = TTGlyphPen(None).glyph()
            
        glyph_order.append(glyph_name)
        glyphs[glyph_name] = glyph_outline
        
        # حساب الـ LSB
        try:
            lsb = int(getattr(glyph_outline, 'xMin', 0))
        except Exception:
            lsb = 0
            
        metrics[glyph_name] = (int(g.advanceWidth), lsb)
        
        if g.unicode and g.unicode > 0:
            character_map[int(g.unicode)] = glyph_name
            
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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
