import os
import sys

# ��������� ���� � ����� ������� ��� ������� ������� ����
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ����������� �������� ������������ ������� (����������� ����������� ����� ����������)
from .admin_sections import telegram_user_admin  # noqa: F401
from .admin_sections import quiz_and_course_admin  # noqa: F401
from .admin_sections import touch_content_admin  # noqa: F401
