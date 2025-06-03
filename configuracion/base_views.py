from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q

def is_admin_user(user):
    """Verificar si el usuario tiene permisos de administrador"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)

class AdminUserRequiredMixin(UserPassesTestMixin):
    """Mixin para requerir permisos de administrador"""
    def test_func(self):
        return is_admin_user(self.request.user)

class BaseConfiguracionMixin(LoginRequiredMixin, AdminUserRequiredMixin):
    """Mixin base para todas las vistas de configuración"""
    
    def get_success_message(self, cleaned_data):
        """Obtener mensaje de éxito para formularios"""
        return f'{self.model._meta.verbose_name} {self.success_message}'

class BaseCRUDMixin(BaseConfiguracionMixin):
    """Mixin base para vistas CRUD"""
    def get_success_url(self):
        return reverse_lazy(f'configuracion_web:{self.url_prefix}-list')
    
    def form_valid(self, form):
        """Método común para manejar formularios válidos"""
        response = super().form_valid(form)
        messages.success(self.request, self.get_success_message(form.cleaned_data))
        return response

class BaseListView(BaseCRUDMixin, ListView):
    """Vista base para listados"""
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        if search and hasattr(self.model, 'get_search_fields'):
            search_fields = self.model.get_search_fields()
            query = None
            for field in search_fields:
                q = Q(**{f"{field}__icontains": search})
                query = q if query is None else query | q
            if query:
                queryset = queryset.filter(query)
        return queryset

class BaseCreateView(BaseCRUDMixin, CreateView):
    """Vista base para crear registros"""
    success_message = "creado exitosamente"

class BaseUpdateView(BaseCRUDMixin, UpdateView):
    """Vista base para actualizar registros"""
    success_message = "actualizado exitosamente"

class BaseDeleteView(BaseCRUDMixin, DeleteView):
    """Vista base para eliminar registros"""
    success_message = "eliminado exitosamente"