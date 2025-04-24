from telebot import types
import time


class ListeningTest:
    def __init__(self, bot):
        self.bot = bot
        self.questions = [
            {
                'audio_file': 'listening/audio/jingle-bells.ogg',  # путь к файлу
                'options': [
                    'Answer A',
                    'Answer B',
                    'Answer C',
                    'Answer D'
                ],
                'correct_answer': 2
            },
            {
                'audio_file': 'listening/audio/jingle-bells.ogg',
                'options': [
                    'Answer A',
                    'Answer B',
                    'Answer C',
                    'Answer D'
                ],
                'correct_answer': 1
            },
        ]
        self.current_question = 0
        self.score = 0
        self.start_time = time.time()
        self.TEST_DURATION = 2160

    def start_test(self, message):
        self.send_question(message.chat.id)

    def send_question(self, chat_id):
        question_data = self.questions[self.current_question]
        keyboard = types.InlineKeyboardMarkup()

        for i, option in enumerate(question_data['options']):
            keyboard.add(types.InlineKeyboardButton(text=option, callback_data=f'listen_answer_{i}'))

        with open(question_data['audio_file'], 'rb') as audio:
            self.bot.send_audio(chat_id, audio, caption=f"Вопрос {self.current_question + 1}/{len(self.questions)}")

        self.bot.send_message(chat_id, "Выберите правильный ответ:", reply_markup=keyboard)

    def handle_answer(self, call):
        chat_id = call.message.chat.id

        if time.time() - self.start_time > self.TEST_DURATION:
            self.finish_test(chat_id)
            return

        answer_index = int(call.data.split('_')[2])
        question_data = self.questions[self.current_question]

        if answer_index == question_data['correct_answer']:
            self.score += 1

        self.current_question += 1
        if self.current_question < len(self.questions):
            self.send_question(chat_id)
        else:
            self.finish_test(chat_id)

    def finish_test(self, chat_id):
        total = len(self.questions)
        percentage = (self.score / total) * 100

        result_text = f"Тест Listening завершён!\n\nПравильных ответов: {self.score}/{total}\nРезультат: {percentage:.1f}%\n\n"
        result_text += "Правильные ответы:\n"
        for i, q in enumerate(self.questions):
            result_text += f"{i + 1}. {q['options'][q['correct_answer']]}\n"

        self.bot.send_message(chat_id, result_text)