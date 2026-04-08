import express from 'express';
import cors from 'cors';
// @ts-ignore
import { Font, svg2ttf } from 'fonteditor-core';

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

app.post('/api/generate-font', (req, res) => {
  try {
    const { glyphs } = req.body;

    // بناء ملف SVG Font بسيط جداً (هذا هو قلب Fontello)
    let svg = `<?xml version="1.0" standalone="no"?>
    <svg xmlns="http://www.w3.org/2000/svg">
    <defs>
    <font id="temp" horiz-adv-x="1000">
      <font-face font-family="MyFont" units-per-em="1000" ascent="800" descent="-200" />
      <missing-glyph horiz-adv-x="500" d="M0,0 L0,500 L500,500 L500,0 Z" />`;

    glyphs.forEach((g: any) => {
      svg += `<glyph glyph-name="${g.name}" unicode="&#x${parseInt(g.unicode).toString(16)};" d="${g.pathData}" horiz-adv-x="1000" />`;
    });

    svg += `</font></defs></svg>`;

    // تحويل الـ SVG إلى TTF مباشرة
    const font = Font.create(svg, { type: 'svg' });
    const ttfBuffer = font.write({ type: 'ttf' });

    res.setHeader('Content-Type', 'font/ttf');
    res.send(Buffer.from(ttfBuffer));

  } catch (e: any) {
    res.status(500).send(e.message);
  }
});

app.listen(process.env.PORT || 3000);
