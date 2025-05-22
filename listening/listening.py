import time
from telebot import types
import listening.listening_questions

class ListeningTest:
    def __init__(self, bot):
        self.bot = bot
        self.questions = listening.listening_questions.l_questions
        self.current_question_index = {}  # chat_id -> current question index
        self.user_answers = {}            # chat_id -> list of answers
        self.scores = {}                  # chat_id -> score
        self.start_times = {}             # chat_id -> start time
        self.TEST_DURATION = 36 * 60
        self.current_audio_file = {}      # chat_id -> audio file name

    def start_test(self, message):
        chat_id = message.chat.id
        self.current_question_index[chat_id] = 0
        self.user_answers[chat_id] = [-1] * len(self.questions)
        self.scores[chat_id] = 0
        self.start_times[chat_id] = time.time()
        self.current_audio_file[chat_id] = None

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
        time.sleep(2)
        self.send_question(chat_id)

    def send_question(self, chat_id):
        index = self.current_question_index.get(chat_id, 0)

        if time.time() - self.start_times[chat_id] > self.TEST_DURATION:
            return self.finish_test(chat_id)

        if index >= len(self.questions):
            return self.finish_test(chat_id)

        question = self.questions[index]
        keyboard = types.InlineKeyboardMarkup()

        selected = self.user_answers[chat_id][index]
        for i, option in enumerate(question['options']):
            text = f"🔵 {option}" if i == selected else option
            keyboard.add(types.InlineKeyboardButton(text=text, callback_data=f'listen_answer_{i}'))

        audio_file = question.get("audio_file")
        if audio_file and self.current_audio_file[chat_id] != audio_file:
            try:
                with open(audio_file, 'rb') as audio:
                    self.bot.send_audio(chat_id, audio, caption=f"🎧 Audio for Question {index + 1}", timeout=30)
                    self.current_audio_file[chat_id] = audio_file
            except Exception as e:
                print(f"Audio error: {e}")
                self.bot.send_message(chat_id, f"(⚠️ Audio unavailable for question {index + 1})")

        self.bot.send_message(
            chat_id,
            f"*Question {index + 1}/{len(self.questions)}*\n\n{question['text']}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    def handle_answer(self, call):
        chat_id = call.message.chat.id
        index = self.current_question_index.get(chat_id, 0)

        if chat_id not in self.user_answers:
            return self.bot.send_message(chat_id, "❗️ Please start the test first by sending /start_listening.")

        if index >= len(self.questions):
            return self.finish_test(chat_id)

        if time.time() - self.start_times[chat_id] > self.TEST_DURATION:
            return self.finish_test(chat_id)

        try:
            answer_index = int(call.data.split('_')[2])
        except (IndexError, ValueError):
            return

        question = self.questions[index]
        self.user_answers[chat_id][index] = answer_index

        keyboard = types.InlineKeyboardMarkup()
        for i, option in enumerate(question['options']):
            text = f"🔵 {option}" if i == answer_index else option
            keyboard.add(types.InlineKeyboardButton(text=text, callback_data=f'listen_answer_{i}'))

        try:
            self.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Edit message error: {e}")

        if answer_index == question['correct_answer']:
            self.scores[chat_id] += 1

        self.current_question_index[chat_id] += 1
        time.sleep(0.5)
        self.send_question(chat_id)

    def finish_test(self, chat_id):
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

        self.current_question_index.pop(chat_id, None)
        self.user_answers.pop(chat_id, None)
        self.scores.pop(chat_id, None)
        self.start_times.pop(chat_id, None)
        self.current_audio_file.pop(chat_id, None)
