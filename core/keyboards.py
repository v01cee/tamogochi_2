from aiogram.types import KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


class KeyboardOperations:
    """Класс для работы с клавиатурами aiogram"""

    async def create_keyboard(
            self,
            buttons: list | dict | None = None,
            interval: int = 1,
            count: int = 0,
            is_builder: bool = None
    ):
        keyboard = InlineKeyboardBuilder()

        match buttons:
            case list():
                keyboard = await self.__reply_keyboard(buttons=buttons, interval=interval, count=count)

            case dict():
                keyboard = await self.__inline_keyboard(buttons=buttons, interval=interval, count=count)

        return keyboard.as_markup() if not is_builder else keyboard

    @staticmethod
    async def __inline_keyboard(buttons: dict, interval: int, count: int):
        buttons_list = list()
        interval_count = 0

        keyboard = InlineKeyboardBuilder()
        button = InlineKeyboardButton

        for text, callback_data in buttons.items():
            if callback_data[0] == "url":
                buttons_list.append(button(text=text, url=callback_data[1]))
            else:
                buttons_list.append(button(text=text, callback_data=callback_data))

            if len(buttons_list) == interval:
                keyboard.row(*buttons_list)
                buttons_list.clear()
                interval_count += 1
                if interval_count == count:
                    interval = 1

        return keyboard

    @staticmethod
    async def __reply_keyboard(buttons: list, interval: int, count: int):
        buttons_list = list()
        interval_count = 0

        keyboard = ReplyKeyboardBuilder()
        button = KeyboardButton

        for text in buttons:
            buttons_list.append(button(text=text))

            if len(buttons_list) == interval:
                keyboard.row(*buttons_list)
                buttons_list.clear()
                interval_count += 1
                if interval_count == count:
                    interval = 1

        return keyboard


