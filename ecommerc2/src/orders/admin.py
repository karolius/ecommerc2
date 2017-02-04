from django.contrib import admin

from .models import UserCheckout, UserAddress, Order


class UserCheckoutAdmin(admin.ModelAdmin):
    list_display = ['id', '__str__', 'user']

    class Mete:
        model = UserCheckout


class UserAddressAdmin(admin.ModelAdmin):
    list_display = ['id', '__str__', 'user']

    class Mete:
        model = UserAddress


admin.site.register(UserCheckout, UserCheckoutAdmin)
admin.site.register(UserAddress, UserAddressAdmin)
admin.site.register(Order)