from django.contrib import admin
from .models import Person, Product, Order, OrderItem, Category

# Register your models here.
admin.site.register(Person)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Category)
