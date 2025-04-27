from telebot import types
import reading.reading_questions
import threading
import time

class ReadingTest:
    def __init__(self, bot):
        self.bot = bot
        self.questions = reading.reading_questions.questions
        self.user_answers = {}
        self.user_messages = {}
        self.timer_threads = {}  # тут будут храниться потоки таймера для каждого чата
        self.test_duration = 2 * 60  # например, 5 минут теста (можешь поставить своё)


    def start_test(self, message):
        chat_id = message.chat.id
        self.user_answers[chat_id] = []
        self.user_messages[chat_id] = []

        # Отправка PDF
        with open('reading/reading_passage.pdf', 'rb') as f:
            self.bot.send_document(chat_id, f)

        # Отправляем вопросы
        for idx, q in enumerate(self.questions):
            markup = types.InlineKeyboardMarkup()
            for i, option in enumerate(q["options"]):
                callback_data = f"q:{idx}:{i}"
                markup.add(types.InlineKeyboardButton(option, callback_data=callback_data))
            
            sent_msg = self.bot.send_message(chat_id, f"<b>{q['text']}</b>", reply_markup=markup, parse_mode="HTML")
            self.user_messages[chat_id].append(sent_msg.message_id)

        # Кнопка "Подтвердить"
        confirm_markup = types.InlineKeyboardMarkup()
        confirm_markup.add(types.InlineKeyboardButton("✅ Подтвердить ответы", callback_data="confirm"))
        self.bot.send_message(chat_id, "Когда закончите, нажмите подтвердить.", reply_markup=confirm_markup)

        # ➡️  Добавляем создание таймера
        self.test_start_time = self.test_start_time if hasattr(self, 'test_start_time') else {}
        self.timer_message_id = self.timer_message_id if hasattr(self, 'timer_message_id') else {}

        self.test_start_time[chat_id] = time.time()

        timer_message = self.bot.send_message(chat_id, f"⏳ Время осталось: {self.format_time(self.test_duration)}")
        self.timer_message_id[chat_id] = timer_message.message_id

        # Запускаем именно timer_thread
        timer_thread = threading.Thread(target=self.timer_thread, args=(chat_id,))
        timer_thread.start()
        self.timer_threads[chat_id] = timer_thread


    def handle_answer(self, call):
        chat_id = call.message.chat.id
        if chat_id not in self.user_answers or chat_id not in self.user_messages:
            self.bot.answer_callback_query(call.id, text="Пожалуйста, начните тест сначала /start")
            return

        # Распарсим данные
        _, q_idx, option_idx = call.data.split(":")
        q_idx = int(q_idx)
        option_idx = int(option_idx)

        # Проверка: если выбран уже этот же вариант — ничего не меняем
        if len(self.user_answers[chat_id]) > q_idx and self.user_answers[chat_id][q_idx] == option_idx:
            self.bot.answer_callback_query(call.id, text="Этот вариант уже выбран ✅")
            return

        # Сохраняем выбор
        while len(self.user_answers[chat_id]) <= q_idx:
            self.user_answers[chat_id].append(None)
        self.user_answers[chat_id][q_idx] = option_idx

        # Обновляем клавиатуру
        q = self.questions[q_idx]
        markup = types.InlineKeyboardMarkup()
        for i, option in enumerate(q["options"]):
            text = f"🔵 {option} (выбрано)" if i == option_idx else option
            callback_data = f"q:{q_idx}:{i}"
            markup.add(types.InlineKeyboardButton(text, callback_data=callback_data))

        # Редактируем сообщение
        self.bot.edit_message_reply_markup(chat_id=chat_id,
                                           message_id=self.user_messages[chat_id][q_idx],
                                           reply_markup=markup)

        self.bot.answer_callback_query(call.id, text=f"Вы выбрали: {q['options'][option_idx]}")


    def timer_thread(self, chat_id):
        while True:
            elapsed = time.time() - self.test_start_time[chat_id]
            remaining = self.test_duration - elapsed
            if remaining <= 0:
                # Время вышло!
                try:
                    self.bot.edit_message_text(chat_id=chat_id,
                                               message_id=self.timer_message_id[chat_id],
                                               text="⏳ Время вышло!")
                    self.force_finish(chat_id)
                except Exception as e:
                    print(e)
                break

            try:
                self.bot.edit_message_text(chat_id=chat_id,
                                           message_id=self.timer_message_id[chat_id],
                                           text=f"⏳ Время осталось: {self.format_time(remaining)}")
            except Exception as e:
                print(e)


            time.sleep(1)


    def format_time(self, seconds):
        minutes = int(seconds) // 60
        seconds = int(seconds) % 60
        return f"{minutes:02d}:{seconds:02d}"


    def handle_confirm(self, call):
        chat_id = call.message.chat.id
        answers = self.user_answers.get(chat_id, [])
        text = "Ваши ответы:\n"
        for idx, answer in enumerate(answers):
            if answer is not None:
                text += f"Вопрос {idx+1}: {self.questions[idx]['options'][answer]}\n"
            else:
                text += f"Вопрос {idx+1}: нет ответа\n"
        self.bot.send_message(chat_id, text)


    def force_finish(self, chat_id):
        # Завершаем тест автоматически
        answers = self.user_answers.get(chat_id, [])
        text = "⏰ Время вышло! Ваши ответы:\n"
        for idx, answer in enumerate(answers):
            if answer is not None:
                text += f"Вопрос {idx+1}: {self.questions[idx]['options'][answer]}\n"
            else:
                text += f"Вопрос {idx+1}: нет ответа\n"
        self.bot.send_message(chat_id, text)


    # Здесь можно добавить проверку правильности и вывод баллов, если нужно

        # def __init__(self, bot):
        # self.bot = bot
        # self.questions = [
        #     {
        #         'question': 'Текст вопроса 1...',
        #         'options': [
        #             'Вариант ответа 1',
        #             'Вариант ответа 2',
        #             'Вариант ответа 3',
        #             'Вариант ответа 4'
        #         ],
        #         'correct_answer': 0  # Индекс правильного ответа
        #     },
        #     {
        #         'question': 'Текст вопроса 2...',
        #         'options': [
        #             'Вариант ответа 1',
        #             'Вариант ответа 2',
        #             'Вариант ответа 3',
        #             'Вариант ответа 4'
        #         ],
        #         'correct_answer': 1
        #     },
        # ]
        # self.current_question = 0
        # self.score = 0
        # self.start_time = time.time()
        # self.TEST_DURATION = 2100

    # def start_test(self, message):
    #     self.send_question(message.chat.id)

    # def send_question(self, chat_id):
    #     question_data = self.questions[self.current_question]
    #     keyboard = types.InlineKeyboardMarkup()

    #     for i, option in enumerate(question_data['options']):
    #         keyboard.add(types.InlineKeyboardButton(text=option, callback_data=f'answer_{i}'))

    #     question_text = f"Вопрос {self.current_question + 1}/{len(self.questions)}\n\n{question_data['question']}"
    #     self.bot.send_message(chat_id, question_text, reply_markup=keyboard)

    # def handle_answer(self, call):
    #     if self.current_question >= len(self.questions):
    #         print("No more questions left.")  # Debug
    #         self.finish_test(call.message.chat.id)
    #         return

    #     try:
    #         chat_id = call.message.chat.id
    #         print(f"Handling answer for chat {chat_id}, current question: {self.current_question}")  # Debug log

    #         # Проверяем, не завершился ли тест по времени
    #         if time.time() - self.start_time > self.TEST_DURATION:
    #             print("Test time expired")  # Debug log
    #             self.finish_test(chat_id)
    #             return

    #         # Получаем индекс ответа пользователя
    #         try:
    #             answer_index = int(call.data.split('_')[1])
    #             print(f"User selected answer {answer_index}")  # Debug log
    #         except (IndexError, ValueError) as e:
    #             print(f"Error parsing answer: {e}")  # Debug log
    #             self.bot.send_message(chat_id, "Произошла ошибка обработки ответа. Пожалуйста, попробуйте ещё раз.")
    #             return

    #         # Проверяем правильность ответа
    #         current_question_data = self.questions[self.current_question]
    #         if answer_index == current_question_data['correct_answer']:
    #             self.score += 1
    #             print("Answer is correct")  # Debug log
    #         else:
    #             print("Answer is wrong")  # Debug log

    #         # Удаляем предыдущее сообщение с вопросом (чтобы избежать накопления сообщений)
    #         try:
    #             self.bot.delete_message(chat_id, call.message.message_id)
    #             print("Previous question message deleted")  # Debug log
    #         except Exception as e:
    #             print(f"Could not delete message: {e}")  # Debug log

    #         # Переходим к следующему вопросу
    #         self.current_question += 1

    #         if self.current_question < len(self.questions):
    #             print(f"Moving to question {self.current_question}")  # Debug log
    #             self.send_question(chat_id)
    #         else:
    #             print("Test completed")  # Debug log
    #             self.finish_test(chat_id)

    #     except Exception as e:
    #         print(f"Unexpected error in handle_answer: {e}")  # Debug log
    #         self.bot.send_message(chat_id, "Произошла непредвиденная ошибка. Тест будет перезапущен.")
    #         self.finish_test(chat_id)

    # def finish_test(self, chat_id):
    #     total = len(self.questions)
    #     percentage = (self.score / total) * 100

    #     result_text = f"Тест завершен!\n\nПравильных ответов: {self.score}/{total}\nРезультат: {percentage:.1f}%\n\n"
    #     result_text += "Правильные ответы:\n"
    #     for i, question in enumerate(self.questions):
    #         result_text += f"{i + 1}. {question['options'][question['correct_answer']]}\n"

    #     self.bot.send_message(chat_id, result_text)