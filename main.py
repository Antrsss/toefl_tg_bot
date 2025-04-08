import telebot
from telebot import types
from reading.reading import start_reading_test, handle_reading_answer
from listening.listening import start_listening_test, handle_listening_answer

bot = telebot.TeleBot('7507944869:AAFQZKisWbLinpBAB2DDCIFBtwtCdjexPb8')

handle_reading_answer(bot)
handle_listening_answer(bot)

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

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    if call.data == "reading":
        start_reading_test(call.message, bot)
    elif call.data == "listening":
        start_listening_test(call.message, bot)
    elif call.data == "speaking":
        bot.send_message(call.message.chat.id, "Speaking пока не реализован.")
    elif call.data == "writing":
        bot.send_message(call.message.chat.id, "Writing пока не реализован.")

if __name__ == '__main__':
    bot.polling(none_stop=True)
