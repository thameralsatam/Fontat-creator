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

    // مربع قياسي 1000x1000 لضمان مطابقة الاستعراض
    let svg = `<?xml version="1.0" standalone="no"?>
    <svg xmlns="http://www.w3.org/2000/svg">
    <defs>
    <font id="SmartFont" horiz-adv-x="1000">
      <font-face font-family="SmartFont" units-per-em="1000" ascent="1000" descent="0" />
      <missing-glyph horiz-adv-x="1000" d="M0 0 L1000 0 L1000 1000 L0 1000 Z" />`;

    glyphs.forEach((g: any) => {
      let d = g.pathData.trim();
      if (!d.toUpperCase().endsWith('Z')) d += ' Z';
      
      const uni = parseInt(g.unicode).toString(16);
      const width = g.advanceWidth || 1000;

      svg += `\n<glyph glyph-name="${g.name}" unicode="&#x${uni};" d="${d}" horiz-adv-x="${width}" />`;
    });

    svg += `\n</font></defs></svg>`;

    const font = Font.create(svg, { type: 'svg' });
    
    // ملاحظة: يمكنك حذف font.optimize() إذا وجدت أن النقاط لا تزال تتغير بشكل لا يعجبك
    font.optimize(); 
    font.compound2simple(); 

    // التصدير بصيغة OTF للحفاظ على جودة الـ Cubic Bézier
    const otfBuffer = font.write({ type: 'otf' });
    
    res.setHeader('Content-Type', 'font/otf');
    res.setHeader('Content-Disposition', 'attachment; filename="SmartArabic.otf"');
    res.send(Buffer.from(otfBuffer));

  } catch (error: any) {
    res.status(500).send(error.message);
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running perfectly on port ${PORT}`);
});
