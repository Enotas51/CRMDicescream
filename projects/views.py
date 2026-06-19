from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import ApprovedUserMixin, CanEditMixin, user_can_edit_object
from .forms import ProjectForm
from .models import Project


class ProjectListView(ApprovedUserMixin, ListView):
  model = Project
  template_name = 'projects/list.html'
  context_object_name = 'projects'
  paginate_by = 20

  def get_queryset(self):
    qs = Project.objects.prefetch_related('members', 'tasks')
    status = self.request.GET.get('status')
    if status:
      qs = qs.filter(status=status)
    search = self.request.GET.get('q')
    if search:
      qs = qs.filter(name__icontains=search)
    return qs


class ProjectDetailView(ApprovedUserMixin, DetailView):
  model = Project
  template_name = 'projects/detail.html'
  context_object_name = 'project'

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['tasks'] = self.object.tasks.select_related('assignee').all()[:20]
    ctx['can_edit'] = user_can_edit_object(self.request.user, self.object)
    return ctx


class ProjectCreateView(CanEditMixin, CreateView):
  model = Project
  form_class = ProjectForm
  template_name = 'projects/form.html'
  success_url = reverse_lazy('projects:list')

  def form_valid(self, form):
    form.instance.created_by = self.request.user
    messages.success(self.request, 'Проект создан.')
    return super().form_valid(form)


class ProjectUpdateView(CanEditMixin, UpdateView):
  model = Project
  form_class = ProjectForm
  template_name = 'projects/form.html'

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and not user_can_edit_object(request.user, self.object):
      messages.error(request, 'Недостаточно прав для редактирования.')
      return redirect('projects:detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)

  def form_valid(self, form):
    messages.success(self.request, 'Проект обновлён.')
    return super().form_valid(form)

  def get_success_url(self):
    return reverse_lazy('projects:detail', kwargs={'pk': self.object.pk})


class ProjectDeleteView(CanEditMixin, DeleteView):
  model = Project
  template_name = 'projects/confirm_delete.html'
  success_url = reverse_lazy('projects:list')

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin:
      messages.error(request, 'Удалять проекты может только администратор.')
      return redirect('projects:detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)
