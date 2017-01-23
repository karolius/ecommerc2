from django.conf import settings
from django.db import models

from carts.models import Cart


class UserCheckout(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True)  # not required
    email = models.EmailField(unique=True)  # required

    def __str__(self):
        return self.email


ADDRESS_TYPE = (
    ('billing', 'Billing'),
    ('shipping', 'Shipping'),
)


class UserAddress(models.Model):
    user = models.ForeignKey(UserCheckout)
    type = models.CharField(max_length=120, choices=ADDRESS_TYPE)
    street = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120)
    zipcode = models.CharField(max_length=120)

    def __str__(self):
        return self.street


class Order (models.Model):
    user = models.ForeignKey(UserCheckout)
    cart = models.ForeignKey(Cart)
    billing_address = models.ForeignKey(UserAddress, related_name="billing_address")
    shipping_address = models.ForeignKey(UserAddress, related_name="shipping_address")
    shipping_total_price = models.DecimalField(max_digits=30, default=5.99, decimal_places=2)
    order_total = models.DecimalField(max_digits=30, default=0.00, decimal_places=2)

    def __str__(self):
        return str(self.cart.id)