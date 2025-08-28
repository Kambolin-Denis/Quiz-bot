import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import F
from data import quiz_data
from DB import (
    get_quiz_index, update_quiz_index, create_table, 
    save_user_answer, get_user_answers, clear_user_answers,
    save_quiz_result, get_user_stats, get_leaderboard
)
from questions import get_question

logging.basicConfig(level=logging.INFO)
API_TOKEN = '8435487987:AAGCqaQHa5aw5ly__iLqFgYBLlS9usis2FI'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
DB_NAME = 'quiz_bot.db'

async def show_final_results(message: types.Message, user_id: int, username: str):
    """Показывает финальные результаты с детализацией всех ответов"""
    user_answers = await get_user_answers(user_id)
    score = sum(1 for answer in user_answers if answer['is_correct'])
    
    # Сохраняем результат квиза
    await save_quiz_result(user_id, username, score, len(quiz_data))
    
    result_text = f"🎉 Квиз завершен!\nВаш результат: {score}/{len(quiz_data)}\n\n"
    result_text += "📊 Детализация ответов:\n\n"
    
    for i, answer in enumerate(user_answers):
        question_data = quiz_data[answer['question_index']]
        user_answer_text = question_data['options'][answer['user_answer']]
        correct_answer_text = question_data['options'][question_data['correct_option']]
        
        result_text += f"{i+1}. {question_data['question']}\n"
        result_text += f"   Ваш ответ: {user_answer_text} {'✅' if answer['is_correct'] else '❌'}\n"
        if not answer['is_correct']:
            result_text += f"   Правильный ответ: {correct_answer_text}\n"
        result_text += "\n"
    
    result_text += f"🏆 Итоговый счет: {score}/{len(quiz_data)}\n\n"
    
    stats = await get_user_stats(user_id)
    result_text += f"📈 Ваша статистика:\n"
    result_text += f"• Последний результат: {stats['last_score']}/{stats['last_total']}\n"
    result_text += f"• Лучший результат: {stats['best_score']}/{stats['best_total']}\n"
    result_text += f"• Всего пройдено квизов: {stats['total_quizzes']}"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🏆 Таблица лидеров", callback_data="show_leaderboard")
    builder.button(text="🔄 Пройти еще раз", callback_data="restart_quiz")
    
    await message.answer(result_text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    user_id = callback.from_user.id
    current_question_index = await get_quiz_index(user_id)
    question_data = quiz_data[current_question_index]
    
    # Получаем выбранный вариант ответа
    selected_option = int(callback.data.split("_")[1])
    user_answer_text = question_data['options'][selected_option]
    
    # Проверяем правильность ответа
    is_correct = selected_option == question_data['correct_option']
    
 
    await save_user_answer(
        user_id,
        current_question_index,
        selected_option,
        is_correct
    )
    
    if is_correct:
        await callback.message.answer("✅ Верно!")
    else:
        correct_answer_text = question_data['options'][question_data['correct_option']]
        await callback.message.answer(f"❌ Неправильно. Правильный ответ: {correct_answer_text}")
    
    current_question_index += 1
    await update_quiz_index(user_id, current_question_index)

    if current_question_index < len(quiz_data):
        await get_question(callback.message, user_id)
    else:
        username = callback.from_user.username or callback.from_user.first_name
        await show_final_results(callback.message, user_id, username)
    
    await callback.answer()

@dp.callback_query(F.data == "show_leaderboard")
async def show_leaderboard_handler(callback: types.CallbackQuery):
    leaderboard = await get_leaderboard()
    
    if not leaderboard:
        await callback.message.answer("📊 Таблица лидеров пуста. Будьте первым!")
        return
    
    leaderboard_text = "🏆 Топ-10 игроков:\n\n"
    
    for i, player in enumerate(leaderboard[:10], 1):
        username = player['username'] or f"Игрок {player['user_id']}"
        leaderboard_text += f"{i}. {username} - {player['best_score']}/{player['best_total']} "
        leaderboard_text += f"(последний: {player['last_score']}/{player['last_total']})\n"
    
    await callback.message.answer(leaderboard_text)
    await callback.answer()

@dp.callback_query(F.data == "restart_quiz")
async def restart_quiz_handler(callback: types.CallbackQuery):
    await new_quiz(callback.message)
    await callback.answer()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    builder.add(types.KeyboardButton(text="📊 Моя статистика"))
    builder.add(types.KeyboardButton(text="🏆 Таблица лидеров"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text == "📊 Моя статистика")
@dp.message(Command("stat"))
async def show_my_stats(message: types.Message):
    stats = await get_user_stats(message.from_user.id)
    
    if stats['total_quizzes'] == 0:
        await message.answer("Вы еще не проходили квизы. Начните игру!")
        return
    
    stats_text = "📈 Ваша статистика:\n\n"
    stats_text += f"• Последний результат: {stats['last_score']}/{stats['last_total']}\n"
    stats_text += f"• Лучший результат: {stats['best_score']}/{stats['best_total']}\n"
    stats_text += f"• Всего пройдено квизов: {stats['total_quizzes']}\n"
    stats_text += f"• Процент правильных ответов: {stats['accuracy']:.1f}%"
    
    await message.answer(stats_text)

@dp.message(F.text == "🏆 Таблица лидеров")
@dp.message(Command("leaderboard"))
async def show_leaderboard_message(message: types.Message):
    leaderboard = await get_leaderboard()
    
    if not leaderboard:
        await message.answer("📊 Таблица лидеров пуста. Будьте первым!")
        return
    
    leaderboard_text = "🏆 Топ-10 игроков:\n\n"
    
    for i, player in enumerate(leaderboard[:10], 1):
        username = player['username'] or f"Игрок {player['user_id']}"
        leaderboard_text += f"{i}. {username} - {player['best_score']}/{player['best_total']} "
        leaderboard_text += f"(последний: {player['last_score']}/{player['last_total']})\n"
    
    await message.answer(leaderboard_text)

async def new_quiz(message):
    user_id = message.from_user.id
    current_question_index = 0
    await clear_user_answers(user_id)
    await update_quiz_index(user_id, current_question_index)
    await get_question(message, user_id)

# Хэндлер на команду /quiz
@dp.message(F.text=="Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await message.answer("Давайте начнем квиз!")
    await new_quiz(message)

# Запуск процесса поллинга новых апдейтов
async def main():
    # Запускаем создание таблицы базы данных
    await create_table()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())