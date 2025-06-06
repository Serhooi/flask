# Деплой на Render.com

## Исправления в этой версии
- ✅ **Адрес переносится на 3 строки** - исправлено в базе данных
- ✅ **Headshot заполняет круг** без растягивания (object-fit: cover)
- ✅ **Убраны артефакты** Photo Template
- ✅ **Логотип сохраняет пропорции**

## Шаги для деплоя

### 1. Обновите репозиторий
```bash
# Скопируйте файлы в ваш репозиторий flask/svg-template-api
cp app.py /path/to/your/flask/svg-template-api/
cp templates.db /path/to/your/flask/svg-template-api/
cp requirements.txt /path/to/your/flask/svg-template-api/

# Коммит изменений
git add .
git commit -m "Fix: address wrapping, headshot cropping, photo template artifacts"
git push origin main
```

### 2. Настройте Render.com
1. Зайдите на https://render.com
2. Подключите ваш GitHub репозиторий `flask/svg-template-api`
3. Выберите "Web Service"
4. Настройки:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Environment**: Python 3.11

### 3. Переменные окружения
Добавьте в Render.com:
- `PYTHON_VERSION`: `3.11.0`

### 4. Обновите URL в React приложении
Замените URL API на новый от Render:
```typescript
const API_BASE_URL = 'https://your-app-name.onrender.com';
```

## API Endpoints
- `GET /api/templates` - список шаблонов
- `POST /api/carousel` - создать карусель
- `POST /api/carousel/{id}/generate` - запустить генерацию
- `GET /api/carousel/{id}/slides` - получить результат
- `GET /health` - проверка здоровья

## Тестирование
После деплоя проверьте:
1. `GET /health` - должен вернуть `{"status": "healthy", "version": "1.1.0-fixed"}`
2. `GET /api/templates` - должен вернуть список шаблонов
3. Создайте тестовую карусель и проверьте что адрес переносится на 3 строки
