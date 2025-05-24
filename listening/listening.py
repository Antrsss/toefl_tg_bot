import time
from telebot import types
import listening.listening_questions
import threading

duration_for_this_test = 36 * 60 + 30  # 30 доп. секунд для прогрузки аудио и высылки всех вопросов

class ListeningTest:
    def __init__(self, bot, user_tests_dict):
        self.bot = bot
        self.user_tests = user_tests_dict
        self.questions = listening.listening_questions.l_questions
        self.current_question_index = {}  # chat_id -> current question index
        self.user_answers = {}            # chat_id -> list of answers
        self.scores = {}                  # chat_id -> score
        self.start_times = {}             # chat_id -> start time
        self.TEST_DURATION = duration_for_this_test
        self.current_audio_file = {}      # chat_id -> audio file name
        self.sent_questions = {}         # chat_id -> set of sent question indices
        self.timer_messages = {}         # chat_id -> timer message id
        self.active_timers = {}          # chat_id -> timer thread flag
        self.finish_buttons = {}         # chat_id -> finish button message id

    def start_test(self, message):
        chat_id = message.chat.id
        self.current_question_index[chat_id] = 0
        self.user_answers[chat_id] = [-1] * len(self.questions)
        self.scores[chat_id] = 0
        self.start_times[chat_id] = time.time()
        self.current_audio_file[chat_id] = None
        self.sent_questions[chat_id] = set()

        instructions = (
            "🎧 *Listening Section Instructions*\n\n"
            "In this section, you will hear several lectures and conversations to test your listening comprehension. "
            "Each lecture or conversation will be played *only once*.\n\n"
            "After listening, answer the following questions. "
            "Questions may ask about the main idea, specific details, or implied meaning.\n\n"
            "📝 You may take notes on a separate sheet of paper. Notes are not scored.\n\n"
            "⏳ You have *36 minutes* to complete this section."
        )
        self.bot.send_message(chat_id, instructions, parse_mode="Markdown")
        
        # Start timer
        self.active_timers[chat_id] = True
        timer_thread = threading.Thread(target=self.update_timer, args=(chat_id,))
        timer_thread.start()
        
        time.sleep(2)
        self.send_all_questions(chat_id)

    def update_timer(self, chat_id):
        """Обновляет таймер каждую секунду"""
        start_time = self.start_times[chat_id]
        end_time = start_time + self.TEST_DURATION
        
        # Отправляем первое сообщение с таймером
        remaining = int(end_time - time.time())
        mins, secs = divmod(remaining, 60)
        timer_msg = self.bot.send_message(chat_id, f"⏱️ Time remaining: {mins:02d}:{secs:02d}")
        self.timer_messages[chat_id] = timer_msg.message_id
        
        while time.time() < end_time and self.active_timers.get(chat_id, False):
            remaining = int(end_time - time.time())
            mins, secs = divmod(remaining, 60)
            
            try:
                self.bot.edit_message_text(
                    f"⏱️ Time remaining: {mins:02d}:{secs:02d}",
                    chat_id=chat_id,
                    message_id=self.timer_messages[chat_id]
                )
            except:
                pass
            
            time.sleep(1)
        
        # Если время вышло, завершаем тест
        if time.time() >= end_time and chat_id in self.user_answers:
            self.finish_test(chat_id)

    def send_all_questions(self, chat_id):
        # Сначала отправляем все аудиофайлы
        audio_files_sent = set()
        for i, question in enumerate(self.questions):
            audio_file = question.get("audio_file")
            if audio_file and audio_file not in audio_files_sent:
                try:
                    with open(audio_file, 'rb') as audio:
                        self.bot.send_audio(chat_id, audio, caption=f"🎧 Audio for Questions {i+1}", timeout=30)
                        audio_files_sent.add(audio_file)
                except Exception as e:
                    print(f"Audio error: {e}")
                    self.bot.send_message(chat_id, f"(⚠️ Audio unavailable for questions {i+1})")
        
        # Затем отправляем все вопросы
        for i, question in enumerate(self.questions):
            self.send_single_question(chat_id, i)
            time.sleep(0.5)  # Небольшая задержка между вопросами
        
        # Добавляем кнопку завершения теста
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="✅ Finish Test", callback_data=f'listen_finish_{chat_id}'))
        finish_msg = self.bot.send_message(chat_id, "You can finish the test early by clicking the button below:", reply_markup=keyboard)
        self.finish_buttons[chat_id] = finish_msg.message_id

    def send_single_question(self, chat_id, question_index):
        """Отправляет один конкретный вопрос"""
        question = self.questions[question_index]
        keyboard = types.InlineKeyboardMarkup()

        selected = self.user_answers[chat_id][question_index]
        for i, option in enumerate(question['options']):
            text = f"🔵 {option}" if i == selected else option
            keyboard.add(types.InlineKeyboardButton(text=text, callback_data=f'listen_answer_{question_index}_{i}'))

        self.bot.send_message(
            chat_id,
            f"*Question {question_index + 1}/{len(self.questions)}*\n\n{question['text']}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        self.sent_questions[chat_id].add(question_index)

    def handle_answer(self, call):
        chat_id = call.message.chat.id
        if chat_id not in self.user_answers:
            return self.bot.send_message(chat_id, "❗️ Please start the test first by sending /start_listening.")

        if time.time() - self.start_times[chat_id] > self.TEST_DURATION:
            return self.finish_test(chat_id)

        try:
            parts = call.data.split('_')
            if parts[1] == 'finish':
                return self.finish_test(int(parts[2]))  # Обрабатываем кнопку завершения
                
            question_index = int(parts[2])
            answer_index = int(parts[3])
        except (IndexError, ValueError):
            return

        question = self.questions[question_index]
        self.user_answers[chat_id][question_index] = answer_index

        if answer_index == question['correct_answer']:
            self.scores[chat_id] += 1

        keyboard = types.InlineKeyboardMarkup()
        for i, option in enumerate(question['options']):
            text = f"🔵 {option}" if i == answer_index else option
            keyboard.add(types.InlineKeyboardButton(text=text, callback_data=f'listen_answer_{question_index}_{i}'))

        try:
            self.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Edit message error: {e}")

        if -1 not in self.user_answers[chat_id]:
            self.finish_test(chat_id)

    def finish_test(self, chat_id):
        # Останавливаем таймер
        self.active_timers[chat_id] = False
        
        # Удаляем сообщение с кнопкой завершения
        if chat_id in self.finish_buttons:
            try:
                self.bot.delete_message(chat_id, self.finish_buttons[chat_id])
            except:
                pass
            del self.finish_buttons[chat_id]

        total = len(self.questions)
        score = self.scores.get(chat_id, 0)
        percentage = (score / total) * 100
        answers = self.user_answers.get(chat_id, [])

        result = f"✅ *Listening Test Completed!*\n\nCorrect answers: *{score} / {total}*\nScore: *{percentage:.1f}%*\n\n*Answers Review:*\n"

        for i, question in enumerate(self.questions):
            user_ans = answers[i]
            correct_ans = question['correct_answer']
            if user_ans == correct_ans:
                result += f"{i + 1}. ✅ {question['options'][correct_ans]}\n"
            else:
                your_answer = question['options'][user_ans] if user_ans != -1 else "No answer"
                result += f"{i + 1}. ❌ Your answer: {your_answer}\n"
                result += f"    ✅ Correct: {question['options'][correct_ans]}\n"

        self.bot.send_message(chat_id, result, parse_mode="Markdown")

        # Очищаем все данные
        self.current_question_index.pop(chat_id, None)
        self.user_answers.pop(chat_id, None)
        self.scores.pop(chat_id, None)
        self.start_times.pop(chat_id, None)
        self.current_audio_file.pop(chat_id, None)
        self.sent_questions.pop(chat_id, None)
        self.timer_messages.pop(chat_id, None)
        self.active_timers.pop(chat_id, None)

        if chat_id in self.user_tests:
            del self.user_tests[chat_id]