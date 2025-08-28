import aiosqlite
from datetime import datetime

DB_NAME = 'quiz_bot.db'

async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица для состояния викторины
        await db.execute('''
            CREATE TABLE IF NOT EXISTS quiz_state (
                user_id INTEGER PRIMARY KEY,
                question_index INTEGER
            )
        ''')
        # Таблица для ответов пользователя
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_index INTEGER,
                user_answer INTEGER,
                is_correct BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Таблица для результатов квизов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                score INTEGER,
                total_questions INTEGER,
                accuracy REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

async def get_quiz_index(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id,)) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0

async def update_quiz_index(user_id, index):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
        await db.commit()

async def save_user_answer(user_id: int, question_index: int, user_answer: int, is_correct: bool):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT INTO user_answers (user_id, question_index, user_answer, is_correct) VALUES (?, ?, ?, ?)',
            (user_id, question_index, user_answer, is_correct)
        )
        await db.commit()

async def get_user_answers(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'SELECT question_index, user_answer, is_correct FROM user_answers WHERE user_id = ? ORDER BY question_index',
            (user_id,)
        )
        answers = await cursor.fetchall()
        return [{'question_index': row[0], 'user_answer': row[1], 'is_correct': bool(row[2])} for row in answers]

async def clear_user_answers(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM user_answers WHERE user_id = ?', (user_id,))
        await db.commit()

async def save_quiz_result(user_id: int, username: str, score: int, total_questions: int):
    accuracy = (score / total_questions) * 100 if total_questions > 0 else 0
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT INTO quiz_results (user_id, username, score, total_questions, accuracy) VALUES (?, ?, ?, ?, ?)',
            (user_id, username, score, total_questions, accuracy)
        )
        await db.commit()

async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        # Последний результат
        cursor = await db.execute(
            '''SELECT score, total_questions FROM quiz_results 
               WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1''',
            (user_id,)
        )
        last_result = await cursor.fetchone()
        
        # Лучший результат
        cursor = await db.execute(
            '''SELECT MAX(score), total_questions FROM quiz_results 
               WHERE user_id = ? GROUP BY total_questions ORDER BY score DESC LIMIT 1''',
            (user_id,)
        )
        best_result = await cursor.fetchone()
        
        # Общее количество квизов
        cursor = await db.execute(
            'SELECT COUNT(*) FROM quiz_results WHERE user_id = ?',
            (user_id,)
        )
        total_quizzes = await cursor.fetchone()
        
        # Средняя точность
        cursor = await db.execute(
            'SELECT AVG(accuracy) FROM quiz_results WHERE user_id = ?',
            (user_id,)
        )
        avg_accuracy = await cursor.fetchone()
        
        return {
            'last_score': last_result[0] if last_result else 0,
            'last_total': last_result[1] if last_result else 0,
            'best_score': best_result[0] if best_result else 0,
            'best_total': best_result[1] if best_result else 0,
            'total_quizzes': total_quizzes[0] if total_quizzes else 0,
            'accuracy': avg_accuracy[0] if avg_accuracy and avg_accuracy[0] is not None else 0
        }

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
    
        cursor = await db.execute('''
            SELECT user_id, username, MAX(score) as best_score, total_questions as best_total,
                   (SELECT score FROM quiz_results r2 
                    WHERE r2.user_id = r1.user_id 
                    ORDER BY timestamp DESC LIMIT 1) as last_score,
                   (SELECT total_questions FROM quiz_results r2 
                    WHERE r2.user_id = r1.user_id 
                    ORDER BY timestamp DESC LIMIT 1) as last_total
            FROM quiz_results r1
            GROUP BY user_id
            ORDER BY best_score DESC, accuracy DESC
        ''')
        results = await cursor.fetchall()
        
        return [{
            'user_id': row[0],
            'username': row[1],
            'best_score': row[2],
            'best_total': row[3],
            'last_score': row[4],
            'last_total': row[5]
        } for row in results]