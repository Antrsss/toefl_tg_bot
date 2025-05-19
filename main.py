import telebot
from telebot import types
from reading.reading import ReadingTest
from listening.listening import ListeningTest

bot = telebot.TeleBot('7507944869:AAFQZKisWbLinpBAB2DDCIFBtwtCdjexPb8')

user_tests = {}


@bot.message_handler(content_types=['text'])
def start(message):
    bot.send_message(message.from_user.id, 'Привет! Я бот для прохождения экзамена TOEFL.')
    send_test_type(message)


def send_test_type(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Reading', callback_data='reading'))
    keyboard.add(types.InlineKeyboardButton(text='Listening', callback_data='listening'))
    keyboard.add(types.InlineKeyboardButton(text='Speaking', callback_data='speaking'))
    keyboard.add(types.InlineKeyboardButton(text='Writing', callback_data='writing'))
    bot.send_message(message.chat.id, 'Выберите тип теста:', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data in ["reading", "listening", "speaking", "writing"])
def callback_worker(call):
    chat_id = call.message.chat.id

    if call.data == "reading":
        user_tests[chat_id] = ReadingTest(bot)
        user_tests[chat_id].start_test(call.message)
    elif call.data == "listening":
        user_tests[chat_id] = ListeningTest(bot)
        user_tests[chat_id].start_test(call.message)
    elif call.data == "speaking":
        bot.send_message(chat_id, "Speaking пока не реализован.")
    elif call.data == "writing":
        bot.send_message(chat_id, "Writing пока не реализован.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('answer_') or call.data.startswith('listen_answer_'))
def handle_all_answers(call):
    chat_id = call.message.chat.id
    if chat_id in user_tests:
        user_tests[chat_id].handle_answer(call)


########################################## VLAD INSERT FOR READING ########################################## START

@bot.callback_query_handler(func=lambda call: call.data == "confirm")
def handle_confirm(call):
    chat_id = call.message.chat.id
    if chat_id in user_tests:
        user_tests[chat_id].handle_confirm(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith("q:"))
def handle_reading_answer(call):
    chat_id = call.message.chat.id
    if chat_id in user_tests:
        user_tests[chat_id].handle_answer(call)

@bot.message_handler(commands=['start_listening'])
def start_listening(message):
    ListeningTest.start_test(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("listen_answer_"))
def handle_listening_answer(call):
    ListeningTest.handle_answer(call)

    

    # Здесь можно добавить проверку правильности и вывод баллов, если нужно

########################################## VLAD INSERT FOR READING ########################################## END


if __name__ == '__main__':
    bot.remove_webhook()
    bot.polling(none_stop=True)
