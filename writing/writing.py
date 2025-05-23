import asyncio
import threading
from telebot import types
import os

class WritingTest:
    def __init__(self, bot):
        self.bot = bot
        self.tasks = [
            {
                "type": "integrated",
                "reading_text": (
                    "📖 *Writing Task 1 - Integrated*\n"
                    "Read the passage about runic alphabet. (3 minutes)\n"
                    "The runic alphabet is a set of letters made up of forms called runes." 
                    "This writing system was used by various Germanic groups in central and" 
                    "northern Europe as early as 150 AD until about 1100 AD. The origins of "
                    "this alphabet have remained unclear, but archaeological evidence shows "
                    "that runes most likely developed independently of any other alphabet. First, "
                    "Germanic groups had little interaction with people from other parts of Europe "
                    "until around 700 AD, when the Romans conquered many parts of central Europe. "
                    "Because people in central and northern Europe were culturally isolated from "
                    "other groups, it is unlikely that the runic alphabet was based on a previous "
                    "writing system. Furthermore, according to the legends of some Germanic people, "
                    "the alphabet was created by a mythological god called Odin. In one mythological "
                    "text, Odin claims that the runes allow him to bring the dead back to life. The "
                    "mythology of the Germanic groups was very different from the mythology in other parts of "
                    "Europe, and the magical significance of the local alphabet within this mythology is "
                    "also distinct. This implies that Germanic groups connected the runes to their unique "
                    "mythology and traditions and not to writing systems from other groups. Finally, many archaeologists "
                    "note that the runic alphabet lacks similarities to any other alphabet that existed before "
                    "or at the same time as the runic system. Any similarities between the runic alphabet and "
                    "other alphabets are most likely random or coincidental. This makes it difficult" 
                    "to verify that the runic alphabet is a variant of an earlier alphabet."
                ),
                "audio_path": "writing/writing_task_1.ogg",
                "audio_duration": 10,
                "question": (
                    "✍️ *Task:* Summarize the points made in the lecture, being sure to explain how they "
                    "cast doubt on specific points made in the reading passage.\n\n"
                    "⏳ *Time Limit:* 20 minutes\n"
                    "📝 *Word Count:* 150-225 words"
                ),
                "reading_time": 10,
                "writing_time": 10
            },
            {
                "type": "discussion",
                "prompt": (
                    "💬 *Writing Task 2 - Discussion*\n"
                    "Some people believe that university students should be required to attend classes. "
                    "Others believe that going to classes should be optional for students.\n\n"
                    "Which point of view do you agree with? Use specific reasons and examples to support your answer.\n\n"
                    "⏳ *Time Limit:* 10 minutes\n"
                    "📝 *Word Count:* ~120 words"
                ),
                "writing_time": 10
            }
        ]
        self.active_users = {}
        self.current_task_index = {}

    async def send_timer(self, chat_id, seconds, label, stop_event=None, allow_early_finish=False):
        markup = types.InlineKeyboardMarkup()
        if allow_early_finish:
            finish_button = types.InlineKeyboardButton(text="⏹ Завершить досрочно", callback_data=f"finish_writing_{chat_id}")
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
                self.bot.edit_message_text(f"⏹ {label} остановлено.", chat_id, msg.message_id)
            except:
                pass
        else:
            self.bot.send_message(chat_id, f"⏱ {label} завершено!")
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

            self.active_users[chat_id] = {
                "writing": False,
                "stop_event": asyncio.Event(),
                "word_count": 0,
                "reading_msg": None,
                "current_task": task["type"],
                "current_phase": None
            }

            if task["type"] == "integrated":
                # Reading phase (можно завершить досрочно)
                self.active_users[chat_id]["current_phase"] = "reading"
                reading_msg = self.bot.send_message(chat_id, task["reading_text"], parse_mode="Markdown")
                self.active_users[chat_id]["reading_msg"] = reading_msg
                timer_msg = await self.send_timer(
                    chat_id, 
                    task["reading_time"], 
                    "Время на чтение",
                    self.active_users[chat_id]["stop_event"],
                    allow_early_finish=True
                )
                
                try:
                    self.bot.delete_message(chat_id, reading_msg.message_id)
                    self.bot.delete_message(chat_id, timer_msg.message_id)
                except Exception as e:
                    print(f"Error deleting message: {e}")
                
                # Listening phase (НЕЛЬЗЯ завершить досрочно)
                self.active_users[chat_id]["current_phase"] = "listening"
                self.bot.send_message(chat_id, "🎧 Сейчас будет аудиозапись лекции:", parse_mode="Markdown")
                with open(task["audio_path"], 'rb') as audio:
                    audio_msg = self.bot.send_audio(chat_id, audio)
                
                await self.send_timer(
                    chat_id, 
                    task["audio_duration"], 
                    "Время прослушивания",
                    allow_early_finish=False
                )
                
                try:
                    self.bot.delete_message(chat_id, audio_msg.message_id)
                except:
                    pass
                
                # Show reading text again
                self.bot.send_message(chat_id, "📖 Текст для справки:", parse_mode="Markdown")
                self.bot.send_message(chat_id, task["reading_text"], parse_mode="Markdown")
                
                # Writing phase (можно завершить досрочно)
                self.active_users[chat_id]["current_phase"] = "writing"
                self.bot.send_message(chat_id, task["question"], parse_mode="Markdown")
                self.active_users[chat_id]["writing"] = True
                await self.send_timer(
                    chat_id, 
                    task["writing_time"], 
                    "Время на написание", 
                    self.active_users[chat_id]["stop_event"],
                    allow_early_finish=True
                )
                self.active_users[chat_id]["writing"] = False
                
                # Word count check
                if self.active_users[chat_id]["word_count"] < 150:
                    self.bot.send_message(chat_id, "⚠️ Вы написали менее 150 слов. Рекомендуется писать 150-225 слов.")
                elif self.active_users[chat_id]["word_count"] > 225:
                    self.bot.send_message(chat_id, "⚠️ Вы написали более 225 слов. Рекомендуется писать 150-225 слов.")

            elif task["type"] == "discussion":
                # Discussion task (можно завершить досрочно)
                self.active_users[chat_id]["current_phase"] = "writing"
                self.bot.send_message(chat_id, task["prompt"], parse_mode="Markdown")
                self.active_users[chat_id]["writing"] = True
                await self.send_timer(
                    chat_id, 
                    task["writing_time"], 
                    "Время на написание", 
                    self.active_users[chat_id]["stop_event"],
                    allow_early_finish=True
                )
                self.active_users[chat_id]["writing"] = False
                
                # Word count check
                if self.active_users[chat_id]["word_count"] < 100:
                    self.bot.send_message(chat_id, "⚠️ Вы написали менее 100 слов. Рекомендуется писать около 120 слов.")
                elif self.active_users[chat_id]["word_count"] > 150:
                    self.bot.send_message(chat_id, "⚠️ Вы написали более 150 слов. Рекомендуется писать около 120 слов.")

            # Переходим к следующему заданию
            self.current_task_index[chat_id] += 1

        self.bot.send_message(chat_id, "✅ Writing Section Complete.")
        self.active_users.pop(chat_id, None)
        self.current_task_index.pop(chat_id, None)

    def handle_text(self, message):
        chat_id = message.chat.id
        user_state = self.active_users.get(chat_id)

        if not user_state:
            self.bot.send_message(chat_id, "Сейчас не проводится задание Writing.")
            return

        if not user_state["writing"]:
            self.bot.send_message(chat_id, "⛔️ Текст не принимается.")
            return

        word_count = len(message.text.split())
        user_state["word_count"] = word_count
        self.bot.send_message(chat_id, f"📝 Слов: {word_count}", reply_to_message_id=message.message_id)

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
                            self.bot.send_message(chat_id, "⚠️ Вы написали менее 150 слов. Рекомендуется писать 150-225 слов.")
                        elif self.active_users[chat_id]["word_count"] > 225:
                            self.bot.send_message(chat_id, "⚠️ Вы написали более 225 слов. Рекомендуется писать 150-225 слов.")
                    else:
                        if self.active_users[chat_id]["word_count"] < 100:
                            self.bot.send_message(chat_id, "⚠️ Вы написали менее 100 слов. Рекомендуется писать около 120 слов.")
                        elif self.active_users[chat_id]["word_count"] > 150:
                            self.bot.send_message(chat_id, "⚠️ Вы написали более 150 слов. Рекомендуется писать около 120 слов.")
                
                self.bot.send_message(chat_id, "✅ Фаза завершена досрочно! Переходим к следующему этапу...")
            else:
                self.bot.send_message(chat_id, "⛔️ Эта фаза не может быть завершена досрочно.")