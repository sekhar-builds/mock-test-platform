from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

# Extra seconds allowed after the deadline, so an auto-submit that is still in
# flight when the timer hits zero is not rejected because of network latency.
SUBMIT_GRACE_SECONDS = 30


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Test(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="tests")
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=10)
    marks_per_question = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    negative_marks = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text="Marks deducted for each wrong answer. Unanswered questions lose nothing.",
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["subject__name", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("exams:test_detail", args=[self.slug])

    @property
    def max_score(self):
        return self.marks_per_question * self.questions.count()


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    explanation = models.TextField(blank=True, help_text="Shown to students after they submit.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:80]

    @property
    def correct_choice(self):
        return next((c for c in self.choices.all() if c.is_correct), None)


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.text


class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    unanswered_count = models.PositiveIntegerField(default=0)
    score = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user} - {self.test}"

    @property
    def deadline(self):
        return self.started_at + timedelta(minutes=self.test.duration_minutes)

    @property
    def is_submitted(self):
        return self.submitted_at is not None

    def seconds_left(self, now=None):
        now = now or timezone.now()
        return max(0, int((self.deadline - now).total_seconds()))

    def accepts_answers(self, now=None):
        now = now or timezone.now()
        return not self.is_submitted and now <= self.deadline + timedelta(seconds=SUBMIT_GRACE_SECONDS)

    @property
    def total_questions(self):
        return self.correct_count + self.wrong_count + self.unanswered_count

    @property
    def percentage(self):
        max_score = self.test.max_score
        if not max_score:
            return 0
        return max(0, round(float(self.score) / float(max_score) * 100))

    def grade(self, selected_choice_ids):
        """Record the student's answers and score the attempt.

        `selected_choice_ids` maps question id -> choice id. Ids that do not
        belong to this test are ignored, so a tampered form cannot score
        answers from another test or pick a choice from another question.
        """
        questions = list(self.test.questions.prefetch_related("choices"))
        correct = wrong = 0
        answers = []
        for question in questions:
            choices = {c.id: c for c in question.choices.all()}
            choice = choices.get(selected_choice_ids.get(question.id))
            answers.append(Answer(attempt=self, question=question, choice=choice))
            if choice is None:
                continue
            if choice.is_correct:
                correct += 1
            else:
                wrong += 1

        self.answers.all().delete()
        Answer.objects.bulk_create(answers)
        self.correct_count = correct
        self.wrong_count = wrong
        self.unanswered_count = len(questions) - correct - wrong
        self.score = correct * self.test.marks_per_question - wrong * self.test.negative_marks
        self.submitted_at = timezone.now()
        self.save()


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="one_answer_per_question"),
        ]

    @property
    def is_correct(self):
        return self.choice is not None and self.choice.is_correct
