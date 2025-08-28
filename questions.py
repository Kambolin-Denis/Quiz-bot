from aiogram.utils.keyboard import InlineKeyboardBuilder
from data import quiz_data
from DB import get_quiz_index

async def get_question(message, user_id):
    # Получение текущего вопроса из базы данных
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, correct_index)
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)

def generate_options_keyboard(options, correct_option):
    builder = InlineKeyboardBuilder()
    
    for option_index, option_text in enumerate(options):
        # Используем формат answer_{option_index} вместо right_answer/wrong_answer
        builder.button(text=option_text, callback_data=f"answer_{option_index}")
    
    builder.adjust(1)
    return builder.as_markup()