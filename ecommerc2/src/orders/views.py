from django.shortcuts import render
from django.views.generic import FormView

from .forms import AddressForm
from .models import UserAddress, UserCheckout


class AddressSelectFormView(FormView):
    form_class = AddressForm
    template_name = "orders/address_select.html"

    def get_form(self, *args, **kwargs):
        form = super(AddressSelectFormView, self).get_form(*args, **kwargs)
        user = self.request.user
        email = UserCheckout.objects.filter(user=user).first()
        # It should work this way...
        # email = user.email
        # print("-------user:-----:	", self.request.user)
        # print("-------EMAIL:-----:	", self.request.user.email)
        form.fields["billing_address"].queryset = UserAddress.objects.filter(
            user__email=email,
            type="billing",
        )
        form.fields["shipping_address"].queryset = UserAddress.objects.filter(
            user__email=email,  # self.request.user.email,
            type="shipping",
        )
        return form

    def form_valid(self, form, *args, **kwargs):
        billing_address = form.cleaned_data["billing_address"]
        shipping_address = form.cleaned_data["shipping_address"]
        self.request.session["billing_address"] = billing_address.id
        self.request.session["shipping_address"] = shipping_address.id
        return super(AddressSelectFormView, self).form_valid(form, *args, **kwargs)

    def get_success_url(self, *args, **kwargs):
        return "/checkout/"