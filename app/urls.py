from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .decorators import partner_required

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
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
