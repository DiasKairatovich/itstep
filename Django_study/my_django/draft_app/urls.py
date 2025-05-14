from django.urls import path, re_path
from . import views

urlpatterns = [

    #### Маршруты без регулярных выражений ###
    path('', views.home, name='home'),
    path('tasks/', views.view_tasks, name='task_list'),
    path('tasks/create/', views.create_task, name='task_create'),
    path('tasks/<int:id>/delete/', views.delete_task, name='task_delete'),
    path('tasks/<int:id>/uncomplete/', views.uncomplete_task, name='task_uncomplete'),
    path('tasks/export/csv/', views.export_csv, name='task_export_csv'),
    path('tasks/import/csv/', views.import_csv, name='task_import_csv'),
    path('tasks/search/', views.search_tasks, name='task_search'),

    #### Маршруты с регулярными выражениями ###
    re_path(r'^tasks/(?P<id>\d+)/$', views.view_task, name='task_detail'),
    re_path(r'^tasks/(?P<id>\d+)/edit/$', views.edit_task, name='task_edit'),
    re_path(r'^tasks/(?P<id>\d+)/complete/$', views.complete_task, name='task_complete'),
    re_path(r'^tasks/status/(?P<status>done|pending)/$', views.filter_by_status, name='task_filter_status'),
]

