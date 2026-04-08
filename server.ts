import express from 'express';
import cors from 'cors';
// @ts-ignore
import { Font } from 'fonteditor-core';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '50mb' }));

app.post('/api/generate-font', (req, res) => {
  try {
    const { glyphs } = req.body;

    // 1. بناء هيكل SVG Font (أكثر استقراراً للنصوص العربية والتداخل)
    let svg = `<?xml version="1.0" standalone="no"?>
    <svg xmlns="http://www.w3.org/2000/svg">
    <defs>
    <font id="SmartFont" horiz-adv-x="1000">
      <font-face font-family="SmartFont" units-per-em="2048" ascent="1900" descent="-500" />
      <missing-glyph horiz-adv-x="500" d="M0,0 L0,500 L500,500 L500,0 Z" />`;

    glyphs.forEach((g: any) => {
      // التأكد من إغلاق المسار بـ Z لمنع الشفافية
      let path = g.pathData.trim();
      if (!path.toUpperCase().endsWith('Z')) {
        path += ' Z';
      }
      
      const unicodeHex = parseInt(g.unicode).toString(16);
      svg += `\n<glyph glyph-name="${g.name}" unicode="&#x${unicodeHex};" d="${path}" horiz-adv-x="${g.advanceWidth || 1000}" />`;
    });

    svg += `\n</font></defs></svg>`;

    // 2. تحويل SVG إلى TTF مع معالجة الهندسة
    const font = Font.create(svg, { type: 'svg' });
    
    // تصحيحات ضرورية لظهور الحرف بشكل مصمت (Solid) وليس شفافاً
    font.optimize(); 
    font.compound2simple(); 

    const ttfBuffer = font.write({ 
        type: 'ttf', 
        hinting: true,
        combinePath: true // لدمج المسارات المتداخلة
    });

    res.setHeader('Content-Type', 'font/ttf');
    res.setHeader('Content-Disposition', 'attachment; filename="SmartFont.ttf"');
    res.send(Buffer.from(ttfBuffer));

  } catch (error: any) {
    console.error("Server Error:", error);
    res.status(500).send(error.message);
  }
});

app.listen(PORT, () => console.log(`Server is running on port ${PORT}`));
