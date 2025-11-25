"""Единая страница статистики всех касаний."""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Avg
from datetime import date, timedelta

from ..models import (
    TouchAnswer,
    EveningReflection,
    EveningRating,
    SaturdayReflection,
    UnifiedStatistics,
)


@admin.register(UnifiedStatistics)
class UnifiedStatisticsAdmin(admin.ModelAdmin):
    """Единая страница статистики всех касаний."""
    
    def has_module_permission(self, request):
        """Показывать в меню админки."""
        return True
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_urls(self):
        urls = super().get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        custom_urls = [
            path('', self.admin_site.admin_view(self.statistics_view), name='%s_%s_changelist' % info),
        ]
        return custom_urls
    
    def statistics_view(self, request):
        """Единая страница статистики всех касаний."""
        # Статистика по ответам на касания (утро/день/вечер)
        touch_answers_stats = TouchAnswer.objects.filter(is_active=True).values(
            'touch_content__touch_type'
        ).annotate(
            count=Count('id')
        ).order_by('touch_content__touch_type')
        
        touch_answers_by_type = {
            'morning': 0,
            'day': 0,
            'evening': 0,
        }
        for stat in touch_answers_stats:
            touch_type = stat['touch_content__touch_type']
            if touch_type in touch_answers_by_type:
                touch_answers_by_type[touch_type] = stat['count']
        
        total_touch_answers = sum(touch_answers_by_type.values())
        
        # Статистика по вечерним рефлексиям
        evening_reflections_count = EveningReflection.objects.filter(is_active=True).count()
        
        # Статистика по вечерним оценкам
        evening_ratings_count = EveningRating.objects.filter(is_active=True).count()
        if evening_ratings_count > 0:
            avg_stats = EveningRating.objects.filter(is_active=True).aggregate(
                avg_energy=Avg('rating_energy'),
                avg_happiness=Avg('rating_happiness'),
                avg_progress=Avg('rating_progress')
            )
            avg_energy = round(avg_stats['avg_energy'] or 0, 1)
            avg_happiness = round(avg_stats['avg_happiness'] or 0, 1)
            avg_progress = round(avg_stats['avg_progress'] or 0, 1)
        else:
            avg_energy = avg_happiness = avg_progress = 0
        
        # Статистика по стратсубботам
        saturday_reflections_count = SaturdayReflection.objects.filter(is_active=True).count()
        
        # Статистика за последние 7 дней
        week_ago = date.today() - timedelta(days=7)
        touch_answers_week_morning = TouchAnswer.objects.filter(
            is_active=True,
            touch_date__gte=week_ago,
            touch_content__touch_type='morning'
        ).count()
        touch_answers_week_day = TouchAnswer.objects.filter(
            is_active=True,
            touch_date__gte=week_ago,
            touch_content__touch_type='day'
        ).count()
        touch_answers_week_evening = TouchAnswer.objects.filter(
            is_active=True,
            touch_date__gte=week_ago,
            touch_content__touch_type='evening'
        ).count()
        touch_answers_week_total = TouchAnswer.objects.filter(
            is_active=True,
            touch_date__gte=week_ago
        ).count()
        evening_reflections_week = EveningReflection.objects.filter(
            is_active=True,
            reflection_date__gte=week_ago
        ).count()
        evening_ratings_week = EveningRating.objects.filter(
            is_active=True,
            rating_date__gte=week_ago
        ).count()
        saturday_reflections_week = SaturdayReflection.objects.filter(
            is_active=True,
            reflection_date__gte=week_ago
        ).count()
        
        # Последние ответы на касания (все типы вместе)
        recent_touch_answers = list(TouchAnswer.objects.filter(
            is_active=True
        ).select_related('user', 'touch_content').order_by('-touch_date', '-created_at')[:30])
        
        # Добавляем вычисляемое поле для номера вопроса
        for answer in recent_touch_answers:
            answer.question_number = answer.question_index + 1
        
        # Последние вечерние рефлексии
        recent_evening_reflections = EveningReflection.objects.filter(
            is_active=True
        ).select_related('user').order_by('-reflection_date', '-created_at')[:15]
        
        # Последние вечерние оценки
        recent_evening_ratings = EveningRating.objects.filter(
            is_active=True
        ).select_related('user').order_by('-rating_date', '-created_at')[:15]
        
        # Последние рефлексии стратсубботы
        recent_saturday_reflections = SaturdayReflection.objects.filter(
            is_active=True
        ).select_related('user').order_by('-reflection_date', '-created_at')[:15]
        
        context = {
            **self.admin_site.each_context(request),
            'title': 'Статистика всех касаний',
            'opts': self.model._meta,
            'touch_answers_by_type': touch_answers_by_type,
            'total_touch_answers': total_touch_answers,
            'evening_reflections_count': evening_reflections_count,
            'evening_ratings_count': evening_ratings_count,
            'avg_energy': avg_energy,
            'avg_happiness': avg_happiness,
            'avg_progress': avg_progress,
            'saturday_reflections_count': saturday_reflections_count,
            'touch_answers_week_morning': touch_answers_week_morning,
            'touch_answers_week_day': touch_answers_week_day,
            'touch_answers_week_evening': touch_answers_week_evening,
            'touch_answers_week_total': touch_answers_week_total,
            'evening_reflections_week': evening_reflections_week,
            'evening_ratings_week': evening_ratings_week,
            'saturday_reflections_week': saturday_reflections_week,
            'recent_touch_answers': recent_touch_answers,
            'recent_evening_reflections': recent_evening_reflections,
            'recent_evening_ratings': recent_evening_ratings,
            'recent_saturday_reflections': recent_saturday_reflections,
        }
        
        return render(request, 'admin/dashboard/unified_statistics.html', context)
    

