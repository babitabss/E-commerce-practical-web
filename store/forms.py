from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

INPUT_STYLE = 'width:100%;padding:11px 14px;border:1.5px solid #e0e4ea;border-radius:8px;font-size:0.95rem;outline:none;font-family:inherit;'

class RegisterForm(UserCreationForm):
    email      = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'your@email.com', 'style': INPUT_STYLE}))
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Your first name', 'style': INPUT_STYLE}))
    last_name  = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Your last name', 'style': INPUT_STYLE}))

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Choose a username', 'style': INPUT_STYLE}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={'placeholder': 'Create a password', 'style': INPUT_STYLE})
        self.fields['password2'].widget = forms.PasswordInput(attrs={'placeholder': 'Repeat your password', 'style': INPUT_STYLE})
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        self.fields['username'].help_text = None

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Enter your username', 'style': INPUT_STYLE}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password', 'style': INPUT_STYLE}))