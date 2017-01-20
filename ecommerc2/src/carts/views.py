from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse
from django.http import Http404, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin, DetailView

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
        if cart_id is None:
            cart = Cart()
            cart.save()
            self.request.session["cart_id"] = cart.id
        else:
            cart = Cart.objects.get(id=cart_id)  # TODO brak else

        if self.request.user.is_authenticated():
            cart.user = self.request.user
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

            cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item_instance)
            if created:
                flash_message = "Successfully added to the cart."
                item_added = True

            if delete_item:
                flash_message = "Item removed successfully."
                cart_item.delete()
            else:
                if not created:
                    flash_message = "Quantity has been updated successfully."
                cart_item.quantity = qty
                cart_item.save()

            if not request.is_ajax():
                return HttpResponseRedirect(reverse("cart"))

        if request.is_ajax():
            try:
                total = cart_item.line_item_total
            except:
                total = None

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
                "line_total": total,
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


class CheckoutView(DetailView):
    model = Cart
    # template_name = ""

    def get_object(self, *args, **kwargs):
        cart_id = self.request.session.get("cart_id")
        if cart_id is None:
            return redirect("cart")
        cart = Cart.objects.get(id=cart_id)
        return cart

    def get_context_data(self, **kwargs):
        context = super(CheckoutView, self).get_context_data(**kwargs)
        user_auth = False

        if not self.request.user.is_authenticated(): # or if is_gues
            context["login_form"] = AuthenticationForm()
            # next_url
        elif self.request.user.is_authenticated():
            user_auth = True
        context["user_auth"] = user_auth
        print(context)
        return context