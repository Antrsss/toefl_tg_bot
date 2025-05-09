from telebot import types
import time
import os
import listening.listening_questions


class ListeningTest:
    def __init__(self, bot):
        self.bot = bot
        self.questions = listening.listening_questions.l_questions
        self.current_question = 0
        self.score = 0
        self.start_time = time.time()
        self.TEST_DURATION = 1200  # 20 minutes in seconds
        self.current_audio_file = None

    def start_test(self, message):
        instructions = """Listening Section
        \nListening Section Instructions
        In this section you will hear six lectures and conversations to test your listening comprehension skills. Each lecture or conversation will only be played once. Following the conversation, you will be asked to answer a series of questions. The questions may ask about the main idea or other details. Other questions may ask about the speaker's stance or purpose.
        \nListen carefully and answer based on what the speaker says or implies.
        \nYou may use a sheet of paper to take notes. These notes can be used to help you answer the questions. Notes are not scored.
        \nYou will have a total of 36 minutes to answer all questions.
        \nNote: In the actual test, you will not be able to return to a question after answering it."""

        self.bot.send_message(message.chat.id, instructions)
        time.sleep(2)
        self.send_question(message.chat.id)

    def send_question(self, chat_id):
        if self.current_question >= len(self.questions):
            self.finish_test(chat_id)
            return

        question_data = self.questions[self.current_question]
        keyboard = types.InlineKeyboardMarkup()

        for i, option in enumerate(question_data['options']):
            keyboard.add(types.InlineKeyboardButton(text=option, callback_data=f'listen_answer_{i}'))

        if question_data['audio_file'] and question_data['audio_file'] != self.current_audio_file:
            try:
                with open(question_data['audio_file'], 'rb') as audio:
                    self.bot.send_audio(
                        chat_id,
                        audio,
                        caption=f"Question {self.current_question + 1}/{len(self.questions)}",
                        timeout=30
                    )
                    self.current_audio_file = question_data['audio_file']
            except Exception as e:
                print(f"Error sending audio: {e}")
                self.bot.send_message(
                    chat_id,
                    f"Audio not available for question {self.current_question + 1}. Continuing with text only."
                )

        self.bot.send_message(
            chat_id,
            f"Question {self.current_question + 1}/{len(self.questions)}\n\n{question_data['text']}",
            reply_markup=keyboard
        )

    def handle_answer(self, call):
        chat_id = call.message.chat.id

        if time.time() - self.start_time > self.TEST_DURATION:
            return self.finish_test(chat_id)

        answer_index = int(call.data.split('_')[2])
        question_data = self.questions[self.current_question]

        if answer_index == question_data['correct_answer']:
            self.score += 1

        self.current_question += 1
        if self.current_question < len(self.questions):
            self.send_question(chat_id)
        else:
            return self.finish_test(chat_id)

    def finish_test(self, chat_id):
        total = len(self.questions)
        percentage = (self.score / total) * 100

        result_text = f"Listening Test Completed!\n\nCorrect answers: {self.score}/{total}\nScore: {percentage:.1f}%\n\n"
        result_text += "Correct answers:\n"
        for i, q in enumerate(self.questions):
            result_text += f"{i + 1}. {q['options'][q['correct_answer']]}\n"

        self.bot.send_message(chat_id, result_text)
        return True  # Сигнал о завершении теста