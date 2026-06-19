from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import ApprovedUserMixin, CanEditMixin, user_can_edit_object
from .forms import TaskForm, TaskStatusForm
from .models import Task, TaskStatus


class TaskListView(ApprovedUserMixin, ListView):
  model = Task
  template_name = 'tasks/list.html'
  context_object_name = 'tasks'
  paginate_by = 30

  def get_queryset(self):
    qs = Task.objects.select_related('project', 'assignee', 'created_by')
    status = self.request.GET.get('status')
    project = self.request.GET.get('project')
    if status:
      qs = qs.filter(status=status)
    if project:
      qs = qs.filter(project_id=project)
    search = self.request.GET.get('q')
    if search:
      qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
    return qs


class TaskKanbanView(ApprovedUserMixin, ListView):
  model = Task
  template_name = 'tasks/kanban.html'
  context_object_name = 'tasks'

  def get_queryset(self):
    return Task.objects.select_related('project', 'assignee').all()

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    tasks = self.get_queryset()
    ctx['kanban_columns'] = [
      {
        'status': status,
        'label': label,
        'tasks': tasks.filter(status=status),
      }
      for status, label in TaskStatus.choices
    ]
    ctx['can_edit'] = self.request.user.can_edit
    return ctx


class TaskDetailView(ApprovedUserMixin, DetailView):
  model = Task
  template_name = 'tasks/detail.html'
  context_object_name = 'task'

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['can_edit'] = user_can_edit_object(self.request.user, self.object)
    return ctx


class TaskCreateView(CanEditMixin, CreateView):
  model = Task
  form_class = TaskForm
  template_name = 'tasks/form.html'

  def get_initial(self):
    initial = super().get_initial()
    project_id = self.request.GET.get('project')
    if project_id:
      initial['project'] = project_id
    return initial

  def form_valid(self, form):
    form.instance.created_by = self.request.user
    messages.success(self.request, 'Задача создана.')
    return super().form_valid(form)

  def get_success_url(self):
    return reverse_lazy('tasks:detail', kwargs={'pk': self.object.pk})


class TaskUpdateView(CanEditMixin, UpdateView):
  model = Task
  form_class = TaskForm
  template_name = 'tasks/form.html'

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and not user_can_edit_object(request.user, self.object):
      messages.error(request, 'Недостаточно прав.')
      return redirect('tasks:detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)

  def form_valid(self, form):
    messages.success(self.request, 'Задача обновлена.')
    return super().form_valid(form)

  def get_success_url(self):
    return reverse_lazy('tasks:detail', kwargs={'pk': self.object.pk})


class TaskDeleteView(CanEditMixin, DeleteView):
  model = Task
  template_name = 'tasks/confirm_delete.html'
  success_url = reverse_lazy('tasks:list')

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and self.object.created_by != request.user:
      messages.error(request, 'Недостаточно прав.')
      return redirect('tasks:detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)


def task_update_status(request, pk):
  if not request.user.can_edit:
    messages.error(request, 'Недостаточно прав.')
    return redirect('tasks:kanban')
  task = get_object_or_404(Task, pk=pk)
  if not request.user.is_admin and not user_can_edit_object(request.user, task):
    messages.error(request, 'Недостаточно прав.')
    return redirect('tasks:kanban')
  if request.method == 'POST':
    form = TaskStatusForm(request.POST, instance=task)
    if form.is_valid():
      form.save()
      messages.success(request, 'Статус обновлён.')
  return redirect('tasks:kanban')
