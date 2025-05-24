from telebot import types
import reading.reading_questions
import threading
import time

duration_for_this_test = 35 * 60 + 1

class ReadingTest:
    def __init__(self, bot, user_tests_dict):
        self.bot = bot
        self.user_tests = user_tests_dict
        self.questions = reading.reading_questions.questions
        self.user_answers = {}
        self.user_messages = {}
        self.timer_threads = {}
        self.test_duration = duration_for_this_test
        self.stop_timer_flags = {}
        self.test_start_time = {}
        self.timer_message_id = {}

    def calculate_results(self, chat_id):
        correct_count = 0
        total_questions = len(self.questions)
        results = []

        for idx, (user_answer, question) in enumerate(zip(self.user_answers[chat_id], self.questions)):
            is_multiple = question.get("multiple_answers", False)
            correct_answer = question["correct"]

            if is_multiple:
                user_correct = set(user_answer) == set(correct_answer) if user_answer else False
            else:
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

        result_text = f"📊 Test results:\n\n"
        result_text += f"✅ Correct answers: {correct_count}/{total_questions}\n"
        result_text += f"🔢 Persent: {score:.1f}%\n\n"
        result_text += "Detailed results:\n"

        for result in results:
            question = self.questions[result["question"] - 1]
            user_ans = result["user_answer"]
            correct_ans = result["correct_answer"]

            if isinstance(user_ans, list):
                user_selected = ", ".join([question["options"][i] for i in user_ans]) if user_ans else "No answer"
            else:
                user_selected = question["options"][user_ans] if user_ans is not None else "No answer"

            if isinstance(correct_ans, list):
                correct_selected = ", ".join([question["options"][i] for i in correct_ans])
            else:
                correct_selected = question["options"][correct_ans]

            result_text += f"\n❓ Question {result['question']}:\n"
            result_text += f"   Your answer: {'✅' if result['is_correct'] else '❌'} {user_selected}\n"
            if not result['is_correct']:
                result_text += f"   Correct answer: {correct_selected}\n"

        self.bot.send_message(chat_id, result_text)

    def start_test(self, message):
        chat_id = message.chat.id
        # Инициализируем user_answers правильными типами данных
        self.user_answers[chat_id] = [
            [] if q.get("multiple_answers", False) else None 
            for q in self.questions
        ]
        self.user_messages[chat_id] = []
        self.stop_timer_flags[chat_id] = False

        with open('reading/texts.docx', 'rb') as f:
            self.bot.send_document(chat_id, f)

        for idx, q in enumerate(self.questions):
            markup = types.InlineKeyboardMarkup()
            for i, option in enumerate(q["options"]):
                callback_data = f"q:{idx}:{i}"
                markup.add(types.InlineKeyboardButton(option, callback_data=callback_data))

            sent_msg = self.bot.send_message(chat_id, f"<b>{q['text']}</b>", reply_markup=markup, parse_mode="HTML")
            self.user_messages[chat_id].append(sent_msg.message_id)

        confirm_markup = types.InlineKeyboardMarkup()
        confirm_markup.add(types.InlineKeyboardButton("✅ CONFIRM ANSWERS", callback_data="confirm"))
        self.bot.send_message(chat_id, "When you're done, click 'CONFIRM ANSWERS'.", reply_markup=confirm_markup)

        self.test_start_time[chat_id] = time.time()
        timer_message = self.bot.send_message(chat_id, f"⏳ Time: {self.format_time(self.test_duration)}")
        self.timer_message_id[chat_id] = timer_message.message_id

        timer_thread = threading.Thread(target=self.timer_thread, args=(chat_id,))
        timer_thread.start()
        self.timer_threads[chat_id] = timer_thread

    def handle_answer(self, call):
        chat_id = call.message.chat.id
        if chat_id not in self.user_answers or chat_id not in self.user_messages:
            self.bot.answer_callback_query(call.id, text="Please start the test again /start")
            return

        _, q_idx, option_idx = call.data.split(":")
        q_idx = int(q_idx)
        option_idx = int(option_idx)

        # Удаляем проверку len(self.user_answers[chat_id]) <= q_idx, так как теперь инициализируем все ответы заранее
        is_multiple = self.questions[q_idx].get("multiple_answers", False)

        if is_multiple:
            current_answers = self.user_answers[chat_id][q_idx]
            if option_idx in current_answers:
                current_answers.remove(option_idx)
            else:
                current_answers.append(option_idx)
        else:
            if self.user_answers[chat_id][q_idx] == option_idx:
                self.bot.answer_callback_query(call.id, text="This option has already been selected ✅")
                return
            self.user_answers[chat_id][q_idx] = option_idx

        q = self.questions[q_idx]
        markup = types.InlineKeyboardMarkup()
        for i, option in enumerate(q["options"]):
            if is_multiple:
                text = f"✅ {option}" if i in self.user_answers[chat_id][q_idx] else option
            else:
                text = f"🔵 {option}" if (self.user_answers[chat_id][q_idx] == i) else option
            callback_data = f"q:{q_idx}:{i}"
            markup.add(types.InlineKeyboardButton(text, callback_data=callback_data))

        self.bot.edit_message_reply_markup(chat_id=chat_id,
                                        message_id=self.user_messages[chat_id][q_idx],
                                        reply_markup=markup)

        self.bot.answer_callback_query(call.id)

    def timer_thread(self, chat_id):
        next_update_time = time.time()  # Время следующего обновления
        while True:
            if self.stop_timer_flags.get(chat_id):
                break

            current_time = time.time()
            elapsed = current_time - self.test_start_time[chat_id]
            remaining = self.test_duration - elapsed
            
            if remaining <= 0:
                try:
                    self.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=self.timer_message_id[chat_id],
                        text="⏳ Time's up!"
                    )
                    self.force_finish(chat_id)
                except Exception as e:
                    print(f"Timer error: {e}")
                break

            try:
                # Обновляем таймер только если прошла целая секунда
                if current_time >= next_update_time:
                    self.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=self.timer_message_id[chat_id],
                        text=f"⏳ Time: {self.format_time(remaining)}"
                    )
                    next_update_time = current_time + 1  # Устанавливаем время следующего обновления
            except Exception as e:
                print(f"Timer update error: {e}")

            # Спим оставшееся время до следующего обновления
            sleep_time = max(0, next_update_time - time.time())
            time.sleep(sleep_time)

    def format_time(self, seconds):
        minutes = int(seconds) // 60
        seconds = int(seconds) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def handle_confirm(self, call):
        chat_id = call.message.chat.id
        self.stop_timer_flags[chat_id] = True

        answers = self.user_answers.get(chat_id, [])
        text = "Your answers:\n"
        for idx, answer in enumerate(answers):
            if answer is not None:
                if isinstance(answer, list):
                    selected = ", ".join([self.questions[idx]['options'][i] for i in answer])
                    text += f"Question {idx + 1}: {selected}\n"
                else:
                    text += f"Question {idx + 1}: {self.questions[idx]['options'][answer]}\n"
            else:
                text += f"Question {idx + 1}: no answer\n"

        self.bot.send_message(chat_id, text)
        self.show_results(chat_id)

        if chat_id in self.user_tests:
            del self.user_tests[chat_id]

    def force_finish(self, chat_id):
        self.stop_timer_flags[chat_id] = True
        answers = self.user_answers.get(chat_id, [])
        text = "⏰ Time's up! Your answers:\n"
        for idx, answer in enumerate(answers):
            if answer is not None:
                if isinstance(answer, list):
                    selected = ", ".join([self.questions[idx]['options'][i] for i in answer])
                    text += f"Question {idx + 1}: {selected}\n"
                else:
                    text += f"Question {idx + 1}: {self.questions[idx]['options'][answer]}\n"
            else:
                text += f"Question {idx + 1}: no answer\n"

        self.bot.send_message(chat_id, text)
        self.show_results(chat_id)

        if chat_id in self.user_tests:
            del self.user_tests[chat_id]
