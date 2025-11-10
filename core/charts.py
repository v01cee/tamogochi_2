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

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_alpha(0.0)

    # Настройка сетки
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)
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
    for angle, value in zip(angles[:-1], plot_values[:-1]):
        ax.text(
            angle,
            value + 0.4,
            f"{value:.0f}",
            color="#444444",
            fontsize=11,
            fontweight="bold",
            ha="center",
            va="center",
        )

    if title:
        ax.set_title(title, pad=20, fontsize=14, fontweight="semibold")

    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="png", transparent=True)
    plt.close(fig)
    buffer.seek(0)
    return buffer.read()



