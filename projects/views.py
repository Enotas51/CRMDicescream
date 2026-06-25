from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import ApprovedUserMixin, CanEditMixin, user_can_edit_object
from finance.balances import compute_finance_balances
from .equipment_order import InsufficientBalanceError, charge_equipment_order
from .forms import (
  ProjectEquipmentEditForm,
  ProjectEquipmentFormSet,
  ProjectEquipmentQuickForm,
  ProjectFileForm,
  ProjectForm,
  ProjectQuickUpdateForm,
)
from .models import Project, ProjectEquipment, ProjectFile
from .ozon import OzonFetchError, fetch_ozon_product, parse_ozon_text


def _redirect_project_detail(project):
  return redirect('projects:detail', pk=project.pk)


def _get_editable_project(request, pk):
  project = get_object_or_404(Project, pk=pk)
  if not user_can_edit_object(request.user, project):
    messages.error(request, 'Недостаточно прав.')
    return None
  return project


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
    return Project.objects.prefetch_related('members', 'equipment', 'files')

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['tasks'] = self.object.tasks.select_related('assignee').all()[:20]
    ctx['equipment'] = self.object.equipment.all()
    ctx['equipment_total'] = self.object.equipment_total
    ctx['project_files'] = self.object.files.select_related('created_by').all()
    ctx['can_edit'] = user_can_edit_object(self.request.user, self.object)
    balances = compute_finance_balances()
    ctx['main_balance'] = balances['main_balance']
    if ctx['can_edit']:
      ctx['quick_form'] = ProjectQuickUpdateForm(instance=self.object)
      ctx['equipment_add_form'] = ProjectEquipmentQuickForm()
      ctx['file_form'] = ProjectFileForm()
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
def project_quick_update_view(request, pk):
  project = _get_editable_project(request, pk)
  if not project:
    return redirect('projects:detail', pk=pk)

  form = ProjectQuickUpdateForm(request.POST, instance=project)
  if form.is_valid():
    form.save()
    messages.success(request, 'Проект обновлён.')
  else:
    messages.error(request, 'Не удалось сохранить изменения.')
  return _redirect_project_detail(project)


@require_POST
def project_equipment_add_view(request, pk):
  project = _get_editable_project(request, pk)
  if not project:
    return redirect('projects:detail', pk=pk)

  form = ProjectEquipmentQuickForm(request.POST)
  if form.is_valid():
    equipment = form.save(commit=False)
    equipment.project = project
    equipment.save()
    messages.success(request, 'Оборудование добавлено.')
  else:
    messages.error(request, 'Проверьте поля оборудования.')
  return _redirect_project_detail(project)


@require_POST
def project_equipment_update_view(request, pk, equipment_pk):
  project = _get_editable_project(request, pk)
  if not project:
    return redirect('projects:detail', pk=pk)

  equipment = get_object_or_404(ProjectEquipment, pk=equipment_pk, project=project)
  form = ProjectEquipmentEditForm(request.POST, instance=equipment)
  if form.is_valid():
    form.save()
    messages.success(request, 'Позиция обновлена.')
  else:
    messages.error(request, 'Не удалось обновить позицию.')
  return _redirect_project_detail(project)


@require_POST
def project_equipment_delete_view(request, pk, equipment_pk):
  project = _get_editable_project(request, pk)
  if not project:
    return redirect('projects:detail', pk=pk)

  equipment = get_object_or_404(ProjectEquipment, pk=equipment_pk, project=project)
  if equipment.order_transaction_id:
    messages.warning(request, 'Позиция удалена. Списание с баланса остаётся в финансах.')
  equipment.delete()
  messages.success(request, 'Позиция удалена.')
  return _redirect_project_detail(project)


@require_POST
def project_equipment_toggle_ordered_view(request, pk, equipment_pk):
  project = _get_editable_project(request, pk)
  if not project:
    return redirect('projects:detail', pk=pk)

  equipment = get_object_or_404(ProjectEquipment, pk=equipment_pk, project=project)
  want_ordered = request.POST.get('is_ordered') == 'on'

  if want_ordered and not equipment.is_ordered:
    try:
      charge_equipment_order(equipment, request.user)
    except InsufficientBalanceError as exc:
      messages.error(request, str(exc))
      return _redirect_project_detail(project)
    except ValueError as exc:
      messages.error(request, str(exc))
      return _redirect_project_detail(project)
    equipment.is_ordered = True
    equipment.save(update_fields=['is_ordered'])
    messages.success(request, f'Заказ оформлен, списано {equipment.total_price} ₽ с баланса.')
  elif not want_ordered and equipment.is_ordered:
    equipment.is_ordered = False
    equipment.save(update_fields=['is_ordered'])
    messages.info(request, 'Отметка «Заказал» снята. Списание в финансах сохранено.')
  return _redirect_project_detail(project)


@require_POST
def project_equipment_toggle_received_view(request, pk, equipment_pk):
  project = _get_editable_project(request, pk)
  if not project:
    return redirect('projects:detail', pk=pk)

  equipment = get_object_or_404(ProjectEquipment, pk=equipment_pk, project=project)
  equipment.is_received = request.POST.get('is_received') == 'on'
  equipment.save(update_fields=['is_received'])
  messages.success(request, 'Статус получения обновлён.')
  return _redirect_project_detail(project)


@require_POST
def project_file_upload_view(request, pk):
  project = _get_editable_project(request, pk)
  if not project:
    return redirect('projects:detail', pk=pk)

  form = ProjectFileForm(request.POST, request.FILES)
  if form.is_valid():
    project_file = form.save(commit=False)
    project_file.project = project
    project_file.created_by = request.user
    project_file.save()
    messages.success(request, 'Файл загружен.')
  else:
    messages.error(request, 'Не удалось загрузить файл.')
  return _redirect_project_detail(project)


@require_POST
def project_file_delete_view(request, pk, file_pk):
  project = _get_editable_project(request, pk)
  if not project:
    return redirect('projects:detail', pk=pk)

  project_file = get_object_or_404(ProjectFile, pk=file_pk, project=project)
  project_file.file.delete(save=False)
  project_file.delete()
  messages.success(request, 'Файл удалён.')
  return _redirect_project_detail(project)


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
