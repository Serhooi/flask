# 🚀 SVG Template API - Render.com Update

## 📦 Что в этом пакете:
- ✅ **app.py** - полная версия API с всеми endpoints
- ✅ **templates.db** - база данных с исправленными шаблонами  
- ✅ **requirements.txt** - все зависимости
- ✅ **Procfile** - конфигурация для Render.com
- ✅ **render.yaml** - настройки деплоя

## 🔄 Как обновить Render.com:

### Вариант 1: Через GitHub (рекомендуется)
1. Скопируйте все файлы в ваш репозиторий `flask/svg-template-api`
2. Сделайте commit и push:
   ```bash
   git add .
   git commit -m "Add missing API endpoints and fix templates"
   git push origin main
   ```
3. Render.com автоматически подхватит изменения

### Вариант 2: Прямой деплой
1. Зайдите в Render.com Dashboard
2. Найдите ваш сервис `svg-template-api`
3. Settings → Deploy → Manual Deploy
4. Загрузите файлы из этого пакета

## ✅ Новые endpoints:
- `GET /health` - проверка здоровья
- `GET /api/templates/all-previews` - все шаблоны с превью
- `POST /api/carousel` - создать карусель
- `POST /api/carousel/{id}/generate` - запустить генерацию
- `GET /api/carousel/{id}/slides` - получить результат

## 🧪 Тестирование:
После деплоя проверьте:
- https://your-app.onrender.com/health
- https://your-app.onrender.com/api/templates/all-previews

Должны вернуться JSON ответы без ошибок 404.

## 🎯 Результат:
После обновления ваше React приложение сможет:
- ✅ Загружать шаблоны с превью
- ✅ Создавать карусели
- ✅ Генерировать слайды
- ✅ Получать результаты генерации

Built with Flask, Pillow, and CairoSVG 🚀
