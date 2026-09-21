from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.urls import reverse
from django.utils.html import format_html

from .models import Attempt, Choice, Question, Subject, Test

admin.site.site_header = "Mock Test Platform - Admin"
admin.site.site_title = "Mock Test Admin"
admin.site.index_title = "Manage tests, questions and results"


class ChoiceFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        kept = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        if len(kept) < 2:
            raise ValidationError("A question needs at least two options.")
        if sum(1 for data in kept if data.get("is_correct")) != 1:
            raise ValidationError("Mark exactly one option as correct.")


class ChoiceInline(admin.TabularInline):
    model = Choice
    formset = ChoiceFormSet
    extra = 4
    max_num = 6


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["short_text", "test", "order"]
    list_filter = ["test__subject", "test"]
    search_fields = ["text"]
    inlines = [ChoiceInline]

    @admin.display(description="Question")
    def short_text(self, obj):
        return str(obj)


class QuestionInline(admin.TabularInline):
    model = Question
    fields = ["order", "text", "edit_link"]
    readonly_fields = ["edit_link"]
    extra = 0
    show_change_link = True

    @admin.display(description="Options")
    def edit_link(self, obj):
        if not obj.pk:
            return "Save first, then add options"
        url = reverse("admin:exams_question_change", args=[obj.pk])
        return format_html('<a href="{}">Edit options ({})</a>', url, obj.choices.count())


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ["title", "subject", "question_count", "duration_minutes", "is_published"]
    list_filter = ["subject", "is_published"]
    list_editable = ["is_published"]
    search_fields = ["title"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [QuestionInline]

    @admin.display(description="Questions")
    def question_count(self, obj):
        return obj.questions.count()


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ["user", "test", "score", "correct_count", "wrong_count", "started_at", "submitted_at"]
    list_filter = ["test"]
    search_fields = ["user__username", "test__title"]
    readonly_fields = [f.name for f in Attempt._meta.fields]

    def has_add_permission(self, request):
        return False
