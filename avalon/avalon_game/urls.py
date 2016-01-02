from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^join/$', views.enter_code, name='enter_code'),
    url(r'^new/$', views.new_game, name='new_game'),
    url(r'^(?P<access_code>[a-z]{6})/', include([
        url(r'$', views.join_game, name='join_game'),
        url(r'(?P<player_secret>[a-z]{8})/', include([
            url(r'^$', views.game, name='game'),
            url(r'^ready/$', views.ready, name='ready'),
            url(r'^vote/(?P<round_num>[1-5])/(?P<vote_num>[1-5])/(?P<vote>(approve|reject))/$', views.vote, name='vote'),
            url(r'^choose/(?P<round_num>[1-5])/(?P<vote_num>[1-5])/(?P<who>[0-9]+)/$', views.choose, name='choose'),
            url(r'^remove/(?P<round_num>[1-5])/(?P<vote_num>[1-5])/(?P<who>[0-9]+)/$', views.remove, name='remove'),
            url(r'^mission/(?P<round_num>[1-5])/(?P<mission_action>(success|fail))/$', views.mission, name='mission'),
            url(r'^assassinate/(?P<target>[0-9]+)/$', views.choose, name='choose'),
        ])),
    ])),
]