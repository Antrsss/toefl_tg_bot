import asyncio
import threading
from telebot import types
import os

class SpeakingTest:
    def __init__(self, bot, user_tests_dict):
        self.bot = bot
        self.user_tests = user_tests_dict
        self.questions = [
            {
                "type": "open",
                "text": (
                    "🗣 *Speaking Task 1*\n"
                    "Some people prefer to focus on activities that help their local towns or communities. "
                    "Others prefer to spend their time and energy on national issues that involve the whole country.\n\n"
                    "Which do you prefer and why?\n\n"
                    "⏳ *Preparation Time:* 15 seconds\n"
                    "🎤 *Response Time:* 45 seconds"
                ),
                "prep_time": 15,
                "response_time": 45
            },
            {
                "type": "reading",
                "text": (
                    "📖 *Speaking Task 2 - Reading*\n"
                    "INTRODUCTION TO ENVIRONMENTAL SCIENCE\n\n"
                    "Winter Term: Monday, Wednesday, and Friday 10:30 PM - 11:20 PM, Room 315 Morris Hall\n"
                    "Instructor: Amy Hansen, Assistant Professor of Geology and Environmental Science\n\n"
                    "*Cell Phone Policy:* Cell phone use in the classroom interrupts the lesson, "
                    "causing both students and the instructor to lose focus. It is important to create a"
                    "productive classroom environment that is polite and respectful to all students." 
                    "Therefore, cell phone use for the purposes of texting, email, or other social media is not permitted in this class. " 
                    "Your cell phone must be turned off, placed in your backpack or bag, and put under your seat during lectures." 
                    "Please let me know if there is a serious need to leave your cell phone on, such as a family emergency, " 
                    "so that when you leave the classroom to take a call, I will understand why."
                    "Any student who is observed using their cell phone during class without permission will be asked to leave immediately."
                ),
                "follow_up": (
                    "🎤 *Task:* The man expresses his opinion about a new policy described in the class syllabus.\n"
                    "State his opinion and explain his reasons for that opinion.\n\n"
                    "⏳ *Preparation Time:* 30 seconds\n"
                    "🎤 *Response Time:* 60 seconds"
                ),
                "reading_time": 45,
                "prep_time": 30,
                "response_time": 60
            },
            {
                "type": "reading",
                "text": (
                    "📖 *Speaking Task 3 - Reading*\n"
                    "The Human Skin\n\n"
                    "Not all human organs are inside the body like the brain or heart are. "
                    "The body's largest organ, the skin, is on the outside. In adults, the skin weighs about eight pounds (3.6 kilograms) " 
                    "on average, depending on body weight, and covers a surface area of approximately 22 square feet (2 square meters). "
                    "The skin is full of nerves that connect our brains to the environment outside of us, allowing it to sense and react to pain, " 
                    "pressure, temperature, and much more. It is composed of three layers: at the top, the epidermis, which is visible; "
                    "in the middle, the dermis where hair production begins; and the deepest layer, the hypodermis, which stores fat. "
                    "These layers act together to protect us against extreme temperature, harmful sunlight, and dangerous chemicals."
                ),
                "follow_up": (
                    "🎤 *Task:* Using the example of goosebumps discussed by the professor, "
                    "explain how it illustrates the ways in which the human skin reacts.\n\n"
                    "⏳ *Preparation Time:* 30 seconds\n"
                    "🎤 *Response Time:* 60 seconds"
                ),
                "reading_time": 45,
                "prep_time": 30,
                "response_time": 60
            },
            {
                "type": "listening",
                "intro_text": (
                    "🎧 *Speaking Task 4 - Listening*\n"
                    "Listen to part of the lecture from a business administration class."
                ),
                "audio_path": "speaking/business_lecture.ogg",
                "audio_duration": 117,  # 1 minute 57 seconds (like audiofile)
                "follow_up": (
                    "🎤 *Task:* Using points and examples from the lecture, "
                    "summarize the main features of agile project management.\n\n"
                    "⏳ *Preparation Time:* 20 seconds\n"
                    "🎤 *Response Time:* 60 seconds"
                ),
                "prep_time": 20,
                "response_time": 60
            }
        ]
        self.active_users = {}

    async def send_timer(self, chat_id, seconds, label, stop_event=None):
        msg = self.bot.send_message(chat_id, f"⏳ {label}: {seconds} sec...")
        while seconds > 0:
            if stop_event and stop_event.is_set():
                try:
                    self.bot.edit_message_text(f"⏹ {label} stopped by user.", chat_id, msg.message_id)
                except:
                    pass
                return
            await asyncio.sleep(1)
            seconds -= 1
            try:
                self.bot.edit_message_text(f"⏳ {label}: {seconds} sec...", chat_id, msg.message_id)
            except:
                pass
        self.bot.send_message(chat_id, f"⏱ {label} completed!")

    def start_test(self, message):
        thread = threading.Thread(target=self._start_async_loop, args=(message.chat.id,))
        thread.start()

    def _start_async_loop(self, chat_id):
        asyncio.run(self._run_test(chat_id))

    async def _run_test(self, chat_id):
        self.bot.send_message(chat_id, "🎙 *Speaking Section Started*", parse_mode="Markdown")

        for task in self.questions:
            self.active_users[chat_id] = {"can_answer": False, "stop_event": asyncio.Event()}

            if task["type"] == "open":
                self.bot.send_message(chat_id, task["text"], parse_mode="Markdown")
                await self.send_timer(chat_id, task["prep_time"], "Preparation time")
                self.bot.send_message(chat_id, "🎤 You can talk now. I'm waiting for a voice message!")
                self.active_users[chat_id]["can_answer"] = True
                await self.send_timer(chat_id, task["response_time"], "Response time", self.active_users[chat_id]["stop_event"])
                self.active_users[chat_id]["can_answer"] = False

            elif task["type"] == "reading":
                self.bot.send_message(chat_id, task["text"], parse_mode="Markdown")
                await self.send_timer(chat_id, task["reading_time"], "Time to read")
                self.bot.send_message(chat_id, task["follow_up"], parse_mode="Markdown")
                await self.send_timer(chat_id, task["prep_time"], "Preparation time")
                self.bot.send_message(chat_id, "🎤 You can talk now. I'm waiting for a voice message!")
                self.active_users[chat_id]["can_answer"] = True
                await self.send_timer(chat_id, task["response_time"], "Response time", self.active_users[chat_id]["stop_event"])
                self.active_users[chat_id]["can_answer"] = False

            elif task["type"] == "listening":
                self.bot.send_message(chat_id, task["intro_text"], parse_mode="Markdown")
                
                with open(task["audio_path"], 'rb') as audio:
                    audio_msg = self.bot.send_audio(chat_id, audio)
                
                await self.send_timer(chat_id, task["audio_duration"], "Time to listen")
                
                try:
                    self.bot.delete_message(chat_id, audio_msg.message_id)
                except:
                    pass
                
                self.bot.send_message(chat_id, task["follow_up"], parse_mode="Markdown")
                await self.send_timer(chat_id, task["prep_time"], "Preparation time")
                self.bot.send_message(chat_id, "🎤 You can talk now. I'm waiting for a voice message!")
                self.active_users[chat_id]["can_answer"] = True
                await self.send_timer(chat_id, task["response_time"], "Response time", self.active_users[chat_id]["stop_event"])
                self.active_users[chat_id]["can_answer"] = False

        self.bot.send_message(chat_id, "✅ Speaking Section Complete.")
        self.active_users.pop(chat_id, None)

        if chat_id in self.user_tests:
            del self.user_tests[chat_id]


    def handle_voice(self, message):
        chat_id = message.chat.id
        user_state = self.active_users.get(chat_id)

        if not user_state:
            self.bot.send_message(chat_id, "The Speaking task is currently not being performed.")
            return

        if not user_state["can_answer"]:
            self.bot.send_message(chat_id, "⛔️  You can't send a voice message now. Voice message is not accepted.")
            return

        user_state["stop_event"].set()
        user_state["can_answer"] = False

        self.bot.send_message(chat_id, "🎧 Your voice message has been received. Thanks!")