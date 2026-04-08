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
<font id="SmartFont" horiz-adv-x="1200">
  <font-face font-family="SmartFont" units-per-em="2048" ascent="1600" descent="-448" />
  <missing-glyph horiz-adv-x="500" d="M0 0 L500 0 L500 500 L0 500 Z" />`;

    glyphs.forEach((g) => {
      let path = g.pathData.trim();

      // تأكد المسار مغلق
      if (!path.toUpperCase().endsWith('Z')) {
        path += ' Z';
      }

      // 🔥 إصلاح الإحداثيات (أهم شي)
      const SCALE = 3;
      const OFFSET_Y = 1400;

      let i = 0;
      path = path.replace(/-?\d+(\.\d+)?/g, (num) => {
        let value = parseFloat(num);

        if (i % 2 === 0) {
          // X
          value = value * SCALE;
        } else {
          // Y
          value = -value * SCALE + OFFSET_Y;
        }

        i++;
        return value;
      });

      // Unicode (رقم أو حرف)
      let unicodeHex;
      if (typeof g.unicode === 'number') {
        unicodeHex = g.unicode.toString(16);
      } else {
        unicodeHex = g.unicode.codePointAt(0).toString(16);
      }

      svg += `
  <glyph 
    glyph-name="${g.name}" 
    unicode="&#x${unicodeHex};" 
    d="${path}" 
    horiz-adv-x="${g.advanceWidth || 1200}" 
  />`;
    });

    svg += `
</font>
</defs>
</svg>`;

    const font = Font.create(svg, { type: 'svg' });

    font.optimize();
    font.compound2simple();

    const ttfBuffer = font.write({
      type: 'ttf',
      hinting: true,
      combinePath: true
    });

    res.setHeader('Content-Type', 'font/ttf');
    res.setHeader('Content-Disposition', 'attachment; filename="SmartFont.ttf"');
    res.send(Buffer.from(ttfBuffer));

  } catch (error) {
    console.error("ERROR:", error);
    res.status(500).send(error.message);
  }
});

app.listen(3000, () => console.log('✅ Server running on port 3000'));
