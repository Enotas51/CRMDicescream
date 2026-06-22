from django.contrib import admin

from .models import Project, ProjectEquipment


class ProjectEquipmentInline(admin.TabularInline):
  model = ProjectEquipment
  extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
  list_display = ('name', 'status', 'budget', 'start_date', 'end_date')
  list_filter = ('status',)
  search_fields = ('name',)
  inlines = [ProjectEquipmentInline]
