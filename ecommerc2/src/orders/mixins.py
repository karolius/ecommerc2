from .models import Order
from carts.models import Cart


class CartOrderMixin(object):
    def get_cart(self, *args, **kwargs):
        cart_id = self.request.session.get("cart_id")
        if cart_id is None:
            return None
        cart = Cart.objects.get(id=cart_id)
        if cart.items.count() < 1:
            return None
        return cart

    def get_order(self, *args, **kwargs):
        cart = self.get_cart()
        if cart is None:
            return None

        order_id = self.request.session.get("order_id")
        if order_id is None:
            order = Order.objects.create(cart=cart)
            self.request.session["order_id"] = order.id
        else:
            order = Order.objects.get(id=order_id)
        return order