from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .decorators import partner_required
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from .forms import CustomPasswordResetForm

app_name = "app"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.category_list, name="category_list"),
    path("products/menu/", views.products_menu, name="products_menu"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/new/", views.order_create, name="order_create"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/delete/", views.order_delete, name="order_delete"),
    path(
        "orders/<int:order_id>/mark_paid/",
        views.order_mark_paid,
        name="order_mark_paid",
    ),
    path("orders/pay-bulk/", 
        views.order_mark_paid, 
        name="order_pay_bulk"),
    path(
        "people/", partner_required(views.PersonListView.as_view()), name="person_list"
    ),
    path("people/new/", views.person_create_api, name="api_person_create"),
    path("profile/<int:person_id>/", views.profile, name="profile"),
    path(
        "profile/edit/<int:pk>/",
        views.PersonUpdateView.as_view(),
        name="update_profile",
    ),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path(
        "force_password_change/",
        views.force_password_change,
        name="force_password_change",
    ),
    path(
        "upload_profile_picture/",
        views.upload_profile_picture,
        name="upload_profile_picture",
    ),
    path(
        "delete_profile_picture/",
        views.delete_profile_picture,
        name="delete_profile_picture",
    ),
    path("sezione/", views.sezione_view, name="sezione"),
    path("api/orders/export/", views.export_orders_api, name="export_orders_api"),
    path("api/check-party-mode/", views.check_party_mode, name="check_party_mode"),
    path("api/set-party-mode/", views.toggle_party_mode, name="set_party_mode"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="app/emails/password_reset_form.html",
            email_template_name="app/emails/password_reset_email.html",
            subject_template_name="app/emails/password_reset_subject.txt",
            form_class=CustomPasswordResetForm,
            success_url=reverse_lazy("app:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="app/emails/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="app/emails/password_reset_confirm.html",
            success_url=reverse_lazy("app:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="app/emails/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
