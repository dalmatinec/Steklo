# start.py

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from datetime import datetime, timedelta
import json
import os
import time

from database import add_user, get_user_link, save_user_link, delete_user_link
from keyboards import main_menu, cancel_inline
from utils import get_link, get_chat_id, get_link_name, get_message

router = Router()


def load_welcome_text():
    """Загружает приветственный текст из text.json"""
    try:
        with open("text.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("welcome", "")
    except Exception:
        return "Добро пожаловать!"


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    # Игнорируем команду в группах
    if message.chat.type in ["group", "supergroup"]:
        return

    user = message.from_user

    # Регистрация пользователя
    add_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    # Загружаем текст приветствия и подставляем имя/юзернейм
    display_name = f"@{user.username}" if user.username else user.first_name
    welcome_text = load_welcome_text().format(
        first_name=user.first_name,
        username=display_name
    )

    # Отправляем фото с подписью
    if os.path.exists("start.jpg"):
        photo = FSInputFile("start.jpg")
        await message.answer_photo(
            photo=photo,
            caption=welcome_text,
            reply_markup=main_menu()
        )
    else:
        await message.answer(
            welcome_text,
            reply_markup=main_menu()
        )


@router.callback_query(F.data.startswith("link_"))
async def callback_link(callback: types.CallbackQuery):
    """Обработчик кнопок со ссылками"""
    # НЕ вызываем await callback.answer() в начале!

    # Игнорируем нажатия в группах
    if callback.message.chat.type in ["group", "supergroup"]:
        await callback.answer(get_message("group_only_private", "❌ Используйте бота в личных сообщениях"), show_alert=True)
        return

    link_key = callback.data.replace("link_", "")
    link_name = get_link_name(link_key)

    # Для чата, новостей, резерва — генерируем ссылку-ЗАЯВКУ на вступление
    if link_key in ["chat", "news", "reserve"]:
        chat_id = get_chat_id(link_key)
        if not chat_id:
            await callback.answer(get_message("link_not_configured", "❌ Ссылка не настроена"), show_alert=True)
            return

        user_id = callback.from_user.id

        # Проверяем наличие активной ссылки в БД для этого типа
        created_at = get_user_link(user_id, link_key)
        if created_at:
            elapsed = time.time() - created_at
            if elapsed < 1800:  # 30 минут
                remaining = int(1800 - elapsed)
                minutes = remaining // 60
                seconds = remaining % 60
                await callback.answer(
                    get_message("join_wait", "⏳ Новая ссылка будет доступна через {minutes} мин {seconds} сек").format(
                        minutes=minutes, seconds=seconds
                    ),
                    show_alert=True
                )
                return
            else:
                # Время истекло, удаляем старую запись
                delete_user_link(user_id, link_key)

        try:
            expire_date = datetime.now() + timedelta(minutes=30)
            # creates_join_request=True -> ссылка создаёт ЗАЯВКУ на вступление,
            # а не мгновенный вход. Заявка автоматически одобряется хендлером
            # chat_join_request ниже. member_limit с creates_join_request
            # использовать нельзя — единственность обеспечивается тем,
            # что ссылка выдаётся только этому пользователю и одноразова по смыслу.
            link = await callback.bot.create_chat_invite_link(
                chat_id=chat_id,
                creates_join_request=True,
                expire_date=expire_date,
                name=f"req-{user_id}-{int(time.time())}"
            )

            save_user_link(user_id, link_key, int(time.time()))

            # Кнопка с ссылкой (зелёная, т.к. это положительное/подтверждающее действие)
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(
                    text=get_message("join_button", "🎟️ Вступить"),
                    url=link.invite_link,
                    style="success"
                )]
            ])

            await callback.bot.send_message(
                chat_id=callback.from_user.id,
                text=get_message("join_ready"),
                reply_markup=keyboard
            )

            await callback.answer()  # закрываем callback после успеха

        except Exception as e:
            await callback.answer(get_message("join_error", "❌ Ошибка при генерации ссылки: {error}").format(error=e), show_alert=True)

    # Для бота/website/CEO/оператора кнопки уже открывают ссылку напрямую (url=)
    # Сюда попадаем только если конкретная ссылка ещё не настроена в link.json
    else:
        url = get_link(link_key)
        if url:
            # Ссылка появилась — просто подсказываем нажать кнопку заново
            await callback.answer()
        else:
            await callback.answer(get_message("link_not_configured", "❌ Ссылка не настроена"), show_alert=True)


@router.chat_join_request()
async def auto_approve_join_request(update: types.ChatJoinRequest):
    """Автоматически одобряет заявки на вступление, созданные через бота"""
    try:
        await update.bot.approve_chat_join_request(
            chat_id=update.chat.id,
            user_id=update.from_user.id
        )
    except Exception:
        pass


@router.callback_query(F.data == "support")
async def callback_support(callback: types.CallbackQuery):
    """Обработчик кнопки 'Связаться с оператором'"""
    await callback.answer()

    # Игнорируем нажатия в группах
    if callback.message.chat.type in ["group", "supergroup"]:
        await callback.answer(get_message("group_only_private", "❌ Используйте бота в личных сообщениях"), show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(
        get_message("support_prompt"),
        reply_markup=cancel_inline()
    )


@router.callback_query(F.data == "cancel_support")
async def callback_cancel(callback: types.CallbackQuery):
    """Отмена обращения"""
    await callback.answer()

    # Игнорируем нажатия в группах
    if callback.message.chat.type in ["group", "supergroup"]:
        await callback.answer(get_message("group_only_private", "❌ Используйте бота в личных сообщениях"), show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(
        get_message("support_cancelled", "❌ Обращение отменено")
    )
