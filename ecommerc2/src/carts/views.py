import braintree
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse
from django.http import Http404, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin, DetailView
from django.views.generic.edit import FormMixin

from orders.forms import GuestCheckForm
from orders.mixins import CartOrderMixin
from orders.models import UserCheckout
from products.models import Variation
from .models import Cart, CartItem

if settings.DEBUG:
    braintree.Configuration.configure(
        braintree.Environment.Sandbox,
        merchant_id=settings.BRAINTREE_MERCHANT_ID,
        public_key=settings.BRAINTREE_PUBLIC,
        private_key=settings.BRAINTREE_PRIVATE
    )


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


class CheckoutView(CartOrderMixin, FormMixin, DetailView):
    model = Cart
    template_name = "carts/checkout_view.html"
    form_class = GuestCheckForm

    def get_object(self, *args, **kwargs):
        cart = self.get_cart()
        if cart is None:
            return None
        return cart

    def get_context_data(self, *args, **kwargs):
        context = super(CheckoutView, self).get_context_data(*args, **kwargs)
        user_auth = False
        user_checkout_id = self.request.session.get("user_checkout_id")
        user = self.request.user
        user_is_auth = user.is_authenticated()

        if user_is_auth:
            user_checkout = UserCheckout.objects.get(user=user)
            context["client_token"] = user_checkout.get_client_token()
            user_auth = True
        elif not user_is_auth and user_checkout_id is None:
            context["login_form"] = AuthenticationForm()
            context["next_url"] = self.request.build_absolute_uri()
        else:
            pass

        if user_checkout_id is not None:
            if not user_is_auth:  # for GUEST user
                user_checkout_2 = UserCheckout.objects.get(id=user_checkout_id)
                context["client_token"] = user_checkout_2.get_client_token()
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
        if self.get_cart() is None:
            return redirect("cart")

        user = self.request.user
        print("user w GET   ", user)
        if user.is_authenticated():  # user id is not inherited from prev session
            user_checkout, created = UserCheckout.objects.get_or_create(user=user)
            print("user_checkout w GET   ", user_checkout, user_checkout.id)
            if created:
                user_checkout.user = user
                user_checkout.save()
            self.request.session["user_checkout_id"] = user_checkout.id
        user_checkout_id = self.request.session.get("user_checkout_id")

        if user_checkout_id is not None:
            new_order = self.get_order()
            if new_order.billing_address_id is None or new_order.shipping_address_id is None:
                return redirect("order_address")

            user_checkout = UserCheckout.objects.get(id=user_checkout_id)
            new_order.user = user_checkout
            new_order.save()
        get_data = super(CheckoutView, self).get(request, *args, **kwargs)
        return get_data


class CheckoutFinalView(CartOrderMixin, View):
    def post(self, request, *args, **kwargs):
        order = self.get_order()
        order_total = order.order_total
        nonce = request.POST.get("payment_method_nonce")
        if nonce:
            result = braintree.Transaction.sale({
                "amount": order_total,
                "payment_method_nonce": nonce,
                "billing": {
                    "postal_code": "%s" % order.billing_address.zipcode,
                },
                "options": {
                    "submit_for_settlement": True
                }
            })

            if result.is_success:
                order.mark_completed(order_id=result.transaction.id)
                del request.session["cart_id"]
                del request.session["order_id"]
                messages.success(request, "Thank you for your order!")
            else:
                messages.success(request, "%s" % result.message)
                return redirect("checkout")

        return redirect("order_detail", pk=order.id)

    def get(self, request, *args, **kwargs):
        return redirect("checkout")