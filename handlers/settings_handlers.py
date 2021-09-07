from contextlib import suppress

from aiogram.types import CallbackQuery
from aiogram.utils.exceptions import (MessageCantBeDeleted,
                                      MessageNotModified,
                                      MessageToDeleteNotFound)

from bot import dp
from config import Config
from db_models.users import User
from services.keyboards import (menu_keyboard,
                                settings_keyboard)
from services.states import States


async def action_settings(callback_query: CallbackQuery, **kwargs):
    user_id = callback_query.from_user.id
    await dp.current_state(user=user_id).set_state(States.THROTTLER)
    user = await User.update_user(user_id=user_id, **kwargs)
    await callback_query.answer()
    await dp.current_state(user=user_id).set_state(States.GRANTED)
    with suppress(MessageNotModified):
        await callback_query.message.edit_reply_markup(reply_markup=settings_keyboard(user=user))


@dp.callback_query_handler(text=['ru', 'en'], state='granted')
async def language_settings(callback_query: CallbackQuery):
    await dp.current_state(user=callback_query.from_user.id).set_state(States.THROTTLER)
    new_language = callback_query.data
    user_id = callback_query.from_user.id
    await dp.current_state(user=user_id).set_state(States.THROTTLER)
    user = await User.update_user(user_id=user_id, language=new_language)
    text = Config.local.help_text.get(new_language)
    with suppress(MessageToDeleteNotFound, MessageCantBeDeleted):
        await callback_query.message.delete()
    await dp.current_state(user=user.id).set_state(States.GRANTED)
    await callback_query.message.answer(Config.local.changed_language.get(new_language),
                                        reply_markup=menu_keyboard(user.language))
    await callback_query.message.answer(text, reply_markup=settings_keyboard(user=user))


@dp.callback_query_handler(text=['yes_avatar', 'no_avatar'], state='granted')
async def avatar_settings(callback_query: CallbackQuery):
    show_avatar = callback_query.data == 'yes_avatar'
    await action_settings(callback_query=callback_query, show_avatar=show_avatar)


@dp.callback_query_handler(text=['yes_telegram', 'no_telegram'], state='granted')
async def telegram_settings(callback_query: CallbackQuery):
    show_me = callback_query.data == 'yes_telegram'
    await action_settings(callback_query=callback_query, show_me=show_me)


@dp.callback_query_handler(text=['yes_campus', 'no_campus'], state='granted')
async def campus_settings(callback_query: CallbackQuery):
    use_default_campus = callback_query.data == 'yes_campus'
    await action_settings(callback_query=callback_query, use_default_campus=use_default_campus)
