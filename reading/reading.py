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

    def calculate_results(self, chat_id):
        correct_count = 0
        total_questions = len(self.questions)
        results = []

        for idx, (user_answer, question) in enumerate(zip(self.user_answers[chat_id], self.questions)):
            is_multiple = question.get("multiple_answers", False)
            correct_answer = question["correct"]

            if is_multiple:
                # Для вопросов с множественным выбором
                user_correct = set(user_answer) == set(correct_answer) if user_answer else False
            else:
                # Для вопросов с одним ответом
                user_correct = user_answer == correct_answer if user_answer is not None else False

            if user_correct:
                correct_count += 1

            results.append({
                "question": idx + 1,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": user_correct
            })

        score = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        return results, score, correct_count, total_questions

    def show_results(self, chat_id):
        results, score, correct_count, total_questions = self.calculate_results(chat_id)

        result_text = f"📊 Результаты теста:\n\n"
        result_text += f"✅ Правильных ответов: {correct_count}/{total_questions}\n"
        result_text += f"🔢 Процент правильных: {score:.1f}%\n\n"
        result_text += "Подробные результаты:\n"

        for result in results:
            question = self.questions[result["question"] - 1]
            user_ans = result["user_answer"]
            correct_ans = result["correct_answer"]

            if isinstance(user_ans, list):  # Множественный выбор
                user_selected = ", ".join([question["options"][i] for i in user_ans]) if user_ans else "Нет ответа"
                correct_selected = ", ".join([question["options"][i] for i in correct_ans])
            else:  # Одиночный выбор
                user_selected = question["options"][user_ans] if user_ans is not None else "Нет ответа"
                correct_selected = question["options"][correct_ans]

            result_text += f"\n❓ Вопрос {result['question']}:\n"
            result_text += f"   Ваш ответ: {'✅' if result['is_correct'] else '❌'} {user_selected}\n"
            if not result['is_correct']:
                result_text += f"   Правильный ответ: {correct_selected}\n"

        self.bot.send_message(chat_id, result_text)

    def start_test(self, message):
        chat_id = message.chat.id
        self.user_answers[chat_id] = []
        self.user_messages[chat_id] = []

        # Отправка PDF
        with open('reading/texts.docx', 'rb') as f:
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

        # Инициализируем список ответов для вопроса, если его еще нет
        while len(self.user_answers[chat_id]) <= q_idx:
            self.user_answers[chat_id].append([] if self.questions[q_idx].get("multiple_answers", False) else None)

        # Проверяем, является ли вопрос с множественным выбором
        is_multiple = self.questions[q_idx].get("multiple_answers", False)

        if is_multiple:
            # Для вопросов с множественным выбором
            current_answers = self.user_answers[chat_id][q_idx]

            # Добавляем или удаляем выбранный вариант
            if option_idx in current_answers:
                current_answers.remove(option_idx)
            else:
                current_answers.append(option_idx)
        else:
            # Для обычных вопросов с одним ответом
            # Проверка: если выбран уже этот же вариант — ничего не меняем
            if self.user_answers[chat_id][q_idx] == option_idx:
                self.bot.answer_callback_query(call.id, text="Этот вариант уже выбран ✅")
                return

            # Сохраняем выбор
            self.user_answers[chat_id][q_idx] = option_idx

        # Обновляем клавиатуру
        q = self.questions[q_idx]
        markup = types.InlineKeyboardMarkup()
        for i, option in enumerate(q["options"]):
            if is_multiple:
                # Для множественного выбора показываем выбранные варианты
                text = f"✅ {option}" if i in self.user_answers[chat_id][q_idx] else option
            else:
                # Для одиночного выбора
                text = f"🔵 {option}" if (self.user_answers[chat_id][q_idx] == i) else option

            callback_data = f"q:{q_idx}:{i}"
            markup.add(types.InlineKeyboardButton(text, callback_data=callback_data))

        # Редактируем сообщение
        self.bot.edit_message_reply_markup(chat_id=chat_id,
                                           message_id=self.user_messages[chat_id][q_idx],
                                           reply_markup=markup)

        self.bot.answer_callback_query(call.id)


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
                if isinstance(answer, list):  # Для множественного выбора
                    selected = ", ".join([self.questions[idx]['options'][i] for i in answer])
                    text += f"Вопрос {idx + 1}: {selected}\n"
                else:  # Для одиночного выбора
                    text += f"Вопрос {idx + 1}: {self.questions[idx]['options'][answer]}\n"
            else:
                text += f"Вопрос {idx + 1}: нет ответа\n"

        self.bot.send_message(chat_id, text)
        self.show_results(chat_id)

    def force_finish(self, chat_id):
        answers = self.user_answers.get(chat_id, [])
        text = "⏰ Время вышло! Ваши ответы:\n"
        for idx, answer in enumerate(answers):
            if answer is not None:
                text += f"Вопрос {idx + 1}: {self.questions[idx]['options'][answer]}\n"
            else:
                text += f"Вопрос {idx + 1}: нет ответа\n"

        self.bot.send_message(chat_id, text)
        self.show_results(chat_id)  # Добавляем показ результатов
