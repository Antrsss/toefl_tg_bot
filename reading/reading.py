from telebot import types
import time


class ReadingTest:
    def __init__(self, bot):
        self.bot = bot
        self.questions = [
            {
                'question': 'Текст вопроса 1...',
                'options': [
                    'Вариант ответа 1',
                    'Вариант ответа 2',
                    'Вариант ответа 3',
                    'Вариант ответа 4'
                ],
                'correct_answer': 0  # Индекс правильного ответа
            },
            {
                'question': 'Текст вопроса 2...',
                'options': [
                    'Вариант ответа 1',
                    'Вариант ответа 2',
                    'Вариант ответа 3',
                    'Вариант ответа 4'
                ],
                'correct_answer': 1
            },
        ]
        self.current_question = 0
        self.score = 0
        self.start_time = time.time()
        self.TEST_DURATION = 2100

    def start_test(self, message):
        self.send_question(message.chat.id)

    def send_question(self, chat_id):
        question_data = self.questions[self.current_question]
        keyboard = types.InlineKeyboardMarkup()

        for i, option in enumerate(question_data['options']):
            keyboard.add(types.InlineKeyboardButton(text=option, callback_data=f'answer_{i}'))

        question_text = f"Вопрос {self.current_question + 1}/{len(self.questions)}\n\n{question_data['question']}"
        self.bot.send_message(chat_id, question_text, reply_markup=keyboard)

    def handle_answer(self, call):
        if self.current_question >= len(self.questions):
            print("No more questions left.")  # Debug
            self.finish_test(call.message.chat.id)
            return

        try:
            chat_id = call.message.chat.id
            print(f"Handling answer for chat {chat_id}, current question: {self.current_question}")  # Debug log

            # Проверяем, не завершился ли тест по времени
            if time.time() - self.start_time > self.TEST_DURATION:
                print("Test time expired")  # Debug log
                self.finish_test(chat_id)
                return

            # Получаем индекс ответа пользователя
            try:
                answer_index = int(call.data.split('_')[1])
                print(f"User selected answer {answer_index}")  # Debug log
            except (IndexError, ValueError) as e:
                print(f"Error parsing answer: {e}")  # Debug log
                self.bot.send_message(chat_id, "Произошла ошибка обработки ответа. Пожалуйста, попробуйте ещё раз.")
                return

            # Проверяем правильность ответа
            current_question_data = self.questions[self.current_question]
            if answer_index == current_question_data['correct_answer']:
                self.score += 1
                print("Answer is correct")  # Debug log
            else:
                print("Answer is wrong")  # Debug log

            # Удаляем предыдущее сообщение с вопросом (чтобы избежать накопления сообщений)
            try:
                self.bot.delete_message(chat_id, call.message.message_id)
                print("Previous question message deleted")  # Debug log
            except Exception as e:
                print(f"Could not delete message: {e}")  # Debug log

            # Переходим к следующему вопросу
            self.current_question += 1

            if self.current_question < len(self.questions):
                print(f"Moving to question {self.current_question}")  # Debug log
                self.send_question(chat_id)
            else:
                print("Test completed")  # Debug log
                self.finish_test(chat_id)

        except Exception as e:
            print(f"Unexpected error in handle_answer: {e}")  # Debug log
            self.bot.send_message(chat_id, "Произошла непредвиденная ошибка. Тест будет перезапущен.")
            self.finish_test(chat_id)

    def finish_test(self, chat_id):
        total = len(self.questions)
        percentage = (self.score / total) * 100

        result_text = f"Тест завершен!\n\nПравильных ответов: {self.score}/{total}\nРезультат: {percentage:.1f}%\n\n"
        result_text += "Правильные ответы:\n"
        for i, question in enumerate(self.questions):
            result_text += f"{i + 1}. {question['options'][question['correct_answer']]}\n"

        self.bot.send_message(chat_id, result_text)