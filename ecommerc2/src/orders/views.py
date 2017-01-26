from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import CreateView
from django.views.generic import FormView

from .forms import AddressForm, UserAddressForm
from .models import UserAddress, UserCheckout


class UserAddressCreateView(CreateView):
    form_class = UserAddressForm
    template_name = "forms.html"
    success_url = "/checkout/address/"

    def get_checkout_user(self):
        user_checkout_id = self.request.session.get("user_checkout_id")
        user_checkout = UserCheckout.objects.get(id=user_checkout_id)
        return user_checkout

    def form_valid(self, form, *args, **kwargs):
        form.instance.user = self.get_checkout_user()
        return super(UserAddressCreateView, self).form_valid(form, *args, **kwargs)


class AddressSelectFormView(FormView):
    form_class = AddressForm
    template_name = "orders/address_select.html"

    def dispatch(self, *args, **kwargs):
        b_addr, s_addr = self.get_addresses()
        if b_addr.count() == 0:
            messages.success(self.request, "Please add a billing address before continuing")
            return redirect("user_address_create")
        elif s_addr.count() == 0:
            messages.success(self.request, "Please add a shipping address before continuing")
            return redirect("user_address_create")
        else:
            return super(AddressSelectFormView, self).dispatch(*args, **kwargs)

    def get_addresses(self, *args, **kwargs):
        user_checkout_id = self.request.session.get("user_checkout_id")
        user_checkout = UserCheckout.objects.get(id=user_checkout_id)
        b_addr = UserAddress.objects.filter(
            user=user_checkout,
            type="billing")
        s_addr = UserAddress.objects.filter(
            user=user_checkout,
            type="shipping")
        return b_addr, s_addr

    def get_form(self, *args, **kwargs):
        form = super(AddressSelectFormView, self).get_form(*args, **kwargs)
        b_addr, s_addr = self.get_addresses()
        form.fields["billing_address"].queryset = b_addr
        form.fields["shipping_address"].queryset = s_addr
        return form

    def form_valid(self, form, *args, **kwargs):
        billing_address = form.cleaned_data["billing_address"]
        shipping_address = form.cleaned_data["shipping_address"]
        self.request.session["billing_address_id"] = billing_address.id
        self.request.session["shipping_address_id"] = shipping_address.id
        return super(AddressSelectFormView, self).form_valid(form, *args, **kwargs)

    def get_success_url(self, *args, **kwargs):
        return "/checkout/"