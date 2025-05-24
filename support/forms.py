from django import forms
from .models import TicketMessage


class TicketMessageAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and not self.instance.pk:
            if 'sender' in self.fields:
                self.initial['sender'] = self.request.user
                self.fields['sender'].disabled = True
        elif self.instance.pk:
            if 'sender' in self.fields:
                self.fields['sender'].disabled = True

    class Meta:
        model = TicketMessage
        fields = '__all__'
