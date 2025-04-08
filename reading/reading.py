from telebot import types
from reading.reading_questions import reading_questions
import time

user_data = {}
TEST_DURATION = 2100

def start_reading_test(message, bot):
    chat_id = message.chat.id
    user_data[chat_id] = {
        'current_test': 'reading',
        'start_time': time.time(),
        'current_question': 0,
        'answers': [],
        'score': 0
    }
    send_reading_question(chat_id, bot)

def send_reading_question(chat_id, bot):
    question_data = reading_questions[user_data[chat_id]['current_question']]
    keyboard = types.InlineKeyboardMarkup()

    for i, option in enumerate(question_data['options']):
        keyboard.add(types.InlineKeyboardButton(text=option, callback_data=f'answer_{i}'))

    question_text = f"Вопрос {user_data[chat_id]['current_question'] + 1}/{len(reading_questions)}\n\n{question_data['question']}"
    bot.send_message(chat_id, question_text, reply_markup=keyboard)

def finish_reading_test(chat_id, bot):
    score = user_data[chat_id]['score']
    total = len(reading_questions)
    percentage = (score / total) * 100

    result_text = f"Тест завершен!\n\nПравильных ответов: {score}/{total}\nРезультат: {percentage:.1f}%\n\n"
    result_text += "Правильные ответы:\n"
    for i, question in enumerate(reading_questions):
        result_text += f"{i + 1}. {question['options'][question['correct_answer']]}\n"

    bot.send_message(chat_id, result_text)
    del user_data[chat_id]

def handle_reading_answer(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith('answer_'))
    def handle_answer(call):
        chat_id = call.message.chat.id
        if chat_id not in user_data or user_data[chat_id]['current_test'] != 'reading':
            return

        if time.time() - user_data[chat_id]['start_time'] > TEST_DURATION:
            finish_reading_test(chat_id, bot)
            return

        answer_index = int(call.data.split('_')[1])
        question_index = user_data[chat_id]['current_question']
        correct_answer = reading_questions[question_index]['correct_answer']

        user_data[chat_id]['answers'].append({
            'question': question_index,
            'user_answer': answer_index,
            'is_correct': answer_index == correct_answer
        })

        if answer_index == correct_answer:
            user_data[chat_id]['score'] += 1

        user_data[chat_id]['current_question'] += 1
        if user_data[chat_id]['current_question'] < len(reading_questions):
            send_reading_question(chat_id, bot)
        else:
            finish_reading_test(chat_id, bot)
