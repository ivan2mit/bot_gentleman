import os
import logging
from datetime import time, datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import random
import asyncio
import json
from pathlib import Path

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GIGACHAT_API_KEY = os.getenv('GIGACHAT_API_KEY')

try:
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
except (ValueError, TypeError):
    ADMIN_ID = 0

SCHEDULES_FILE = 'user_schedules.json'
NAMES_FILE = 'user_names.json'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Система промпта для джентльмена
GENTLEMAN_SYSTEM_PROMPT = """Ты — галантный и воспитанный джентльмен, специалист по мотивации и комплиментам для женщин. 
Твоя цель:
1. Дарить искренние и оригинальные комплименты
2. Мотивировать и вдохновлять
3. Быть вежливым, деликатным и уважительным
4. Поддерживать позитивное настроение
5. Давать мудрые советы о саморазвитии и достижении целей

Правила:
- Всегда обращайся на 'вы' и с уважением
- Комплименты должны быть разнообразными (ум, характер, способности, внешность)
- Не льсти чрезмерно, будь искренен
- Если пользователь грустит, проявляй эмпатию
- Поддерживай разговор, задавай вопросы
- Никогда не пиши грубо или неуважительно
- Ответы 1-2 абзаца, не длинный текст"""


class GentlemanBot:
    def __init__(self):
        logger.info("🚀 Инициализация бота...")
        self.user_ids = set()
        self.app = None
        self.user_schedules = {}
        self.user_names = {}
        
        try:
            self.giga = GigaChat(
                credentials=GIGACHAT_API_KEY,
                verify_ssl_certs=False
            )
            logger.info("✅ GigaChat инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации GigaChat: {e}")
            self.giga = None
        
        # Загружаем расписания и имена из файлов
        self.load_schedules()
        self.load_names()
    
    def load_schedules(self):
        """Загрузить расписания пользователей из файла"""
        try:
            if Path(SCHEDULES_FILE).exists():
                with open(SCHEDULES_FILE, 'r', encoding='utf-8') as f:
                    self.user_schedules = json.load(f)
                logger.info(f"✅ Загружено расписаний: {len(self.user_schedules)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки расписаний: {e}")
    
    def save_schedules(self):
        """Сохранить расписания в файл"""
        try:
            with open(SCHEDULES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.user_schedules, f, ensure_ascii=False, indent=2)
            logger.info("✅ Расписания сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения расписаний: {e}")
    
    def load_names(self):
        """Загрузить имена пользователей из файла"""
        try:
            if Path(NAMES_FILE).exists():
                with open(NAMES_FILE, 'r', encoding='utf-8') as f:
                    self.user_names = json.load(f)
                logger.info(f"✅ Загружено имён: {len(self.user_names)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки имён: {e}")
    
    def save_names(self):
        """Сохранить имена в файл"""
        try:
            with open(NAMES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.user_names, f, ensure_ascii=False, indent=2)
            logger.info("✅ Имена сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения имён: {e}")
    
    def get_response(self, user_message: str) -> str:
        """Получить ответ от GigaChat"""
        if not self.giga:
            return "⚠️ Бот временно недоступен. Проверьте API ключ."
        
        try:
            logger.info(f"📤 Запрос: {user_message[:100]}")
            
            payload = Chat(
                messages=[
                    Messages(
                        role=MessagesRole.SYSTEM,
                        content=GENTLEMAN_SYSTEM_PROMPT
                    ),
                    Messages(
                        role=MessagesRole.USER,
                        content=user_message
                    )
                ],
                temperature=0.7,
                max_tokens=512,
            )
            
            response = self.giga.chat(payload)
            logger.info(f"✅ Ответ получен")
            
            if response and response.choices:
                answer = response.choices[0].message.content
                logger.info(f"📥 Ответ: {answer[:100]}")
                return answer
            else:
                logger.error(f"⚠️ Неожиданный формат ответа")
                return "Не удалось получить ответ"
                
        except Exception as e:
            logger.error(f"❌ Ошибка GigaChat: {type(e).__name__}: {e}", exc_info=True)
            return f"⚠️ Ошибка: {str(e)[:100]}"
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        self.user_ids.add(user_id)
        
        logger.info(f"🆔 Новый пользователь: {user_id}")
        
        user_id_str = str(user_id)
        
        # Проверяем, знаем ли мы имя
        if user_id_str in self.user_names:
            name = self.user_names[user_id_str]
            greeting = f"""Добрый день, {name}! 🎩 

Рад видеть вас снова! Я — ваш виртуальный джентльмен и готов:
• Дарить вам персонализированные комплименты
• Мотивировать и вдохновлять
• Поддерживать позитивные беседы
• Давать мудрые советы

/compliment - получить комплимент
/motivate - получить мотивацию
/setname - изменить имя
/schedule - настроить расписание
/help - справка"""
        else:
            greeting = f"""Добрый день! Я — ваш виртуальный джентльмен. Рад познакомиться! 🎩

Чтобы я мог дарить вам персонализированные комплименты, напишите мне своё имя.

Например: Мария, Александра, Виктория и т.д.

Или используйте /setname чтобы указать имя."""
            context.user_data['waiting_for_name'] = True
        
        await update.message.reply_text(greeting)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка"""
        help_text = """🎩 Команды джентльмена:

📋 ОСНОВНЫЕ:
/start - начать разговор / перезагрузиться
/help - эта справка

💬 КОМПЛИМЕНТЫ И МОТИВАЦИЯ:
/compliment - получить персонализированный комплимент
/motivate - получить мотивирующее сообщение

👤 ЛИЧНЫЕ ДАННЫЕ:
/setname - указать/изменить ваше имя (для персональных комплиментов)

⏰ РАСПИСАНИЕ:
/schedule - настроить персональное расписание мотиваций
/myschedule - посмотреть ваше текущее расписание

💬 ОБЩЕНИЕ:
Просто напишите мне сообщение - я отвечу как истинный джентльмен!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ Я готов:
• Дарить вам персонализированные комплименты
• Мотивировать и вдохновлять
• Поддерживать позитивные беседы
• Давать мудрые советы"""
        await update.message.reply_text(help_text)
    
    async def compliment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Спонтанный комплимент"""
        user_id = update.effective_user.id
        self.user_ids.add(user_id)
        user_id_str = str(user_id)
        
        logger.info(f"🎁 /compliment от {user_id}")
        
        # Формируем подсказку для GigaChat
        if user_id_str in self.user_names:
            name = self.user_names[user_id_str]
            prompt = f"Придумай оригинальный, искренний и красивый комплимент для {name}. Один комплимент, без лишних объяснений. Используй её имя в комплименте."
        else:
            prompt = "Придумай оригинальный, искренний и красивый комплимент для женщины. Один комплимент, без лишних объяснений."
        
        response = self.get_response(prompt)
        await update.message.reply_text(response)
    
    async def setname_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для установки имени"""
        user_id = update.effective_user.id
        self.user_ids.add(user_id)
        
        await update.message.reply_text("📝 Как вас зовут? (Напишите ваше имя)")
        context.user_data['waiting_for_name'] = True
        logger.info(f"📝 Запрос имени от {user_id}")
    
    async def motivate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мотивирующее сообщение"""
        user_id = update.effective_user.id
        self.user_ids.add(user_id)
        
        logger.info(f"💪 /motivate от {user_id}")
        
        prompt = "Напиши вдохновляющее сообщение о достижении целей и саморазвитии. Одно-два предложения, мудро и лаконично."
        response = self.get_response(prompt)
        await update.message.reply_text(response)
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для настройки расписания"""
        user_id = update.effective_user.id
        self.user_ids.add(user_id)
        
        schedule_text = """⏰ Настройка расписания мотиваций

Введите часы через запятую (0-23), когда вы хотите получать мотивирующие сообщения.

Примеры:
• 8,14,20 - мотивация в 8:00, 14:00 и 20:00
• 9,12,18,21 - мотивация в 9:00, 12:00, 18:00 и 21:00
• 6 - только в 6:00

Напишите часы или 'отмена' чтобы отключить:"""
        
        await update.message.reply_text(schedule_text)
        context.user_data['waiting_for_schedule'] = True
        logger.info(f"⏰ Запрос расписания от {user_id}")
    
    async def myschedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать текущее расписание пользователя"""
        user_id = str(update.effective_user.id)
        
        if user_id in self.user_schedules and self.user_schedules[user_id]['hours']:
            hours = self.user_schedules[user_id]['hours']
            times = ', '.join([f"{h}:00" for h in sorted(hours)])
            await update.message.reply_text(f"📅 Ваше расписание мотиваций:\n{times}")
        else:
            await update.message.reply_text("❌ У вас не установлено расписание.\n/schedule - установить расписание")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений"""
        user_id = update.effective_user.id
        self.user_ids.add(user_id)
        user_message = update.message.text
        user_id_str = str(user_id)
        
        # Проверяем, ждём ли имя
        if context.user_data.get('waiting_for_name'):
            context.user_data['waiting_for_name'] = False
            await self.process_name_input(update, user_message, user_id_str)
            return
        
        # Проверяем, ждём ли расписание
        if context.user_data.get('waiting_for_schedule'):
            context.user_data['waiting_for_schedule'] = False
            await self.process_schedule_input(update, user_message, user_id)
            return
        
        logger.info(f"📨 Сообщение от {user_id}: {user_message[:100]}")
        
        await update.message.chat.send_action("typing")
        
        response = self.get_response(user_message)
        logger.info(f"📬 Отправляю ответ {user_id}")
        await update.message.reply_text(response)
    
    async def process_name_input(self, update: Update, user_name: str, user_id_str: str):
        """Обработать введённое имя"""
        name = user_name.strip()
        
        if not name or len(name) < 2:
            await update.message.reply_text("❌ Пожалуйста, введите корректное имя (минимум 2 символа)")
            context.user_data['waiting_for_name'] = True
            return
        
        # Сохраняем имя
        self.user_names[user_id_str] = name
        self.save_names()
        
        await update.message.reply_text(f"✅ Спасибо, {name}! Я буду дарить вам персонализированные комплименты! 🎩")
        logger.info(f"✅ Имя сохранено для {user_id_str}: {name}")
    
    async def process_schedule_input(self, update: Update, user_input: str, user_id: int):
        """Обработать введённое расписание"""
        user_id_str = str(user_id)
        
        if user_input.lower() == 'отмена':
            if user_id_str in self.user_schedules:
                del self.user_schedules[user_id_str]
            self.save_schedules()
            await update.message.reply_text("❌ Расписание отключено")
            logger.info(f"❌ Расписание отключено для {user_id}")
            return
        
        try:
            hours = [int(h.strip()) for h in user_input.split(',')]
            
            # Валидация
            if not all(0 <= h <= 23 for h in hours):
                await update.message.reply_text("❌ Ошибка! Часы должны быть от 0 до 23")
                context.user_data['waiting_for_schedule'] = True
                return
            
            # Сохраняем расписание
            self.user_schedules[user_id_str] = {
                'hours': sorted(hours),
                'enabled': True
            }
            self.save_schedules()
            
            times = ', '.join([f"{h}:00" for h in sorted(hours)])
            await update.message.reply_text(f"✅ Расписание установлено!\n⏰ {times}")
            logger.info(f"✅ Расписание установлено для {user_id}: {hours}")
            
        except ValueError:
            await update.message.reply_text("❌ Ошибка! Введите часы через запятую (например: 8,14,20)")
            context.user_data['waiting_for_schedule'] = True
    
    async def scheduled_message(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправить мотивирующее сообщение пользователям по их расписаниям"""
        now = datetime.now()
        current_hour = now.hour
        
        prompts = [
            "Напиши короткий комплимент для начала дня - позитивное и воодушевляющее сообщение.",
            "Придумай мудрый совет о самолюбии и уверенности в себе.",
            "Напиши вдохновляющее сообщение о том, что каждый день - новая возможность.",
            "Скажи что-то приятное про умных и целеустремленных женщин.",
            "Напиши мотивацию для завершения дня с улыбкой.",
        ]
        
        prompt = random.choice(prompts)
        message = self.get_response(prompt)
        
        count = 0
        for user_id_str, schedule in self.user_schedules.items():
            if schedule.get('enabled', True) and current_hour in schedule.get('hours', []):
                try:
                    user_id = int(user_id_str)
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✨ {message}\n\n— Ваш джентльмен"
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Ошибка отправки {user_id_str}: {e}")
        
        if count > 0:
            logger.info(f"📢 Отправлено мотиваций: {count} пользователям")
    
    def setup_scheduler(self, application: Application):
        """Настройка расписания сообщений"""
        # Проверяем каждый час (в начале каждого часа)
        application.job_queue.run_repeating(
            self.scheduled_message,
            interval=3600,  # каждый час (3600 секунд)
            first=0,  # запустить сразу
            name="hourly_motivations"
        )
        logger.info("✅ Планировщик настроен: проверка каждый час")
    
    async def run(self):
        """Запуск бота"""
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Команды
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("compliment", self.compliment_command))
        app.add_handler(CommandHandler("motivate", self.motivate_command))
        app.add_handler(CommandHandler("setname", self.setname_command))
        app.add_handler(CommandHandler("schedule", self.schedule_command))
        app.add_handler(CommandHandler("myschedule", self.myschedule_command))
        
        # Обычные сообщения
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Настроим планировщик
        self.setup_scheduler(app)
        
        logger.info("🎩 Джентльмен готов к работе!")
        
        # Инициализируем и запускаем
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("⛔ Бот остановлен")
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()


if __name__ == '__main__':
    bot = GentlemanBot()
    asyncio.run(bot.run())