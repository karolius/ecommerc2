from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_save, post_delete

from products.models import Variation


class CartItem(models.Model):  # as intermediate model
    cart = models.ForeignKey("Cart")
    item = models.ForeignKey(Variation)
    quantity = models.PositiveIntegerField(default=1)
    line_item_total = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return self.item.title

    def remove(self):
        return self.item.remove_from_cart()


def cart_item_pre_action_receiver(sender, instance, *args, **kwargs):
    qty = instance.quantity
    if qty >= 1:
        price = Decimal(instance.item.get_price())
        line_item_total = price * qty
        instance.line_item_total = line_item_total

pre_save.connect(cart_item_pre_action_receiver, sender=CartItem)


def cart_item_post_action_receiver(sender, instance, *args, **kwargs):
    instance.cart.update_subtotal()

post_save.connect(cart_item_post_action_receiver, sender=CartItem)
post_delete.connect(cart_item_post_action_receiver, sender=CartItem)


class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
    items = models.ManyToManyField(Variation, through=CartItem)
    timestamp = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=5, default=0.085)
    subtotal = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
    tax_total = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
    # discounts
    # shipping

    def __str__(self):
        return str(self.id)

    def update_subtotal(self):
        subtotal = 0
        cart_item_totals = self.cartitem_set.all()
        for cart_item in cart_item_totals:
            subtotal += cart_item.line_item_total
        self.subtotal = "{0:.2f}".format(subtotal)
        self.save()


def do_tax_and_receiver(sender, instance, *args, **kwargs):
    subtotal = Decimal(instance.subtotal)
    tax_total = round(subtotal * Decimal(instance.tax_percentage), 2)
    instance.tax_total = "{0:.2f}".format(tax_total)
    instance.total = "{0:.2f}".format(round(tax_total+subtotal, 2))

# Connected with pre_save because it doesnt need to be saved (as it would be in post_)
pre_save.connect(do_tax_and_receiver, sender=Cart)