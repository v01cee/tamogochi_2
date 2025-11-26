from __future__ import annotations

import io
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def generate_radar_chart(
    labels: Sequence[str],
    values: Sequence[float | int],
    *,
    title: str | None = None,
) -> bytes:
    """
    Построение и возврат радарной диаграммы в виде байтов PNG.

    Args:
        labels: Подписи осей (в порядке обхода по часовой стрелке).
        values: Значения, соответствующие подписям.
        title: Заголовок диаграммы (опционально).

    Returns:
        Бинарное содержимое изображения в формате PNG.
    """
    if len(labels) != len(values):
        raise ValueError("Количество подписей и значений должно совпадать.")

    if not labels:
        raise ValueError("Для построения диаграммы требуется минимум одна точка.")

    numeric_values = np.array([float(value) for value in values])
    num_vars = len(labels)

    # Углы для каждой оси
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    # Замыкаем многоугольник
    plot_values = numeric_values.tolist()
    plot_values += plot_values[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_alpha(0.0)

    # Настройка сетки
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    # Устанавливаем метки
    ax.set_xticklabels(labels, fontsize=10)
    # Увеличиваем отступ меток от центра после их создания
    for label in ax.get_xticklabels():
        label.set_horizontalalignment('center')
    ax.tick_params(axis='x', pad=20)  # Устанавливаем отступ через tick_params
    ax.set_rlabel_position(180 / num_vars)
    ax.set_yticks(range(1, 11))
    ax.set_yticklabels([])
    ax.set_ylim(0, 10)
    ax.tick_params(axis="y", labelsize=0)
    ax.grid(color="#cccccc", linestyle="solid", linewidth=0.8)

    # Построение многоугольника
    ax.plot(angles, plot_values, color="#f47c57", linewidth=2)
    ax.fill(angles, plot_values, color="#f7b267", alpha=0.35)

    # Подписи значений на соответствующих осях
    # Увеличиваем отступ от значения, чтобы числа не накладывались на метки
    for angle, value in zip(angles[:-1], plot_values[:-1]):
        # Вычисляем позицию для числа так, чтобы оно было между меткой и значением
        text_radius = max(value + 0.6, 1.5)  # Минимальный отступ от центра
        ax.text(
            angle,
            text_radius,
            f"{value:.0f}",
            color="#444444",
            fontsize=10,
            fontweight="bold",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor="none"),
        )

    if title:
        ax.set_title(title, pad=30, fontsize=14, fontweight="semibold")

    buffer = io.BytesIO()
    plt.tight_layout(pad=2.0)
    plt.savefig(buffer, format="png", transparent=True, dpi=150, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer.read()



