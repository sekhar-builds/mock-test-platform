from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Attempt, Choice, Question, Subject, Test


def make_test(questions=3, negative="0", published=True, slug="sample"):
    subject = Subject.objects.get_or_create(name="History", slug="history")[0]
    test = Test.objects.create(
        subject=subject,
        title="Sample",
        slug=slug,
        duration_minutes=10,
        marks_per_question=2,
        negative_marks=Decimal(negative),
        is_published=published,
    )
    for i in range(questions):
        q = Question.objects.create(test=test, text=f"Question {i}", order=i)
        Choice.objects.create(question=q, text="right", is_correct=True)
        Choice.objects.create(question=q, text="wrong", is_correct=False)
    return test


def pick(test, correct):
    """Map every question to its right (or wrong) choice id."""
    return {q.id: q.choices.get(is_correct=correct).id for q in test.questions.all()}


class GradingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("student", password="pw")

    def test_scores_correct_wrong_and_skipped(self):
        test = make_test(questions=3, negative="0.5")
        right, wrong = pick(test, True), pick(test, False)
        q1, q2, _ = test.questions.all()
        attempt = Attempt.objects.create(user=self.user, test=test)

        attempt.grade({q1.id: right[q1.id], q2.id: wrong[q2.id]})

        self.assertEqual((attempt.correct_count, attempt.wrong_count, attempt.unanswered_count), (1, 1, 1))
        self.assertEqual(attempt.score, Decimal("1.5"))  # 2 - 0.5
        self.assertEqual(attempt.answers.count(), 3)
        self.assertTrue(attempt.is_submitted)

    def test_choice_from_another_question_is_ignored(self):
        test = make_test(questions=2)
        q1, q2 = test.questions.all()
        attempt = Attempt.objects.create(user=self.user, test=test)

        attempt.grade({q1.id: q2.choices.get(is_correct=True).id})

        self.assertEqual(attempt.correct_count, 0)
        self.assertEqual(attempt.unanswered_count, 2)

    def test_percentage_never_negative(self):
        test = make_test(questions=2, negative="1")
        attempt = Attempt.objects.create(user=self.user, test=test)
        attempt.grade(pick(test, False))
        self.assertLess(attempt.score, 0)
        self.assertEqual(attempt.percentage, 0)


class FlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("student", password="pw")
        self.client.force_login(self.user)
        self.test = make_test()

    def start(self):
        self.client.post(reverse("exams:start_test", args=[self.test.slug]))
        return Attempt.objects.get(user=self.user, submitted_at__isnull=True)

    def submit(self, attempt, answers):
        data = {f"q_{qid}": cid for qid, cid in answers.items()}
        return self.client.post(reverse("exams:submit_test", args=[attempt.id]), data)

    def test_full_flow(self):
        attempt = self.start()
        self.assertContains(self.client.get(reverse("exams:take_test", args=[attempt.id])), "Question 0")

        response = self.submit(attempt, pick(self.test, True))

        self.assertRedirects(response, reverse("exams:result", args=[attempt.id]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.correct_count, 3)
        self.assertEqual(attempt.percentage, 100)
        self.assertContains(self.client.get(reverse("exams:dashboard")), "100%")

    def test_starting_twice_resumes_the_same_attempt(self):
        first = self.start()
        self.start()
        self.assertEqual(Attempt.objects.filter(user=self.user).count(), 1)
        self.assertEqual(first.id, Attempt.objects.get().id)

    def test_resubmitting_does_not_change_the_score(self):
        attempt = self.start()
        self.submit(attempt, pick(self.test, False))
        self.submit(attempt, pick(self.test, True))
        attempt.refresh_from_db()
        self.assertEqual(attempt.correct_count, 0)

    def test_answers_after_deadline_are_not_counted(self):
        attempt = self.start()
        Attempt.objects.filter(id=attempt.id).update(started_at=timezone.now() - timedelta(minutes=11))

        self.submit(attempt, pick(self.test, True))

        attempt.refresh_from_db()
        self.assertTrue(attempt.is_submitted)
        self.assertEqual(attempt.correct_count, 0)

    def test_answers_within_grace_period_count(self):
        attempt = self.start()
        Attempt.objects.filter(id=attempt.id).update(
            started_at=timezone.now() - timedelta(minutes=10, seconds=10)
        )
        self.submit(attempt, pick(self.test, True))
        attempt.refresh_from_db()
        self.assertEqual(attempt.correct_count, 3)

    def test_other_students_cannot_see_an_attempt(self):
        attempt = self.start()
        self.submit(attempt, pick(self.test, True))
        other = get_user_model().objects.create_user("other", password="pw")
        self.client.force_login(other)
        for name in ["take_test", "result"]:
            self.assertEqual(self.client.get(reverse(f"exams:{name}", args=[attempt.id])).status_code, 404)

    def test_unpublished_tests_are_hidden(self):
        hidden = make_test(published=False, slug="hidden")
        self.assertNotContains(self.client.get(reverse("exams:home")), reverse("exams:test_detail", args=[hidden.slug]))
        self.assertEqual(self.client.get(reverse("exams:test_detail", args=[hidden.slug])).status_code, 404)

    def test_login_required_to_start(self):
        self.client.logout()
        response = self.client.post(reverse("exams:start_test", args=[self.test.slug]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertFalse(Attempt.objects.exists())


class SeedTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command("seed_demo", stdout=StringIO())
        count = Question.objects.count()
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Question.objects.count(), count)
        self.assertTrue(get_user_model().objects.filter(username="demo").exists())
        for question in Question.objects.prefetch_related("choices"):
            self.assertEqual(sum(c.is_correct for c in question.choices.all()), 1, question.text)
