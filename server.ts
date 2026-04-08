import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
// @ts-ignore
import { Font } from 'fonteditor-core';

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

app.post('/api/generate-font', (req, res) => {
  try {
    const { glyphs } = req.body;
    const templatePath = path.join(process.cwd(), 'template.ttf');
    const buffer = fs.readFileSync(templatePath);
    
    // 1. افتح القالب
    const font = Font.create(buffer, { type: 'ttf' });
    const fontData = font.get();

    // 2. "حشر" المحارف الجديدة حشر في القالب
    glyphs.forEach((g: any) => {
      // إجبار الحرف إنه يكون له إحداثيات واضحة ومقياس كبير
      const newGlyph = {
        name: g.name || "custom_char",
        unicode: [parseInt(g.unicode)], // تأكد إنه رقم
        d: g.pathData, 
        advanceWidth: 1500, // عرض ثابت وكبير عشان يبين
        xMin: 0,
        yMin: 0,
        xMax: 1000,
        yMax: 1000
      };

      // ضيفه في أول القائمة عشان البرامج تشوفه بسرعة
      fontData.glyf.unshift(newGlyph); 
    });

    // 3. تعطيل أي عملية تحسين قد تحذف المحارف "الغريبة"
    font.set(fontData);
    
    const ttfBuffer = font.write({ 
      type: 'ttf', 
      hinting: false, // عطل الهنتنج حالياً
      writeZeroGlyph: true 
    });

    res.setHeader('Content-Type', 'application/x-font-ttf');
    res.send(Buffer.from(ttfBuffer));

  } catch (error: any) {
    res.status(500).send(error.message);
  }
});

app.listen(process.env.PORT || 3000);
