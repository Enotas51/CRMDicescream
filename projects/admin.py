from django.contrib import admin

from .models import Project, ProjectEquipment, ProjectFile


class ProjectEquipmentInline(admin.TabularInline):
  model = ProjectEquipment
  extra = 0


class ProjectFileInline(admin.TabularInline):
  model = ProjectFile
  extra = 0
  readonly_fields = ('created_at',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
  list_display = ('name', 'status', 'budget', 'start_date', 'end_date')
  list_filter = ('status',)
  search_fields = ('name',)
  inlines = [ProjectEquipmentInline, ProjectFileInline]


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
  list_display = ('display_name', 'project', 'created_at', 'created_by')
  list_filter = ('project',)
