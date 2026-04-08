import express from 'express';
import { createServer as createViteServer } from 'vite';
import cors from 'cors';
import path from 'path';
// @ts-ignore
import { Font } from 'fonteditor-core';

async function startServer() {
  const app = express();
  const PORT = process.env.PORT || 3000;

  app.use(cors());
  // زيادة حجم الطلب المسموح به لأن ملفات الـ SVG قد تكون كبيرة
  app.use(express.json({ limit: '50mb' }));

  // مسار API لتوليد الخط
  app.post('/api/generate-font', (req, res) => {
    try {
      const { glyphs, unitsPerEm, ascender, descender } = req.body;

      // 1. بناء قالب SVG Font في الذاكرة
      // مكتبة fonteditor-core ممتازة في قراءة خطوط الـ SVG وتحويلها لـ TTF
      let svgFont = `<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg">
<defs>
<font id="SmartArabicFont" horiz-adv-x="${unitsPerEm}">
  <font-face font-family="SmartArabicFont" units-per-em="${unitsPerEm}" ascent="${ascender}" descent="${descender}" />
  <missing-glyph horiz-adv-x="500" d="M50,0 L50,700 L450,700 L450,0 Z" />
`;

      // 2. إضافة المحارف التي تم إرسالها من المتصفح
      for (const g of glyphs) {
        // حماية الأسماء من كسر كود الـ XML
        const safeName = g.name.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        // تحويل الـ Unicode إلى صيغة XML Entity
        const unicodeEntity = `&#x${g.unicode.toString(16)};`;
        
        svgFont += `  <glyph glyph-name="${safeName}" unicode="${unicodeEntity}" horiz-adv-x="${g.advanceWidth}" d="${g.pathData}" />\n`;
      }

      svgFont += `</font>\n</defs>\n</svg>`;

      // 3. قراءة الـ SVG Font باستخدام fonteditor-core
      const font = Font.create(svgFont, {
        type: 'svg'
      });

      // --- [الإضافات السحرية هنا] ---

      // أ. توحيد اتجاه المسارات وفك التقاطعات المعقدة (حتى لا تظهر ثقوب شفافة)
      font.compound2simple();

      // ب. تحسين وتصحيح هندسة المحارف (ضروري جداً لظهور المحرف)
      font.optimize();

      // ج. ملاحظة بخصوص الـ Y-Axis:
      // مكتبة fonteditor-core تفترض أن الـ SVG مقلوب بشكل افتراضي وتصححه أحياناً.
      // إذا ظهرت الحروف مقلوبة بعد التجربة، ستحتاج لإضافة سطر رياضي هنا لقلبها (Scale Y: -1)

      // 4. تحويل الخط إلى TTF (TrueType Font)
      const ttfBuffer = font.write({
        type: 'ttf',
        hinting: true,
        // d. تأكيد إزالة التقاطعات أثناء التحويل
        support: {
          head: true,
          hhea: true,
          maxp: true,
          post: true,
          cmap: true,
          glyf: true,
          name: true
        }
      });

      // 5. إرسال ملف الخط كاستجابة للتحميل
