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

    // إنشاء هيكل الخط بمربع قياسي (1000x1000)
    // الصفر في الأسفل (Descent=0) والقمة في الأعلى (Ascent=1000)
    let svg = `<?xml version="1.0" standalone="no"?>
    <svg xmlns="http://www.w3.org/2000/svg">
    <defs>
    <font id="SmartFont" horiz-adv-x="1000">
      <font-face font-family="SmartFont" units-per-em="1000" ascent="1000" descent="0" />
      <missing-glyph horiz-adv-x="1000" d="M0 0 L1000 0 L1000 1000 L0 1000 Z" />`;

    glyphs.forEach((g: any) => {
      // إغلاق المسار لضمان عدم وجود أجزاء شفافة
      let d = g.pathData.trim();
      if (!d.toUpperCase().endsWith('Z')) d += ' Z';
      
      const uni = parseInt(g.unicode).toString(16);
      // استخدام advanceWidth القادم من الموقع، وإذا لم يوجد نستخدم 1000
      const width = g.advanceWidth || 1000;

      svg += `\n<glyph glyph-name="${g.name}" unicode="&#x${uni};" d="${d}" horiz-adv-x="${width}" />`;
    });

    svg += `\n</font></defs></svg>`;

    // المعالجة والتحويل لـ TTF
    const font = Font.create(svg, { type: 'svg' });
    font.optimize(); // تنظيف المسارات فقط
    font.compound2simple(); // جعلها كتلة مصمتة

    const ttfBuffer = font.write({ type: 'ttf' });
    res.setHeader('Content-Type', 'font/ttf');
    res.send(Buffer.from(ttfBuffer));

  } catch (error: any) {
    res.status(500).send(error.message);
  }
});

app.listen(process.env.PORT || 3000, () => {
    console.log("Server running perfectly on port 3000");
});
