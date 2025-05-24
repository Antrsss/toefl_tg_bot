import telebot
from telebot import types
from reading.reading import ReadingTest
from listening.listening import ListeningTest
from speaking.speaking import SpeakingTest
from writing.writing import WritingTest

bot = telebot.TeleBot('7507944869:AAFQZKisWbLinpBAB2DDCIFBtwtCdjexPb8')

user_tests = {}

@bot.message_handler(content_types=['voice'])
def handle_voice_message(message):
    chat_id = message.chat.id
    if chat_id in user_tests and isinstance(user_tests[chat_id], SpeakingTest):
        user_tests[chat_id].handle_voice(message)

#################################################################################### Text message handler

# new version of text handler
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id

    if chat_id in user_tests:
        test = user_tests[chat_id]
        if isinstance(test, WritingTest):
            return test.handle_text(message)
        # в остальных тестах текст от пользователя игнорируется
        return

    # нет активного теста — показываем меню
    bot.send_message(chat_id, "Hello! I'm TOEFL-bot.")
    send_test_type(message)

####################################################################################

def send_test_type(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Reading', callback_data='reading'))
    keyboard.add(types.InlineKeyboardButton(text='Listening', callback_data='listening'))
    keyboard.add(types.InlineKeyboardButton(text='Speaking', callback_data='speaking'))
    keyboard.add(types.InlineKeyboardButton(text='Writing', callback_data='writing'))
    bot.send_message(message.chat.id, 'Select test type:', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data in ["reading", "listening", "speaking", "writing"])
def callback_worker(call): # delete this message after choice of section
    chat_id = call.message.chat.id

    if chat_id in user_tests:
        bot.answer_callback_query(call.id, text="❗ You have already started the test. Finish it first.")
        bot.edit_message_reply_markup(chat_id=chat_id,
                                 message_id=call.message.message_id,
                                 reply_markup=None)
        return

    bot.edit_message_reply_markup(chat_id=chat_id,
                                 message_id=call.message.message_id,
                                 reply_markup=None)

    if call.data == "reading":
        user_tests[chat_id] = ReadingTest(bot, user_tests)
        user_tests[chat_id].start_test(call.message)
    elif call.data == "listening":
        user_tests[chat_id] = ListeningTest(bot, user_tests)
        user_tests[chat_id].start_test(call.message)
    elif call.data == "speaking":
        user_tests[chat_id] = SpeakingTest(bot, user_tests)
        user_tests[chat_id].start_test(call.message)
    elif call.data == "writing":
        user_tests[chat_id] = WritingTest(bot, user_tests)
        user_tests[chat_id].start_test(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('answer_') or call.data.startswith('listen_answer_'))
def handle_all_answers(call):
    chat_id = call.message.chat.id
    if chat_id in user_tests:
        user_tests[chat_id].handle_answer(call)
        
@bot.callback_query_handler(func=lambda call: call.data.startswith('finish_writing_'))
def handle_finish_writing(call):
    chat_id = int(call.data.split('_')[2])
    if chat_id in user_tests and isinstance(user_tests[chat_id], WritingTest):
        user_tests[chat_id].finish_early(chat_id)
    bot.answer_callback_query(call.id)


########################################## VLAD INSERT FOR READING ########################################## START

@bot.callback_query_handler(func=lambda call: call.data == "confirm")
def handle_confirm(call):
    chat_id = call.message.chat.id
    if chat_id in user_tests:
        user_tests[chat_id].handle_confirm(call)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("q:"))
def handle_reading_answer(call):
    chat_id = call.message.chat.id
    if chat_id in user_tests:
        user_tests[chat_id].handle_answer(call)

@bot.message_handler(commands=['start_listening'])
def start_listening(message):
    ListeningTest.start_test(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('listen_'))
def handle_listening_callbacks(call):
    chat_id = call.message.chat.id
    if chat_id in user_tests and isinstance(user_tests[chat_id], ListeningTest):
        if call.data.startswith('listen_answer_'):
            user_tests[chat_id].handle_answer(call)
        elif call.data.startswith('listen_finish_'):
            # Получаем chat_id из callback_data
            try:
                finish_chat_id = int(call.data.split('_')[2])
                user_tests[finish_chat_id].finish_test(finish_chat_id)
            except (IndexError, ValueError):
                user_tests[chat_id].finish_test(chat_id)
    


if __name__ == '__main__':
    bot.remove_webhook()
    bot.polling(none_stop=True)
