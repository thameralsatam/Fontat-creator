import express from 'express';
import cors from 'cors';
// @ts-ignore
import { Font } from 'fonteditor-core';

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

app.post('/api/generate-font', (req, res) => {
  try {
    const { glyphs } = req.body;

    // التأكد من وجود بيانات
    if (!glyphs || glyphs.length === 0) {
      throw new Error("No glyphs provided");
    }

    let svg = `<?xml version="1.0" standalone="no"?>
    <svg xmlns="http://www.w3.org/2000/svg">
    <defs>
    <font id="SmartFont" horiz-adv-x="1000">
      <font-face font-family="SmartFont" units-per-em="1000" ascent="1000" descent="0" />
      <missing-glyph horiz-adv-x="1000" d="M0 0 L1000 0 L1000 1000 L0 1000 Z" />`;

    glyphs.forEach((g: any) => {
      let d = g.pathData.trim();
      // تأكد إن المسار مش فاضي
      if (!d) return;
      
      if (!d.toUpperCase().endsWith('Z')) d += ' Z';
      
      const uni = parseInt(g.unicode).toString(16);
      const width = g.advanceWidth || 1000;

      svg += `\n<glyph glyph-name="${g.name || 'char_' + uni}" unicode="&#x${uni};" d="${d}" horiz-adv-x="${width}" />`;
    });

    svg += `\n</font></defs></svg>`;

    // خلق كائن الخط
    const font = Font.create(svg, { type: 'svg' });
    
    // دمج المسارات المتداخلة (مهم جداً للوصلات اللي عملتها)
    font.compound2simple(); 

    // التصدير - جرب ttf أولاً إذا الـ otf أعطى خطأ 500
    // لأن بعض نسخ المكتبة بتحتاج ttf2otf كإضافة خارجية
    const outBuffer = font.write({ 
      type: 'ttf', // النصيحة: خليك ttf حالياً للتأكد من نجاح العملية، ثم جرب otf
      hinting: true 
    });
    
    res.setHeader('Content-Type', 'application/x-font-ttf');
    res.setHeader('Content-Disposition', 'attachment; filename="SmartArabic.ttf"');
    res.send(Buffer.from(outBuffer));

  } catch (error: any) {
    console.error("Export Error:", error.message);
    res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is live on port ${PORT}`);
});
