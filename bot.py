from dotenv import load_dotenv
from openai import OpenAI
from os import getenv
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import Message
from typing import Final, TypeAlias


Username: TypeAlias = str
UserContextMessage: TypeAlias = str


class UserContext:
    """Хранит контексты пользователей для корректных ответов нейросети."""

    storage: dict[Username, list[str]] = {}

    def _create_context(self, username: str) -> None:
        """
        Создает контекст для пользователя.
        :param username: 'Ник' пользователя.
        """
        self.storage[username] = []

    def _get_context(self, username: str) -> UserContextMessage:
        """Возвращает контекст пользователя."""
        LAST_MESSAGES_TO_RETURN: Final[int] = -3
        return " ".join(self.storage[username][LAST_MESSAGES_TO_RETURN:])
        

    def _add_context(self, username: str, message: Message) -> None:
        """
        Добавляет сообщение в контекст пользователя.
        :param username: 'Ник' пользователя.
        :param message: Сообщение пользователя.
        """
        self.storage[username].append(message.text)
    
    def _del_context(self, username: str) -> None:
        """
        Удаляет сообщение из контекста пользователя.
        :param username: 'Ник' пользователя.
        :param message: Сообщение пользователя.
        """
        self.storage[username].clear()


# Инициализация API-ключей и бота
load_dotenv('venv.env')

OPENAI_API_KEY: Final[str] = getenv('OPENAI_API_KEY')
TELEGRAM_BOT_TOKEN: Final[str] = getenv('TELEGRAM_API_TOKEN')
client = OpenAI(api_key=OPENAI_API_KEY)

ERROR_RESPONSE = "На стороне сервиса произошла ошибка. Воспользуйтесь сервисом позже."

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_context = UserContext()


def get_gpt_response(user_message: str, system_prompt: str) -> str:
    """
    Отправляет запрос к GPT и обрабатывает ответ.
    :param user_message: Текст сообщения пользователя.
    :param system_prompt: Контекст, необходимый для обработки запроса.
    """
    try:
        response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500, 
                temperature=0.7, 
                frequency_penalty=0.0,
                presence_penalty=0.0)

        text = response.choices[0].message.content
        return text.strip()
    except Exception as e:
        print(f"Ошибка GPT: {e}")
        return ERROR_RESPONSE


@bot.message_handler(commands=['start'])
def send_welcome(message: Message) -> None:
    """
    Приветствует пользователя в начале диалога (=при вводе /start).
    :param message: Сообщение пользователя.
    """
    bot.reply_to(message, "Привет! Я бот, использующий GPT для упрощения "
                          "текстов законов. Напишите мне текст, и я перепишу его.")


@bot.message_handler(func=lambda message: True)
def handle_text(message: Message) -> None:
    """
    Обрабатывает текст пользователя (в контексте задачи сокращения текста закона).
    :param message: Сообщение пользователя.
    """
    user_message = message.text
    username = message.from_user.username
    chat_id = message.chat.id

    if username not in user_context.storage:
        user_context._create_context(username)

    user_context._add_context(username, message)
    context = user_context._get_context(username)

    if user_message == "Очистить контекст":
        user_context._del_context(username)
        bot.reply_to(message, "Контекст сброшен.")

    else:
        if user_message == 'Объяснить термины':
            system_prompt = (
                'Добавь список сложных терминов из твоего предыдущего'
                ' ответа с их краткими определениями. Например: '
                '<i>Термин:</i> Конституция — основной закон государства.'
            )
        else:
            system_prompt = (
                "Ты - эксперт, который помогает переписывать тексты законов, делая их простыми, ясными и доступными для широкой "
                "аудитории, не обладающей юридическими знаниями. Сохраняй ключевые аспекты и суть закона, избегая сложных "
                "формулировок и юридического жаргона. Включай пояснения сложных моментов и примеры (в формате: <i>Пример:</i>). "
                "Также форматируй текст в формате: <b>Заголовок</b> "
                "Это пример текста, в котором <b>жирный текст</b>, <i>курсивный текст</i>, <s>зачёркнутый текст</s>, "
                "<u>подчёркнутый текст</u> и <code>код</code> вместо ``` и ** оформлены в соответствии с указанным форматом."
            )
        
        bot.reply_to(message, "Подождите...")
        response = get_gpt_response(context, system_prompt)

        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        if response != ERROR_RESPONSE: 
            markup.add(KeyboardButton("Очистить контекст"))
            markup.add(KeyboardButton("Объяснить термины"))

        bot.send_message(chat_id, response, parse_mode='HTML', reply_markup=markup)


def main() -> None:
    """Daemon-функция, запускающая функционал бота."""
    print("Бот запущен...")
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
