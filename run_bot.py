#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для запуска Telegram бота.
Альтернативный способ запуска бота (можно использовать вместо bot.py).
"""

import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем и запускаем main функцию из bot.py
from bot import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())


