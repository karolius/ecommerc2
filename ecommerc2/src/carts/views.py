from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse
from django.http import Http404, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin, DetailView
from django.views.generic.edit import FormMixin

from orders.forms import GuestCheckForm
from orders.models import UserCheckout, Order, UserAddress
from products.models import Variation
from .models import Cart, CartItem


class ItemCountView(View):
    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            cart_item_count = 0
            cart_id = self.request.session.get("cart_id")
            if cart_id is not None:
                cart = Cart.objects.get(id=cart_id)
                cart_item_count = cart.items.count()

            # when we set it, it wont flip from 0 to c.i.c
            request.session["cart_item_count"] = cart_item_count
            return JsonResponse({"cart_item_count": cart_item_count})  # cart-count-badge
        raise Http404


class CartView(SingleObjectMixin, View):
    model = Cart
    template_name = "carts/view.html"

    def get_object(self, *args, **kwargs):
        self.request.session.set_expiry(0)  # as long as u not close browser
        cart_id = self.request.session.get("cart_id")

        cart = Cart.objects.get_or_create(id=cart_id)[0]
        if cart_id is None:
            self.request.session["cart_id"] = cart.id

        user = self.request.user
        if user.is_authenticated():
            cart.user = user
            cart.save()
        return cart

    def get(self, request, *args, **kwargs):
        cart = self.get_object()
        item_id = request.GET.get("item")
        delete_item = request.GET.get("delete", False)
        item_added = False
        flash_message = ""

        if item_id:
            item_instance = get_object_or_404(Variation, id=item_id)

            qty = int(request.GET.get("qty", 1))  # assume ist number
            try:
                if qty < 1:
                    delete_item = True
            except:
                raise Http404

            cart_item, cart_created = CartItem.objects.get_or_create(cart=cart, item=item_instance)
            if cart_created:
                flash_message = "Successfully added to the cart."
                item_added = True

            if delete_item:
                flash_message = "Item removed successfully."
                cart_item.delete()
            else:
                if not cart_created:
                    flash_message = "Quantity has been updated successfully."
                cart_item.quantity = qty
                cart_item.save()

            if not request.is_ajax():
                return HttpResponseRedirect(reverse("cart"))

        if request.is_ajax():
            try:
                line_total = cart_item.line_item_total
            except:
                line_total = None

            try:
                subtotal = cart_item.cart.subtotal  # cart.subtotal // shows prev (???)
            except:
                subtotal = None

            try:
                total_items = cart_item.cart.items.count()
            except:
                total_items = 0

            try:
                tax_total = cart_item.cart.tax_total
            except:
                tax_total = None

            try:
                total = cart_item.cart.total
            except:
                total = None

            data = {
                "deleted": delete_item,
                "flash_message": flash_message,
                "item_added": item_added,
                "line_total": line_total,
                "subtotal": subtotal,
                "tax_total": tax_total,
                "total": total,
                "total_items": total_items,
            }
            return JsonResponse(data)  # not Del/Add -> Updated

        context = {
            "object": cart,  # self.get_object()
        }
        template = self.template_name
        return render(request, template, context)


class CheckoutView(FormMixin, DetailView):
    model = Cart
    template_name = "carts/checkout_view.html"
    form_class = GuestCheckForm
    # use success_url = ... or method

    def get_object(self, *args, **kwargs):
        cart_id = self.request.session.get("cart_id")
        if cart_id is None:
            return redirect("cart")
        cart = Cart.objects.get(id=cart_id)
        return cart

    def get_order(self, *args, **kwargs):
        cart = self.get_object()
        order_id = self.request.session.get("order_id")
        if order_id is None:
            order = Order.objects.create(cart=cart)
            self.request.session["order_id"] = order.id
        else:
            order = Order.objects.get(id=order_id)
        return order

    def get_context_data(self, *args, **kwargs):
        context = super(CheckoutView, self).get_context_data(*args, **kwargs)
        user_auth = False
        user_checkout_id = self.request.session.get("user_checkout_id")
        user = self.request.user
        user_is_auth = user.is_authenticated()

        if user_is_auth:
            user_auth = True
            user_checkout, created = UserCheckout.objects.get_or_create(user=user)
            self.request.session["user_checkout_id"] = user_checkout.id
            if created:
                user_checkout.user = user
                user_checkout.save()
            else:
                print("-----DIFF user_checkout: %s      user: %s" % (user_checkout.user, user))
        elif user_is_auth and user_checkout_id is None:
            context["login_form"] = AuthenticationForm()
            context["next_url"] = self.request.build_absolute_uri()
        else:
            pass

        if user_checkout_id is not None:
            user_auth = True

        context["order"] = self.get_order()
        context["user_auth"] = user_auth
        context["form"] = self.get_form()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        form = self.get_form()
        if form.is_valid():
            email = form.cleaned_data.get("email")
            user_checkout = UserCheckout.objects.get_or_create(email=email)[0]
            request.session["user_checkout_id"] = user_checkout.id
            return self.form_valid(form)

        return self.form_invalid(form)

    def get_success_url(self):
        return reverse("checkout")

    def get(self, request, *args, **kwargs):
        get_data = super(CheckoutView, self).get(request, *args, **kwargs)
        user_checkout_id = request.session.get("user_checkout_id")
        if user_checkout_id is not None:
            user_checkout = UserCheckout.objects.get(id=user_checkout_id)
            billing_address_id = request.session.get("billing_address_id")
            shipping_address_id = request.session.get("shipping_address_id")
            if billing_address_id is None or shipping_address_id is None:
                return redirect("order_address")

            billing_address = UserAddress.objects.get(id=billing_address_id)
            shipping_address = UserAddress.objects.get(id=shipping_address_id)

            new_order = self.get_order()
            new_order.user = user_checkout
            new_order.billing_address = billing_address
            new_order.shipping_address = shipping_address
            new_order.save()
        return get_data