from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import ApprovedUserMixin, CanEditMixin, user_can_edit_object
from .forms import ProjectEquipmentFormSet, ProjectForm
from .models import Project
from .ozon import OzonFetchError, fetch_ozon_product, parse_ozon_text


class ProjectListView(ApprovedUserMixin, ListView):
  model = Project
  template_name = 'projects/list.html'
  context_object_name = 'projects'
  paginate_by = 20

  def get_queryset(self):
    qs = Project.objects.prefetch_related('members', 'tasks', 'equipment')
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

  def get_queryset(self):
    return Project.objects.prefetch_related('members', 'equipment')

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['tasks'] = self.object.tasks.select_related('assignee').all()[:20]
    ctx['equipment'] = self.object.equipment.all()
    ctx['equipment_total'] = self.object.equipment_total
    ctx['can_edit'] = user_can_edit_object(self.request.user, self.object)
    return ctx


class ProjectCreateView(CanEditMixin, CreateView):
  model = Project
  form_class = ProjectForm
  template_name = 'projects/form.html'
  success_url = reverse_lazy('projects:list')

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    if self.request.POST:
      ctx['equipment_formset'] = ProjectEquipmentFormSet(self.request.POST, prefix='equipment')
    else:
      ctx['equipment_formset'] = ProjectEquipmentFormSet(prefix='equipment')
    return ctx

  def post(self, request, *args, **kwargs):
    self.object = None
    form = self.get_form()
    formset = ProjectEquipmentFormSet(self.request.POST, prefix='equipment')
    if form.is_valid() and formset.is_valid():
      return self.form_valid(form, formset)
    return self.form_invalid(form, formset)

  def form_valid(self, form, formset):
    form.instance.created_by = self.request.user
    self.object = form.save()
    formset.instance = self.object
    formset.save()
    messages.success(self.request, 'Проект создан.')
    return redirect(self.success_url)

  def form_invalid(self, form, formset):
    return self.render_to_response(
      self.get_context_data(form=form, equipment_formset=formset),
    )


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

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    if self.request.POST:
      ctx['equipment_formset'] = ProjectEquipmentFormSet(
        self.request.POST,
        instance=self.object,
        prefix='equipment',
      )
    else:
      ctx['equipment_formset'] = ProjectEquipmentFormSet(
        instance=self.object,
        prefix='equipment',
      )
    return ctx

  def post(self, request, *args, **kwargs):
    self.object = self.get_object()
    form = self.get_form()
    formset = ProjectEquipmentFormSet(self.request.POST, instance=self.object, prefix='equipment')
    if form.is_valid() and formset.is_valid():
      return self.form_valid(form, formset)
    return self.form_invalid(form, formset)

  def form_valid(self, form, formset):
    self.object = form.save()
    formset.save()
    messages.success(self.request, 'Проект обновлён.')
    return redirect(self.get_success_url())

  def form_invalid(self, form, formset):
    return self.render_to_response(
      self.get_context_data(form=form, equipment_formset=formset),
    )

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


@require_POST
def fetch_ozon_product_view(request):
  if not request.user.is_authenticated or not request.user.can_edit:
    return JsonResponse({'error': 'Недостаточно прав.'}, status=403)

  text = request.POST.get('text', '').strip()
  if text:
    try:
      data = parse_ozon_text(text)
      return JsonResponse(data)
    except OzonFetchError as exc:
      return JsonResponse({'error': str(exc)}, status=400)
    except Exception:
      return JsonResponse(
        {'error': 'Не удалось разобрать вставленный текст.'},
        status=400,
      )

  url = request.POST.get('url', '').strip()
  if not url:
    return JsonResponse({'error': 'Укажите ссылку или вставьте текст с OZON.'}, status=400)

  try:
    data = fetch_ozon_product(url, allow_partial=True)
    return JsonResponse(data)
  except OzonFetchError as exc:
    return JsonResponse({'error': str(exc)}, status=400)
  except Exception:
    return JsonResponse(
      {'error': 'Автозагрузка недоступна. Скопируйте текст с OZON и нажмите «Вставить текст».'},
      status=502,
    )
