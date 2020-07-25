from django.urls import re_path, include

from . import views

urlpatterns = [
    # re_path("", views.index, name="index"),
    re_path(r"^$", views.now_playing, {"page": str(1)}, name="index"),
    re_path(r"^nowplaying/(?P<page>([1-9][0-9]{0,1}))/$", views.now_playing, name="nowplayingpage"),
    re_path(r"^artists/$", views.artists, name="artists"),
    re_path(r"^song/$", views.song, name="song"),
    re_path(r"^new/$", views.new, name="new"),
    re_path(r"^about/$", views.about, name="about"),
    re_path(r"^mostplayed/day/$", views.most_played_day, name="mostplayed-day"),
    re_path(r"^mostplayed/week/$", views.most_played_week, name="mostplayed-week"),
    re_path(r"^mostplayed/month/$", views.most_played_month, name="mostplayed-month")
]