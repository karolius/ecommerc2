from django import forms
from django.contrib.auth import get_user_model


User = get_user_model()


class GuestCheckForm(forms.Form):
    email = forms.EmailField()
    email2 = forms.EmailField(label="Verify Email")

    def clean_email2(self):
        email = self.cleaned_data.get("email")
        email2 = self.cleaned_data.get("email2")

        if email == email2:
            user_exits = User.objects.filter(email=email).count()
            print("--------BEDE CZYSCYCUCS", user_exits)
            if user_exits != 0:
                raise forms.ValidationError("This User already exists. Please login instead.")
            return email2
        raise forms.ValidationError("Please confirm emails are the same.")