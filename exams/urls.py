from django.urls import path

from . import views

app_name = "exams"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("tests/<slug:slug>/", views.test_detail, name="test_detail"),
    path("tests/<slug:slug>/start/", views.start_test, name="start_test"),
    path("attempts/<int:attempt_id>/", views.take_test, name="take_test"),
    path("attempts/<int:attempt_id>/submit/", views.submit_test, name="submit_test"),
    path("attempts/<int:attempt_id>/result/", views.result, name="result"),
]
