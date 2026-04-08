import express from 'express';
import cors from 'cors';
// @ts-ignore
import { Font } from 'fonteditor-core';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '50mb' }));

// مسار المعالجة الوحيد الذي نحتاجه
app.post('/api/generate-font', (req, res) => {
  try {
    const { glyphs, unitsPerEm, ascender, descender } = req.body;

    // بناء قالب SVG Font
    let svgFont = `<?xml version="1.0" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg">
<defs>
<font id="SmartFont" horiz-adv-x="${unitsPerEm}">
  <font-face font-family="SmartFont" units-per-em="${unitsPerEm}" ascent="${ascender}" descent="${descender}" />
  <missing-glyph horiz-adv-x="500" d="M50,0 L50,700 L450,700 L450,0 Z" />`;

    for (const g of glyphs) {
      const unicodeEntity = `&#x${g.unicode.toString(16)};`;
      // نضع المسار (d) كما هو، ونعالج التنسيق في الخطوة التالية
      svgFont += `\n  <glyph glyph-name="${g.name}" unicode="${unicodeEntity}" horiz-adv-x="${g.advanceWidth}" d="${g.pathData}" />`;
    }

    svgFont += `\n</font>\n</defs>\n</svg>`;

    // المعالجة بواسطة fonteditor-core
    const font = Font.create(svgFont, { type: 'svg' });
    
    // أهم خطوة لظهور المحارف: تحويل المسارات لتنسيق TTF بسيط ومفهوم للويندوز
    font.compound2simple();
    font.optimize();

    const ttfBuffer = font.write({
      type: 'ttf',
      hinting: true,
      support: { head: true, hhea: true, maxp: true, post: true, cmap: true, glyf: true, name: true }
    });

    res.setHeader('Content-Type', 'font/ttf');
    res.setHeader('Content-Disposition', 'attachment; filename="font.ttf"');
    res.send(Buffer.from(ttfBuffer));

  } catch (error: any) {
    console.error("Font Error:", error);
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => console.log(`API Server running on port ${PORT}`));
