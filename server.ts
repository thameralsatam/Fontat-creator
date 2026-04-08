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

    // فتح القالب
    const buffer = fs.readFileSync(templatePath);
    const font = Font.create(buffer, { type: 'ttf' });
    const fontData = font.get();

    // استبدال المحارف
    glyphs.forEach((g: any) => {
      const targetIndex = fontData.glyf.findIndex((item: any) => 
        item.unicode && item.unicode.includes(g.unicode)
      );

      if (targetIndex !== -1) {
        fontData.glyf[targetIndex].d = g.pathData;
        fontData.glyf[targetIndex].advanceWidth = g.advanceWidth || 1000;
      } else {
        fontData.glyf.push({
          unicode: [g.unicode],
          name: g.name,
          d: g.pathData,
          advanceWidth: g.advanceWidth || 1000
        });
      }
    });

    font.set(fontData);
    font.optimize();

    const ttfBuffer = font.write({ type: 'ttf', hinting: true });
    res.send(Buffer.from(ttfBuffer));

  } catch (error: any) {
    res.status(500).send(error.message);
  }
});

app.listen(process.env.PORT || 3000);
