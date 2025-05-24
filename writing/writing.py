import asyncio
import threading
from telebot import types
from .writing_texts import texts

class WritingTest:
    def __init__(self, bot, user_tests_dict):
        self.bot = bot
        self.user_tests = user_tests_dict
        self.tasks = texts
        self.active_users = {}
        self.current_task_index = {}

    async def send_timer(self, chat_id, seconds, label, stop_event=None, allow_early_finish=False):
        markup = types.InlineKeyboardMarkup()
        if allow_early_finish:
            finish_button = types.InlineKeyboardButton(text="⏹ Finish now", callback_data=f"finish_writing_{chat_id}")
            markup.add(finish_button)
        
        msg = self.bot.send_message(chat_id, f"⏳ {label}: {seconds // 60}:{seconds % 60:02d}", reply_markup=markup)
        
        while seconds > 0 and not (stop_event and stop_event.is_set()):
            await asyncio.sleep(1)
            seconds -= 1
            try:
                self.bot.edit_message_text(
                    f"⏳ {label}: {seconds // 60}:{seconds % 60:02d}", 
                    chat_id, 
                    msg.message_id,
                    reply_markup=markup
                )
            except:
                pass
        
        if stop_event and stop_event.is_set():
            try:
                self.bot.edit_message_text(f"⏹ {label} stopped.", chat_id, msg.message_id)
            except:
                pass
        else:
            self.bot.send_message(chat_id, f"⏱ {label} completed!")
        return msg

    def start_test(self, message):
        chat_id = message.chat.id
        self.current_task_index[chat_id] = 0
        thread = threading.Thread(target=self._start_async_loop, args=(chat_id,))
        thread.start()

    def _start_async_loop(self, chat_id):
        asyncio.run(self._run_test(chat_id))

    async def _run_test(self, chat_id):
        self.bot.send_message(chat_id, "✍️ *Writing Section Started*", parse_mode="Markdown")

        while self.current_task_index.get(chat_id, 0) < len(self.tasks):
            task_index = self.current_task_index[chat_id]
            task = self.tasks[task_index]

            # Создаем новое событие для каждого задания
            self.active_users[chat_id] = {
                "writing": False,
                "stop_event": asyncio.Event(),  # Важно: новый Event для каждого задания
                "word_count": 0,
                "reading_msg": None,
                "current_task": task["type"],
                "current_phase": None
            }

            if task["type"] == "integrated":
                # Этап 1: Чтение (можно завершить досрочно)
                self.active_users[chat_id]["current_phase"] = "reading"
                reading_msg = self.bot.send_message(chat_id, task["reading_text"], parse_mode="Markdown")
                self.active_users[chat_id]["reading_msg"] = reading_msg
                
                # Запускаем таймер чтения
                timer_msg = await self.send_timer(
                    chat_id,
                    task["reading_time"],
                    "Reading time",
                    self.active_users[chat_id]["stop_event"],
                    allow_early_finish=True
                )
                
                try:
                    self.bot.delete_message(chat_id, reading_msg.message_id)
                    self.bot.delete_message(chat_id, timer_msg.message_id)
                except Exception as e:
                    print(f"Error deleting message: {e}")
                
                # Этап 2: Аудирование (нельзя завершить досрочно)
                self.active_users[chat_id]["current_phase"] = "listening"
                self.bot.send_message(chat_id, "🎧 Now listen to the lecture:", parse_mode="Markdown")
                
                with open(task["audio_path"], 'rb') as audio:
                    audio_msg = self.bot.send_audio(chat_id, audio)
                
                # Таймер аудирования (без возможности досрочного завершения)
                await self.send_timer(
                    chat_id,
                    task["audio_duration"],
                    "Listening time",
                    allow_early_finish=False
                )
                
                try:
                    self.bot.delete_message(chat_id, audio_msg.message_id)
                except:
                    pass

                # Этап 3: Письмо (можно завершить досрочно)
                self.active_users[chat_id]["current_phase"] = "writing"
                
                # Показываем текст для справки и вопрос
                self.bot.send_message(chat_id, "📖 Text for reference:", parse_mode="Markdown")
                self.bot.send_message(chat_id, task["reading_text"], parse_mode="Markdown")
                self.bot.send_message(chat_id, task["question"], parse_mode="Markdown")
                
                # Сбрасываем stop_event перед началом письма
                self.active_users[chat_id]["stop_event"].clear()
                self.active_users[chat_id]["writing"] = True
                
                # Запускаем таймер письма
                await self.send_timer(
                    chat_id,
                    task["writing_time"],
                    "Writing time",
                    self.active_users[chat_id]["stop_event"],
                    allow_early_finish=True
                )
                
                self.active_users[chat_id]["writing"] = False
                
                # Проверка количества слов
                if self.active_users[chat_id]["word_count"] < 150:
                    self.bot.send_message(chat_id, "⚠️ You have written less than 150 words. Recommended: 150-225 words.")
                elif self.active_users[chat_id]["word_count"] > 225:
                    self.bot.send_message(chat_id, "⚠️ You have written more than 225 words. Recommended: 150-225 words.")

            elif task["type"] == "discussion":
                # Discussion task (можно завершить досрочно)
                self.active_users[chat_id]["current_phase"] = "writing"
                self.bot.send_message(chat_id, task["prompt"], parse_mode="Markdown")
                self.active_users[chat_id]["writing"] = True
                await self.send_timer(
                    chat_id, 
                    task["writing_time"], 
                    "Time to write:", 
                    self.active_users[chat_id]["stop_event"],
                    allow_early_finish=True
                )
                self.active_users[chat_id]["writing"] = False
                
                # Word count check
                if self.active_users[chat_id]["word_count"] < 100:
                    self.bot.send_message(chat_id, "⚠️ You have written less than 100 words. It is recommended to write about 120 words.")
                elif self.active_users[chat_id]["word_count"] > 150:
                    self.bot.send_message(chat_id, "⚠️ You have written more than 150 words. It is recommended to write about 120 words.")

            # Переход к следующему заданию
            self.current_task_index[chat_id] += 1

        # Завершение секции
        self.bot.send_message(chat_id, "✅ Writing Section Complete.")
        self.active_users.pop(chat_id, None)
        self.current_task_index.pop(chat_id, None)

    def handle_text(self, message):
        chat_id = message.chat.id
        user_state = self.active_users.get(chat_id)

        if not user_state:
            self.bot.send_message(chat_id, "The Writing task is not currently underway.")
            return

        if not user_state["writing"]:
            self.bot.send_message(chat_id, "⛔️ You can't send you text now. The text is not accepted.")
            return

        word_count = len(message.text.split())
        user_state["word_count"] = word_count
        self.bot.send_message(chat_id, f"📝 Words: {word_count}", reply_to_message_id=message.message_id)

    def finish_early(self, chat_id):
        if chat_id in self.active_users:
            current_phase = self.active_users[chat_id].get("current_phase")
            
            # Проверяем, можно ли завершить текущую фазу досрочно
            if current_phase in ["reading", "writing"]:
                # Останавливаем текущее задание
                self.active_users[chat_id]["stop_event"].set()
                self.active_users[chat_id]["writing"] = False
                
                # Проверка количества слов (только для фазы writing)
                if current_phase == "writing":
                    if self.active_users[chat_id]["current_task"] == "integrated":
                        if self.active_users[chat_id]["word_count"] < 150:
                            self.bot.send_message(chat_id, "⚠️ You have written less than 150 words. It is recommended to write 150-225 words.")
                        elif self.active_users[chat_id]["word_count"] > 225:
                            self.bot.send_message(chat_id, "⚠️ You have written more than 225 words. It is recommended to write 150-225 words.")
                    else:
                        if self.active_users[chat_id]["word_count"] < 100:
                            self.bot.send_message(chat_id, "⚠️ You have written less than 100 words. It is recommended to write about 120 words.")
                        elif self.active_users[chat_id]["word_count"] > 150:
                            self.bot.send_message(chat_id, "⚠️ You have written more than 150 words. It is recommended to write about 120 words.")
                
                self.bot.send_message(chat_id, "✅ The phase is completed ahead of schedule! Moving on to the next stage...")
            else:
                self.bot.send_message(chat_id, "⛔️ This phase cannot be completed ahead of schedule.")