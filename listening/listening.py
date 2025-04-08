from telebot import types
from listening.listening_questions import listening_questions
import time

user_data = {}
TEST_DURATION = 2160  # 36 минут на весь listening тест

def start_listening_test(message, bot):
    chat_id = message.chat.id
    user_data[chat_id] = {
        'current_test': 'listening',
        'start_time': time.time(),
        'current_question': 0,
        'answers': [],
        'score': 0
    }
    send_listening_question(chat_id, bot)

def send_listening_question(chat_id, bot):
    q_index = user_data[chat_id]['current_question']
    question_data = listening_questions[q_index]
    keyboard = types.InlineKeyboardMarkup()

    for i, option in enumerate(question_data['options']):
        keyboard.add(types.InlineKeyboardButton(text=option, callback_data=f'listen_answer_{i}'))

    # Отправляем аудио без возможности перемотки
    with open(question_data['audio_file'], 'rb') as audio:
        bot.send_audio(chat_id, audio, caption=f"Вопрос {q_index + 1}/{len(listening_questions)}")

    # Далее – варианты ответа
    bot.send_message(chat_id, "Выберите правильный ответ:", reply_markup=keyboard)

def finish_listening_test(chat_id, bot):
    score = user_data[chat_id]['score']
    total = len(listening_questions)
    percentage = (score / total) * 100

    result_text = f"Тест Listening завершён!\n\nПравильных ответов: {score}/{total}\nРезультат: {percentage:.1f}%\n\n"
    result_text += "Правильные ответы:\n"
    for i, q in enumerate(listening_questions):
        result_text += f"{i + 1}. {q['options'][q['correct_answer']]}\n"

    bot.send_message(chat_id, result_text)
    del user_data[chat_id]

def handle_listening_answer(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith('listen_answer_'))
    def handle_answer(call):
        chat_id = call.message.chat.id
        if chat_id not in user_data or user_data[chat_id]['current_test'] != 'listening':
            return

        if time.time() - user_data[chat_id]['start_time'] > TEST_DURATION:
            finish_listening_test(chat_id, bot)
            return

        answer_index = int(call.data.split('_')[2])
        question_index = user_data[chat_id]['current_question']
        correct_answer = listening_questions[question_index]['correct_answer']

        user_data[chat_id]['answers'].append({
            'question': question_index,
            'user_answer': answer_index,
            'is_correct': answer_index == correct_answer
        })

        if answer_index == correct_answer:
            user_data[chat_id]['score'] += 1

        user_data[chat_id]['current_question'] += 1
        if user_data[chat_id]['current_question'] < len(listening_questions):
            send_listening_question(chat_id, bot)
        else:
            finish_listening_test(chat_id, bot)
