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

    let svg = `<?xml version="1.0" standalone="no"?>
    <svg xmlns="http://www.w3.org/2000/svg">
    <defs>
    <font id="SmartFont" horiz-adv-x="1000">
      <font-face font-family="SmartFont" 
        units-per-em="1000" 
        ascent="800" 
        descent="-200" 
        alphabetic="0" /> 
      <missing-glyph horiz-adv-x="500" d="M0 0 L500 0 L500 500 L0 500 Z" />`;

    glyphs.forEach((g: any) => {
      let d = g.pathData.trim();
      if (!d.toUpperCase().endsWith('Z')) d += ' Z';
      
      const uni = parseInt(g.unicode).toString(16);
      // استخدام العرض القادم من نقاط الارتكاز في الموقع
      const width = g.advanceWidth || 1000;

      svg += `\n<glyph glyph-name="${g.name}" unicode="&#x${uni};" d="${d}" horiz-adv-x="${width}" />`;
    });

    svg += `\n</font></defs></svg>`;

    const font = Font.create(svg, { type: 'svg' });
    font.compound2simple(); // لدمج الوصلات

    const fontBuffer = font.write({ type: 'ttf' }); // ttf أكثر استقراراً للمعاينة
    res.setHeader('Content-Type', 'font/ttf');
    res.send(Buffer.from(fontBuffer));

  } catch (error: any) {
    res.status(500).send(error.message);
  }
});

app.listen(process.env.PORT || 3000);
