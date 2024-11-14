import telebot
from PIL import Image, ImageOps
import io
from telebot import types
from TOKENBOT import TOKEN

bot = telebot.TeleBot(TOKEN)

user_states = {}

ASCII_CHARS = '@%#*+=-:. '


def resize_image(image, new_width=100):
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))


def grayify(image):
    return image.convert("L")


def image_to_ascii(image_stream, new_width=40):
    image = Image.open(image_stream).convert('L')

    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(
        aspect_ratio * new_width * 0.55)
    img_resized = image.resize((new_width, new_height))

    img_str = pixels_to_ascii(img_resized)
    img_width = img_resized.width

    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)

    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"

    return ascii_art


def pixels_to_ascii(image):
    pixels = image.getdata()
    characters = ""
    for pixel in pixels:
        characters += ASCII_CHARS[pixel * len(ASCII_CHARS) // 256]
    return characters


def pixelate_image(image, pixel_size):
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image


def invert_colors(image):
    return ImageOps.invert(image)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Send me an image, and I'll provide options for you!")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_states[message.chat.id] = {'level': 0}
    # user_states[message.chat.id]['photo'] = message.photo[-1].file_id
    bot.reply_to(message, "I got your photo! Please choose what you'd like to do with it.",
                 reply_markup=get_options_keyboard(message))
    user_states[message.chat.id]['photo'] = message.photo[-1].file_id
    # user_states[message.chat.id]['message_id'] = message.message_id


def get_options_keyboard(message):
    print(user_states.get(message.chat.id))
    if user_states.get(message.chat.id) and user_states[message.chat.id]['level'] == 0:
        keyboard = types.InlineKeyboardMarkup()
        pixelate_btn = types.InlineKeyboardButton("Pixelate", callback_data="pixelate")
        ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii_art")
        keyboard.add(pixelate_btn, ascii_btn)
        user_states[message.chat.id]['message_id'] = message.message_id
        return keyboard
    elif user_states.get(message.chat.id) and user_states[message.chat.id]['level'] == 1:
        keyboard = types.InlineKeyboardMarkup()
        pixelate_btn = types.InlineKeyboardButton("Pixelate img", callback_data="pixelate_img")
        ascii_btn = types.InlineKeyboardButton("Invert color", callback_data="invert")
        keyboard.add(pixelate_btn, ascii_btn)
        user_states[message.chat.id]['message_id'] = message.message_id
        return keyboard
    elif user_states.get(message.chat.id) and user_states[message.chat.id]['level'] == 2:
        keyboard = types.InlineKeyboardMarkup()
        pixelate_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
        ascii_btn = types.InlineKeyboardButton("ASCII Personal Art", callback_data="ascii_personal")
        keyboard.add(pixelate_btn, ascii_btn)
        user_states[message.chat.id]['message_id'] = message.message_id
        return keyboard


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id

    if call.data == "pixelate":
        user_states[chat_id]['level'] = 1
        bot.reply_to(call.message, f"Выберите действие... {call.message.message_id}",
                     reply_markup=get_options_keyboard(call.message))
        bot.delete_message(chat_id, user_states[chat_id]['message_id'])
    elif call.data == "pixelate_img":
        user_states[chat_id]['level'] = 3
        bot.answer_callback_query(call.id, f"Pixelating your image... {call.message.message_id}")
        pixelate_and_send(call.message)
    elif call.data == "invert":
        user_states[chat_id]['level'] = 4
        bot.reply_to(call.message, f"Inverting your image... {call.message.message_id}")
        pixelate_and_send(call.message)
    elif call.data == "ascii_art":
        user_states[chat_id]['level'] = 2
        bot.send_message(call.message.chat.id,
                         f"Выберите способ преобразования картинки в ASCII...{call.message.message_id}",
                         reply_markup=get_options_keyboard(call.message))
        bot.delete_message(chat_id, user_states[chat_id]['message_id'])
    elif call.data == "ascii":
        user_states[chat_id]['level'] = 5
        bot.answer_callback_query(call.id, "Converting your image to ASCII art...")
        ascii_and_send(call.message)
    elif call.data == "ascii_personal":
        user_states[chat_id]['level'] = 6
        bot.reply_to(call.message, "Enter char for converting your image to ASCII art...")
        # bot.delete_message(chat_id, user_states[chat_id]['message_id'])


def pixelate_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    if user_states.get(message.chat.id) and user_states[message.chat.id]['level'] == 3:
        pixelated = pixelate_image(image, 20)
    elif user_states.get(message.chat.id) and user_states[message.chat.id]['level'] == 4:
        pixelated = invert_colors(image)
    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)
    user_states[message.chat.id]['level'] = 0
    bot.send_message(message.chat.id,
                     f"Выберите действие, которое хотите сделать с изображением. {message.message_id}",
                     reply_markup=get_options_keyboard(message))
    bot.delete_message(message.chat.id, user_states[message.chat.id]['message_id'])


def ascii_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)

    ascii_art = image_to_ascii(image_stream)
    bot.send_message(message.chat.id, f"```\n{ascii_art}\n```", parse_mode="MarkdownV2")
    user_states[message.chat.id]['level'] = 0
    bot.send_message(message.chat.id, "Please choose what you'd like to do with it.",
                     reply_markup=get_options_keyboard(message))
    bot.delete_message(message.chat.id, user_states[message.chat.id]['message_id'])
    # user_states[message.chat.id]['message_id'] = message.message_id


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if user_states.get(message.chat.id) and user_states[message.chat.id]['level'] == 6:
        bot.delete_message(message.chat.id, user_states[message.chat.id]['message_id'] + 1)
        global ASCII_CHARS
        ASCII_CHARS = message.text
        ascii_and_send(message)


bot.polling(none_stop=True)
