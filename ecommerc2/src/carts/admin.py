from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    # extra = 3
    # max_num = 15


class CartAdmin(admin.ModelAdmin):
    inlines = [
        CartItemInline,
    ]

    class Mete:
        model = Cart


admin.site.register(Cart, CartAdmin)