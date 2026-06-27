# سلف توليد الخطوط العربي - Arabic Font Generator Server (Python)

هذا مجلد مستقل يحتوي على سيرفر بايثون (Python Server) مبني باستخدام **FastAPI** ومكتبة **fonttools** لمعالجة وتوليد ملفات الخطوط بصيغة TTF بشكل رياضي دقيق.

## المتطلبات لتشغيل السيرفر (Prerequisites)

- تثبيت بايثون 3.8 أو أحدث.
- تثبيت المكتبات المطلوبة من ملف `requirements.txt`.

## خطوات التشغيل (How to Run)

1. افتح مبدل الأوامر في مجلد `server_python`:
   ```bash
   cd server_python
   ```

2. قم بتثبيت الاعتمادات (Dependencies):
   ```bash
   pip install -r requirements.txt
   ```

3. قم بتشغيل السيرفر:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

سيعمل السيرفر على الرابط التالي: `http://localhost:8000`

## الروابط البرمجية (Endpoints)

- **توليد الخط**: `POST /api/generate-font`
  - يستقبل قائمة الحروف بمسارات SVG، العرض والأبعاد، ويعيد ملف خط TTF حقيقي ومكتمل وجاهز للتثبيت والتحميل.
