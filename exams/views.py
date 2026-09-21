from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Attempt, Subject, Test


def home(request):
    tests = (
        Test.objects.filter(is_published=True)
        .select_related("subject")
        .annotate(question_total=Count("questions", distinct=True))
    )
    subjects = Subject.objects.filter(tests__is_published=True).distinct()
    active_subject = request.GET.get("subject")
    if active_subject:
        tests = tests.filter(subject__slug=active_subject)
    return render(
        request,
        "exams/home.html",
        {"tests": tests, "subjects": subjects, "active_subject": active_subject},
    )


def test_detail(request, slug):
    test = get_object_or_404(Test.objects.select_related("subject"), slug=slug, is_published=True)
    my_attempts = []
    if request.user.is_authenticated:
        my_attempts = test.attempts.filter(user=request.user, submitted_at__isnull=False)[:5]
    top_scores = (
        test.attempts.filter(submitted_at__isnull=False)
        .values("user__username")
        .annotate(best=Max("score"))
        .order_by("-best")[:5]
    )
    return render(
        request,
        "exams/test_detail.html",
        {
            "test": test,
            "question_total": test.questions.count(),
            "my_attempts": my_attempts,
            "top_scores": top_scores,
        },
    )


@login_required
@require_POST
def start_test(request, slug):
    test = get_object_or_404(Test, slug=slug, is_published=True)
    if not test.questions.exists():
        messages.error(request, "This test has no questions yet.")
        return redirect(test)

    # Resume an attempt that is still running instead of starting a second one.
    for attempt in test.attempts.filter(user=request.user, submitted_at__isnull=True):
        if attempt.accepts_answers():
            return redirect("exams:take_test", attempt_id=attempt.id)
        attempt.grade({})

    attempt = Attempt.objects.create(user=request.user, test=test)
    return redirect("exams:take_test", attempt_id=attempt.id)


def _own_attempt(request, attempt_id):
    return get_object_or_404(Attempt.objects.select_related("test"), id=attempt_id, user=request.user)


@login_required
def take_test(request, attempt_id):
    attempt = _own_attempt(request, attempt_id)
    if attempt.is_submitted:
        return redirect("exams:result", attempt_id=attempt.id)
    if not attempt.accepts_answers():
        attempt.grade({})
        messages.warning(request, "Time ran out before this test was submitted.")
        return redirect("exams:result", attempt_id=attempt.id)

    questions = attempt.test.questions.prefetch_related("choices")
    return render(
        request,
        "exams/take_test.html",
        {"attempt": attempt, "questions": questions, "seconds_left": attempt.seconds_left()},
    )


@login_required
@require_POST
def submit_test(request, attempt_id):
    attempt = _own_attempt(request, attempt_id)
    if attempt.is_submitted:
        return redirect("exams:result", attempt_id=attempt.id)

    if not attempt.accepts_answers():
        attempt.grade({})
        messages.warning(request, "Time was up, so answers sent after the deadline were not counted.")
        return redirect("exams:result", attempt_id=attempt.id)

    selected = {}
    for key, value in request.POST.items():
        if key.startswith("q_"):
            try:
                selected[int(key[2:])] = int(value)
            except ValueError:
                continue
    attempt.grade(selected)
    return redirect("exams:result", attempt_id=attempt.id)


@login_required
def result(request, attempt_id):
    attempt = _own_attempt(request, attempt_id)
    if not attempt.is_submitted:
        return redirect("exams:take_test", attempt_id=attempt.id)

    answers = {a.question_id: a for a in attempt.answers.select_related("choice")}
    review = [
        {"question": q, "answer": answers.get(q.id)}
        for q in attempt.test.questions.prefetch_related("choices")
    ]
    return render(request, "exams/result.html", {"attempt": attempt, "review": review})


@login_required
def dashboard(request):
    attempts = request.user.attempts.filter(submitted_at__isnull=False).select_related("test__subject")
    stats = attempts.aggregate(taken=Count("id"), tests=Count("test", distinct=True))
    percentages = [a.percentage for a in attempts]
    stats["average"] = round(sum(percentages) / len(percentages)) if percentages else 0
    stats["best"] = max(percentages, default=0)
    return render(request, "exams/dashboard.html", {"attempts": attempts[:20], "stats": stats})


def signup(request):
    if request.user.is_authenticated:
        return redirect("exams:dashboard")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Pick a test to get started.")
        return redirect("exams:home")
    return render(request, "registration/signup.html", {"form": form})
