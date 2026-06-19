from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import ApprovedUserMixin, CanEditMixin, user_can_edit_object
from .forms import DebtDebtorFormSet, DebtForm, LinkDebtorForm
from .models import Debt, DebtDebtor, DebtStatus


class DebtListView(ApprovedUserMixin, ListView):
  model = Debt
  template_name = 'debts/list.html'
  context_object_name = 'debts'
  paginate_by = 30

  def get_queryset(self):
    qs = Debt.objects.select_related('creditor_user', 'project').prefetch_related('debtors')
    status = self.request.GET.get('status')
    if status:
      qs = qs.filter(status=status)
    search = self.request.GET.get('q')
    if search:
      qs = qs.filter(title__icontains=search)
    return qs

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['can_edit'] = self.request.user.can_edit
    return ctx


class DebtDetailView(ApprovedUserMixin, DetailView):
  model = Debt
  template_name = 'debts/detail.html'
  context_object_name = 'debt'

  def get_queryset(self):
    return Debt.objects.prefetch_related('debtors__debtor_user')

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    debt = self.object
    ctx['debtors'] = debt.debtors.select_related('debtor_user').all()
    ctx['repayments'] = debt.repayments.select_related(
      'debt_debtor', 'debt_debtor__debtor_user', 'created_by',
    ).order_by('-date')
    ctx['repaid_amount'] = debt.get_repaid_amount()
    ctx['remaining_amount'] = debt.remaining_amount
    ctx['utilities_credited'] = debt.get_utilities_credited()
    ctx['can_edit'] = user_can_edit_object(self.request.user, debt)
    ctx['link_form'] = LinkDebtorForm()
    ctx['show_link_creditor'] = not debt.creditor_user and debt.creditor_name
    return ctx


class DebtCreateView(CanEditMixin, CreateView):
  model = Debt
  form_class = DebtForm
  template_name = 'debts/form.html'
  success_url = reverse_lazy('debts:list')

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    if self.request.POST:
      ctx['debtor_formset'] = DebtDebtorFormSet(self.request.POST)
    else:
      ctx['debtor_formset'] = DebtDebtorFormSet()
    return ctx

  def post(self, request, *args, **kwargs):
    self.object = None
    form = self.get_form()
    formset = DebtDebtorFormSet(self.request.POST)
    if form.is_valid() and formset.is_valid():
      return self.form_valid(form, formset)
    return self.form_invalid(form, formset)

  def form_valid(self, form, formset):
    form.instance.created_by = self.request.user
    self.object = form.save()
    formset.instance = self.object
    formset.save()
    self.object.recalculate_amount()
    messages.success(self.request, 'Задолженность создана.')
    return redirect(self.success_url)

  def form_invalid(self, form, formset):
    return self.render_to_response(self.get_context_data(form=form, debtor_formset=formset))


class DebtUpdateView(CanEditMixin, UpdateView):
  model = Debt
  form_class = DebtForm
  template_name = 'debts/form.html'

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and not user_can_edit_object(request.user, self.object):
      messages.error(request, 'Недостаточно прав.')
      return redirect('debts:detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    if self.request.POST:
      ctx['debtor_formset'] = DebtDebtorFormSet(self.request.POST, instance=self.object)
    else:
      ctx['debtor_formset'] = DebtDebtorFormSet(instance=self.object)
    return ctx

  def post(self, request, *args, **kwargs):
    self.object = self.get_object()
    form = self.get_form()
    formset = DebtDebtorFormSet(self.request.POST, instance=self.object)
    if form.is_valid() and formset.is_valid():
      return self.form_valid(form, formset)
    return self.form_invalid(form, formset)

  def form_valid(self, form, formset):
    self.object = form.save()
    formset.save()
    self.object.recalculate_amount()
    self.object.refresh_status()
    messages.success(self.request, 'Задолженность обновлена.')
    return redirect(self.get_success_url())

  def form_invalid(self, form, formset):
    return self.render_to_response(self.get_context_data(form=form, debtor_formset=formset))

  def get_success_url(self):
    return reverse_lazy('debts:detail', kwargs={'pk': self.object.pk})


class DebtDeleteView(CanEditMixin, DeleteView):
  model = Debt
  template_name = 'debts/confirm_delete.html'
  success_url = reverse_lazy('debts:list')

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin:
      messages.error(request, 'Удалять может только администратор.')
      return redirect('debts:detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)


def link_creditor(request, pk):
  if not request.user.can_edit:
    messages.error(request, 'Недостаточно прав.')
    return redirect('debts:list')
  debt = get_object_or_404(Debt, pk=pk)
  if request.method != 'POST':
    return redirect('debts:detail', pk=pk)

  user_id = request.POST.get('user')
  if user_id:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    debt.creditor_user = user
    debt.sync_creditor_name()
    debt.save(update_fields=['creditor_user', 'creditor_name'])
    messages.success(request, f'Кредитор привязан к пользователю {user.username}.')
  return redirect('debts:detail', pk=pk)


def link_debtor(request, pk, debtor_pk):
  if not request.user.can_edit:
    messages.error(request, 'Недостаточно прав.')
    return redirect('debts:list')
  debt = get_object_or_404(Debt, pk=pk)
  debtor = get_object_or_404(DebtDebtor, pk=debtor_pk, debt=debt)
  if request.method != 'POST':
    return redirect('debts:detail', pk=pk)

  form = LinkDebtorForm(request.POST)
  if form.is_valid():
    user = form.cleaned_data['user']
    debtor.debtor_user = user
    debtor.sync_name()
    debtor.save(update_fields=['debtor_user', 'debtor_name'])
    messages.success(request, f'Должник «{debtor.display_name}» привязан к {user.username}.')
  else:
    messages.error(request, 'Не удалось привязать пользователя.')
  return redirect('debts:detail', pk=pk)
